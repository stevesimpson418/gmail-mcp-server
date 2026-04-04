"""Tests for Gmail OAuth2 setup CLI."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from gmail_mcp.setup import main


class TestSetupCLI:
    def test_help_flag(self, capsys):
        with pytest.raises(SystemExit, match="0"):
            main(["--help"])
        output = capsys.readouterr().out
        assert "Authenticate with Gmail" in output
        assert "--credentials" in output
        assert "--token" in output

    def test_default_paths_passed_to_auth(self):
        mock_auth = MagicMock()
        with patch("gmail_mcp.setup.GmailAuth", return_value=mock_auth) as mock_cls:
            main([])
        mock_cls.assert_called_once_with(
            "credentials/gmail_credentials.json", "credentials/token.json"
        )
        mock_auth.get_service.assert_called_once()

    def test_custom_paths_passed_to_auth(self):
        mock_auth = MagicMock()
        with patch("gmail_mcp.setup.GmailAuth", return_value=mock_auth) as mock_cls:
            main(["--credentials", "/tmp/creds.json", "--token", "/tmp/tok.json"])
        mock_cls.assert_called_once_with("/tmp/creds.json", "/tmp/tok.json")
        mock_auth.get_service.assert_called_once()

    def test_prints_success_message(self, capsys):
        mock_auth = MagicMock()
        with patch("gmail_mcp.setup.GmailAuth", return_value=mock_auth):
            main(["--token", "my/token.json"])
        output = capsys.readouterr().out
        assert "Token saved to my/token.json" in output

    def test_file_not_found_exits_with_error(self, capsys):
        mock_auth = MagicMock()
        mock_auth.get_service.side_effect = FileNotFoundError(
            "Gmail credentials file not found at 'missing.json'."
        )
        with (
            patch("gmail_mcp.setup.GmailAuth", return_value=mock_auth),
            pytest.raises(SystemExit, match="1"),
        ):
            main(["--credentials", "missing.json"])
        output = capsys.readouterr().err
        assert "Gmail credentials file not found" in output
