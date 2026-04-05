"""Tests for Gmail OAuth2 authentication."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from google.auth.exceptions import RefreshError

from gmail_mcp.auth import SCOPES, GmailAuth


class TestGmailAuthGetCredentials:
    def test_loads_existing_valid_token(self, tmp_path):
        token_path = str(tmp_path / "token.json")
        creds_path = str(tmp_path / "creds.json")
        auth = GmailAuth(creds_path, token_path)

        mock_creds = MagicMock()
        mock_creds.valid = True

        with (
            patch("os.path.exists", return_value=True),
            patch("gmail_mcp.auth.Credentials.from_authorized_user_file", return_value=mock_creds),
        ):
            result = auth.get_credentials()

        assert result is mock_creds

    def test_refreshes_expired_token(self, tmp_path):
        token_path = str(tmp_path / "token.json")
        creds_path = str(tmp_path / "creds.json")
        auth = GmailAuth(creds_path, token_path)

        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_token_value"
        mock_creds.to_json.return_value = '{"token": "refreshed"}'

        with (
            patch("os.path.exists", return_value=True),
            patch(
                "gmail_mcp.auth.Credentials.from_authorized_user_file",
                return_value=mock_creds,
            ),
            patch("gmail_mcp.auth.os.open", return_value=3),
            patch("gmail_mcp.auth.os.fdopen", MagicMock()),
        ):
            result = auth.get_credentials()

        mock_creds.refresh.assert_called_once()
        assert result is mock_creds

    def test_refresh_error_falls_through_to_consent_flow(self, tmp_path):
        token_path = str(tmp_path / "token.json")
        creds_path = str(tmp_path / "creds.json")
        creds_path_obj = tmp_path / "creds.json"
        creds_path_obj.write_text("{}")

        auth = GmailAuth(creds_path, token_path)

        expired_creds = MagicMock()
        expired_creds.valid = False
        expired_creds.expired = True
        expired_creds.refresh_token = "old_refresh"
        expired_creds.refresh.side_effect = RefreshError("Token revoked")

        new_creds = MagicMock()
        new_creds.to_json.return_value = '{"token": "new"}'
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = new_creds

        with (
            patch("os.path.exists", return_value=True),
            patch(
                "gmail_mcp.auth.Credentials.from_authorized_user_file",
                return_value=expired_creds,
            ),
            patch(
                "gmail_mcp.auth.InstalledAppFlow.from_client_secrets_file",
                return_value=mock_flow,
            ),
            patch("gmail_mcp.auth.os.open", return_value=3),
            patch("gmail_mcp.auth.os.fdopen", MagicMock()),
        ):
            result = auth.get_credentials()

        mock_flow.run_local_server.assert_called_once_with(port=0)
        assert result is new_creds

    def test_corrupt_token_falls_through_to_consent_flow(self, tmp_path):
        token_path = str(tmp_path / "token.json")
        creds_path = str(tmp_path / "creds.json")
        (tmp_path / "token.json").write_text("{corrupt")
        (tmp_path / "creds.json").write_text("{}")

        auth = GmailAuth(creds_path, token_path)

        new_creds = MagicMock()
        new_creds.to_json.return_value = '{"token": "new"}'
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = new_creds

        with (
            patch(
                "gmail_mcp.auth.Credentials.from_authorized_user_file",
                side_effect=ValueError("Invalid token format"),
            ),
            patch(
                "gmail_mcp.auth.InstalledAppFlow.from_client_secrets_file",
                return_value=mock_flow,
            ),
            patch("gmail_mcp.auth.os.open", return_value=3),
            patch("gmail_mcp.auth.os.fdopen", MagicMock()),
        ):
            result = auth.get_credentials()

        mock_flow.run_local_server.assert_called_once_with(port=0)
        assert result is new_creds

    def test_invalid_but_not_expired_token_triggers_reauth(self, tmp_path, caplog):
        token_path = str(tmp_path / "token.json")
        creds_path = str(tmp_path / "creds.json")
        (tmp_path / "creds.json").write_text("{}")

        auth = GmailAuth(creds_path, token_path)

        invalid_creds = MagicMock()
        invalid_creds.valid = False
        invalid_creds.expired = False
        invalid_creds.refresh_token = None

        new_creds = MagicMock()
        new_creds.to_json.return_value = '{"token": "new"}'
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = new_creds

        with (
            patch("os.path.exists", return_value=True),
            patch(
                "gmail_mcp.auth.Credentials.from_authorized_user_file",
                return_value=invalid_creds,
            ),
            patch(
                "gmail_mcp.auth.InstalledAppFlow.from_client_secrets_file",
                return_value=mock_flow,
            ),
            patch("gmail_mcp.auth.os.open", return_value=3),
            patch("gmail_mcp.auth.os.fdopen", MagicMock()),
        ):
            import logging

            with caplog.at_level(logging.WARNING):
                result = auth.get_credentials()

        assert "credentials are invalid" in caplog.text
        mock_flow.run_local_server.assert_called_once_with(port=0)
        assert result is new_creds

    def test_raises_when_credentials_file_missing(self, tmp_path):
        token_path = str(tmp_path / "token.json")
        creds_path = str(tmp_path / "nonexistent_creds.json")
        auth = GmailAuth(creds_path, token_path)

        with pytest.raises(FileNotFoundError, match="Gmail credentials file not found"):
            auth.get_credentials()

    def test_runs_consent_flow_on_first_run(self, tmp_path):
        token_path = str(tmp_path / "token.json")
        creds_path = str(tmp_path / "creds.json")
        creds_path_obj = tmp_path / "creds.json"
        creds_path_obj.write_text("{}")

        auth = GmailAuth(creds_path, token_path)

        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"token": "new"}'
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds

        with (
            patch(
                "gmail_mcp.auth.InstalledAppFlow.from_client_secrets_file",
                return_value=mock_flow,
            ),
            patch("gmail_mcp.auth.os.open", return_value=3),
            patch("gmail_mcp.auth.os.fdopen", MagicMock()),
        ):
            result = auth.get_credentials()

        mock_flow.run_local_server.assert_called_once_with(port=0)
        assert result is mock_creds


class TestGmailAuthGetService:
    def test_builds_and_caches_service(self, tmp_path):
        token_path = str(tmp_path / "token.json")
        creds_path = str(tmp_path / "creds.json")
        auth = GmailAuth(creds_path, token_path)

        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_service = MagicMock()

        with (
            patch("os.path.exists", return_value=True),
            patch(
                "gmail_mcp.auth.Credentials.from_authorized_user_file",
                return_value=mock_creds,
            ),
            patch("gmail_mcp.auth.build", return_value=mock_service) as mock_build,
        ):
            service1 = auth.get_service()
            service2 = auth.get_service()

        assert service1 is mock_service
        assert service2 is mock_service
        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds)


class TestSaveToken:
    def test_logs_warning_on_write_failure(self, tmp_path, caplog):
        token_path = str(tmp_path / "nonexistent_dir" / "deep" / "token.json")
        auth = GmailAuth("creds.json", token_path)

        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"token": "test"}'

        with patch("gmail_mcp.auth.os.makedirs", side_effect=OSError("Permission denied")):
            import logging

            with caplog.at_level(logging.WARNING):
                auth._save_token(mock_creds)

        assert "Failed to save token" in caplog.text


class TestScopes:
    def test_scopes_include_only_modify(self):
        """gmail.modify is the sole scope — it covers read, modify, send, and drafts."""
        assert SCOPES == ["https://www.googleapis.com/auth/gmail.modify"]
