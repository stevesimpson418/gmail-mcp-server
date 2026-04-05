"""Gmail OAuth2 authentication — token persistence and refresh."""

from __future__ import annotations

import logging
import os
import stat

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

logger = logging.getLogger(__name__)

# gmail.modify is the minimum single scope that covers all server operations:
#   - Read:   messages.list, messages.get, threads.get, messages.attachments.get
#   - Modify: messages.batchModify (archive, label, read/unread, star, important)
#   - Trash:  messages.trash
#   - Labels: labels.list, labels.create
#   - Send:   messages.send, drafts.create, drafts.send
#
# Narrower scopes (gmail.readonly, gmail.labels, gmail.compose, gmail.send) cannot
# cover messages.batchModify or messages.trash — those require gmail.modify or the
# full-access mail.google.com scope. Since gmail.modify is needed anyway and it
# includes all other operations, a single scope is both sufficient and minimal.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailAuth:
    """Handles Gmail OAuth2 flow, token storage, and refresh.

    On first run, opens a browser for consent. Subsequent runs use the
    stored token, refreshing automatically when expired.
    """

    def __init__(self, credentials_path: str, token_path: str) -> None:
        self._credentials_path = credentials_path
        self._token_path = token_path
        self._service = None

    def get_credentials(self) -> Credentials:
        """Load or create OAuth2 credentials.

        Returns valid credentials, handling refresh and first-run consent flow.

        Raises:
            FileNotFoundError: If the OAuth credentials file is missing.
            RefreshError: If token refresh fails and re-auth is needed.
        """
        creds = None

        # Try loading existing token
        if os.path.exists(self._token_path):
            try:
                creds = Credentials.from_authorized_user_file(self._token_path, SCOPES)
            except (ValueError, KeyError) as e:
                logger.warning(
                    "Token file '%s' is corrupt (%s) — will re-authenticate.",
                    self._token_path,
                    e,
                )

        # Refresh or run consent flow
        if creds and creds.valid:
            return creds

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._save_token(creds)
                return creds
            except RefreshError:
                logger.warning(
                    "Token refresh failed — re-running consent flow. "
                    "If this persists, delete '%s' and re-authenticate.",
                    self._token_path,
                )
                creds = None

        if creds and not creds.valid:
            logger.warning(
                "Token file exists but credentials are invalid and cannot be refreshed. "
                "Re-authenticating."
            )

        # First-run or re-auth: need credentials file
        if not os.path.exists(self._credentials_path):
            raise FileNotFoundError(
                f"Gmail credentials file not found at '{self._credentials_path}'. "
                "Download it from Google Cloud Console: "
                "https://console.cloud.google.com/apis/credentials"
            )

        flow = InstalledAppFlow.from_client_secrets_file(self._credentials_path, SCOPES)
        creds = flow.run_local_server(port=0)
        self._save_token(creds)
        return creds

    def get_service(self) -> Resource:
        """Build and cache a Gmail API service resource."""
        if self._service is None:
            creds = self.get_credentials()
            self._service = build("gmail", "v1", credentials=creds)
        return self._service

    def _save_token(self, creds: Credentials) -> None:
        """Persist token to disk with owner-only permissions."""
        try:
            os.makedirs(os.path.dirname(self._token_path) or ".", exist_ok=True)
            fd = os.open(
                self._token_path,
                os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                stat.S_IRUSR | stat.S_IWUSR,
            )
            with os.fdopen(fd, "w") as f:
                f.write(creds.to_json())
        except OSError as e:
            logger.warning(
                "Failed to save token to '%s': %s — "
                "credentials are valid for this session but won't persist.",
                self._token_path,
                e,
            )
