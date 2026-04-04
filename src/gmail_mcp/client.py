"""Gmail API client wrapper for the Gmail MCP server."""

from __future__ import annotations

import base64
import logging
from email.mime.text import MIMEText

from gmail_mcp.exceptions import GmailAPIError

logger = logging.getLogger(__name__)

# Gmail batchModify API limit per call
_BATCH_MODIFY_LIMIT = 1000


class GmailClient:
    """Client wrapping the Gmail API.

    All methods use userId="me" (the authenticated user).
    """

    def __init__(self, service) -> None:
        self._service = service
        self._label_cache: dict[str, str] | None = None

    # --- Read operations ---

    def search_messages(self, query: str, max_results: int = 20) -> list[dict]:
        """Search for messages matching a Gmail query.

        Returns trimmed summaries (id, thread_id, subject, from, date, snippet, label_ids).
        Full body is only available via read_message().
        """
        try:
            response = (
                self._service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
            messages = response.get("messages", [])
            if not messages:
                return []

            results = []
            for msg_ref in messages:
                msg = (
                    self._service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=msg_ref["id"],
                        format="metadata",
                        metadataHeaders=["Subject", "From", "Date"],
                    )
                    .execute()
                )
                results.append(self._parse_message_summary(msg))
            return results
        except GmailAPIError:
            raise
        except Exception as e:
            raise GmailAPIError(f"Failed to search messages: {e}") from e

    def read_message(self, message_id: str) -> dict:
        """Read a full message including body content."""
        try:
            msg = (
                self._service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            return self._parse_full_message(msg)
        except GmailAPIError:
            raise
        except Exception as e:
            raise GmailAPIError(f"Failed to read message {message_id}: {e}") from e

    def read_thread(self, thread_id: str) -> dict:
        """Read all messages in a thread."""
        try:
            thread = (
                self._service.users()
                .threads()
                .get(userId="me", id=thread_id, format="full")
                .execute()
            )
            messages = [self._parse_full_message(msg) for msg in thread.get("messages", [])]
            return {"thread_id": thread_id, "message_count": len(messages), "messages": messages}
        except GmailAPIError:
            raise
        except Exception as e:
            raise GmailAPIError(f"Failed to read thread {thread_id}: {e}") from e

    # --- Attachment operations ---

    @staticmethod
    def _extract_attachment_metadata(payload: dict) -> list[dict]:
        """Recursively extract attachment metadata from a message payload."""
        attachments = []
        for part in payload.get("parts", []):
            filename = part.get("filename", "")
            if filename:
                attachments.append(
                    {
                        "attachment_id": part.get("body", {}).get("attachmentId", ""),
                        "filename": filename,
                        "mime_type": part.get("mimeType", ""),
                        "size": part.get("body", {}).get("size", 0),
                        "part_id": part.get("partId", ""),
                    }
                )
            if "parts" in part:
                attachments.extend(GmailClient._extract_attachment_metadata(part))
        return attachments

    def list_attachments(self, message_id: str) -> list[dict]:
        """List attachments for a message."""
        try:
            msg = (
                self._service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            return self._extract_attachment_metadata(msg.get("payload", {}))
        except GmailAPIError:
            raise
        except Exception as e:
            raise GmailAPIError(f"Failed to list attachments for {message_id}: {e}") from e

    def get_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Fetch and decode a raw attachment."""
        try:
            response = (
                self._service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )
            return base64.urlsafe_b64decode(response["data"])
        except GmailAPIError:
            raise
        except Exception as e:
            raise GmailAPIError(
                f"Failed to get attachment {attachment_id} from {message_id}: {e}"
            ) from e

    # Non-text/* MIME types that are actually text-readable;
    # application/csv handles servers that misreport text/csv
    _TEXT_MIME_TYPES = frozenset({"application/json", "application/csv", "application/xml"})

    def read_attachment_content(
        self, message_id: str, attachment_id: str, filename: str, mime_type: str
    ) -> dict:
        """Read attachment content, decoding text types as UTF-8."""
        raw_bytes = self.get_attachment(message_id, attachment_id)
        is_text = mime_type.startswith("text/") or mime_type in self._TEXT_MIME_TYPES
        if is_text:
            content = raw_bytes.decode("utf-8", errors="replace")
            encoding = "text"
        else:
            content = base64.b64encode(raw_bytes).decode("ascii")
            encoding = "base64"
        return {
            "filename": filename,
            "mime_type": mime_type,
            "size": len(raw_bytes),
            "encoding": encoding,
            "content": content,
        }

    # --- Label operations ---

    def list_labels(self) -> list[dict]:
        """List all Gmail labels."""
        try:
            response = self._service.users().labels().list(userId="me").execute()
            labels = response.get("labels", [])
            return [
                {"id": lbl["id"], "name": lbl["name"], "type": lbl.get("type", "")}
                for lbl in labels
            ]
        except GmailAPIError:
            raise
        except Exception as e:
            raise GmailAPIError(f"Failed to list labels: {e}") from e

    def create_label(
        self,
        name: str,
        text_color: str | None = None,
        background_color: str | None = None,
    ) -> dict:
        """Create a new Gmail label.

        Both text_color and background_color must be provided together;
        providing only one raises ValueError.
        """
        if bool(text_color) != bool(background_color):
            raise ValueError(
                "Both text_color and background_color must be provided together, or neither."
            )
        try:
            body: dict = {
                "name": name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
            if text_color and background_color:
                body["color"] = {"textColor": text_color, "backgroundColor": background_color}
            label = self._service.users().labels().create(userId="me", body=body).execute()
            self._label_cache = None  # Invalidate cache so new label is discoverable
            return {"id": label["id"], "name": label["name"]}
        except GmailAPIError:
            raise
        except Exception as e:
            raise GmailAPIError(f"Failed to create label '{name}': {e}") from e

    def apply_label(self, message_ids: list[str], label_name: str) -> dict:
        """Apply a label to messages by label name."""
        label_id = self._resolve_label_id(label_name)
        return self._modify_messages(message_ids, add_labels=[label_id])

    def remove_label(self, message_ids: list[str], label_name: str) -> dict:
        """Remove a label from messages by label name."""
        label_id = self._resolve_label_id(label_name)
        return self._modify_messages(message_ids, remove_labels=[label_id])

    # --- Archive operations ---

    def archive_messages(self, message_ids: list[str]) -> dict:
        """Archive messages by removing the INBOX label."""
        return self._modify_messages(message_ids, remove_labels=["INBOX"])

    def bulk_archive(self, query: str) -> dict:
        """Search for messages and archive all results in one operation.

        Paginates through all search results, then uses batchModify to
        remove INBOX from all matched messages efficiently.
        """
        try:
            all_ids = []
            page_token = None
            while True:
                response = (
                    self._service.users()
                    .messages()
                    .list(userId="me", q=query, maxResults=500, pageToken=page_token)
                    .execute()
                )
                messages = response.get("messages", [])
                all_ids.extend(msg["id"] for msg in messages)
                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            if not all_ids:
                return {"archived": 0, "query": query}

            for i in range(0, len(all_ids), _BATCH_MODIFY_LIMIT):
                chunk = all_ids[i : i + _BATCH_MODIFY_LIMIT]
                self._service.users().messages().batchModify(
                    userId="me",
                    body={"ids": chunk, "removeLabelIds": ["INBOX"]},
                ).execute()
            return {"archived": len(all_ids), "query": query}
        except GmailAPIError:
            raise
        except Exception as e:
            raise GmailAPIError(f"Failed to bulk archive for query '{query}': {e}") from e

    # --- Read state ---

    def mark_read(self, message_ids: list[str]) -> dict:
        """Mark messages as read by removing UNREAD label."""
        return self._modify_messages(message_ids, remove_labels=["UNREAD"])

    def mark_unread(self, message_ids: list[str]) -> dict:
        """Mark messages as unread by adding UNREAD label."""
        return self._modify_messages(message_ids, add_labels=["UNREAD"])

    # --- Star / Important ---
    # Note: unstar/unmark-important can be done via remove_gmail_label
    # with "STARRED"/"IMPORTANT"

    def star_messages(self, message_ids: list[str]) -> dict:
        """Star messages by adding STARRED label."""
        return self._modify_messages(message_ids, add_labels=["STARRED"])

    def mark_important(self, message_ids: list[str]) -> dict:
        """Mark messages as important by adding IMPORTANT label."""
        return self._modify_messages(message_ids, add_labels=["IMPORTANT"])

    # --- Compose / Send ---

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: str | None = None,
        cc: str | None = None,
    ) -> dict:
        """Create a draft email. Use thread_id for in-thread replies."""
        try:
            raw = self._build_mime_message(to, subject, body, cc)
            draft_body: dict = {"message": {"raw": raw}}
            if thread_id:
                draft_body["message"]["threadId"] = thread_id
            draft = self._service.users().drafts().create(userId="me", body=draft_body).execute()
            return {
                "draft_id": draft["id"],
                "message_id": draft["message"]["id"],
                "thread_id": draft["message"].get("threadId"),
            }
        except GmailAPIError:
            raise
        except Exception as e:
            raise GmailAPIError(f"Failed to create draft: {e}") from e

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str | None = None,
    ) -> dict:
        """Send an email directly."""
        try:
            raw = self._build_mime_message(to, subject, body, cc)
            sent = self._service.users().messages().send(userId="me", body={"raw": raw}).execute()
            return {"message_id": sent["id"], "thread_id": sent.get("threadId")}
        except GmailAPIError:
            raise
        except Exception as e:
            raise GmailAPIError(f"Failed to send email: {e}") from e

    def send_draft(self, draft_id: str) -> dict:
        """Send an existing draft."""
        try:
            sent = self._service.users().drafts().send(userId="me", body={"id": draft_id}).execute()
            return {"message_id": sent["id"], "thread_id": sent.get("threadId")}
        except GmailAPIError:
            raise
        except Exception as e:
            raise GmailAPIError(f"Failed to send draft {draft_id}: {e}") from e

    # --- Trash ---

    def trash_messages(self, message_ids: list[str]) -> dict:
        """Move messages to trash (recoverable for 30 days)."""
        succeeded = 0
        failed = 0
        errors: list[dict] = []
        for msg_id in message_ids:
            try:
                self._service.users().messages().trash(userId="me", id=msg_id).execute()
                succeeded += 1
            except Exception as e:
                logger.warning("Failed to trash message %s: %s", msg_id, e)
                failed += 1
                errors.append({"message_id": msg_id, "error": str(e)})
        return {"succeeded": succeeded, "failed": failed, "errors": errors}

    # --- Private helpers ---

    def _modify_messages(
        self,
        message_ids: list[str],
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
    ) -> dict:
        """Batch modify labels on messages, chunking to respect API limits."""
        if not message_ids:
            return {"modified": 0}
        try:
            for i in range(0, len(message_ids), _BATCH_MODIFY_LIMIT):
                chunk = message_ids[i : i + _BATCH_MODIFY_LIMIT]
                body: dict = {"ids": chunk}
                if add_labels:
                    body["addLabelIds"] = add_labels
                if remove_labels:
                    body["removeLabelIds"] = remove_labels
                self._service.users().messages().batchModify(userId="me", body=body).execute()
            return {"modified": len(message_ids)}
        except GmailAPIError:
            raise
        except Exception as e:
            raise GmailAPIError(f"Failed to modify messages: {e}") from e

    def _resolve_label_id(self, label_name: str) -> str:
        """Resolve a label name to its ID. Caches label list with one retry on miss."""
        for attempt in range(2):
            if self._label_cache is None or attempt > 0:
                labels = self.list_labels()
                self._label_cache = {lbl["name"].lower(): lbl["id"] for lbl in labels}
            label_id = self._label_cache.get(label_name.lower())
            if label_id is not None:
                return label_id
        available = ", ".join(sorted(self._label_cache.keys()))
        raise ValueError(f"Label '{label_name}' not found. Available labels: {available}")

    @staticmethod
    def _build_mime_message(to: str, subject: str, body: str, cc: str | None = None) -> str:
        """Build a base64url-encoded MIME message."""
        msg = MIMEText(body)
        msg["to"] = to
        msg["subject"] = subject
        if cc:
            msg["cc"] = cc
        return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")

    @staticmethod
    def _get_header(headers: list[dict], name: str) -> str:
        """Extract a header value by name."""
        for h in headers:
            if h["name"].lower() == name.lower():
                return h["value"]
        return ""

    def _parse_message_summary(self, msg: dict) -> dict:
        """Parse a metadata-format message into a summary dict."""
        headers = msg.get("payload", {}).get("headers", [])
        return {
            "id": msg["id"],
            "thread_id": msg["threadId"],
            "subject": self._get_header(headers, "Subject"),
            "from": self._get_header(headers, "From"),
            "date": self._get_header(headers, "Date"),
            "snippet": msg.get("snippet", ""),
            "label_ids": msg.get("labelIds", []),
        }

    def _parse_full_message(self, msg: dict) -> dict:
        """Parse a full-format message including body."""
        payload = msg.get("payload", {})
        headers = payload.get("headers", [])
        body = self._extract_body(payload)
        attachments = self._extract_attachment_metadata(payload)
        return {
            "id": msg["id"],
            "thread_id": msg["threadId"],
            "subject": self._get_header(headers, "Subject"),
            "from": self._get_header(headers, "From"),
            "to": self._get_header(headers, "To"),
            "cc": self._get_header(headers, "Cc"),
            "date": self._get_header(headers, "Date"),
            "snippet": msg.get("snippet", ""),
            "label_ids": msg.get("labelIds", []),
            "body": body,
            "has_attachments": bool(attachments),
            "attachment_count": len(attachments),
        }

    @staticmethod
    def _extract_body(payload: dict) -> str:
        """Extract body text from a message payload, preferring text/plain."""
        # Simple message (no parts)
        if "body" in payload and payload["body"].get("data"):
            data = payload["body"]["data"]
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        # Multipart message
        parts = payload.get("parts", [])
        # First pass: look for text/plain
        for part in parts:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode(
                    "utf-8", errors="replace"
                )
        # Second pass: fall back to text/html
        for part in parts:
            if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode(
                    "utf-8", errors="replace"
                )
        # Nested multipart (e.g. multipart/alternative inside multipart/mixed)
        for part in parts:
            if "parts" in part:
                result = GmailClient._extract_body(part)
                if result:
                    return result
        return ""
