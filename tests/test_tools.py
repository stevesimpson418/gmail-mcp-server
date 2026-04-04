"""Tests for Gmail MCP tool registration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from gmail_mcp.tools import register_gmail_tools


class TestToolRegistration:
    def test_skips_when_env_vars_missing(self):
        mcp = MagicMock()

        with patch.dict("os.environ", {}, clear=True):
            register_gmail_tools(mcp)

        # No tools should be registered
        mcp.tool.assert_not_called()

    def test_skips_when_credentials_file_missing(self):
        mcp = MagicMock()

        with patch.dict(
            "os.environ",
            {
                "GMAIL_CREDENTIALS_PATH": "/nonexistent/creds.json",
                "GMAIL_TOKEN_PATH": "/nonexistent/token.json",
            },
        ):
            register_gmail_tools(mcp)

        # Auth will fail with FileNotFoundError, tools should not be registered
        mcp.tool.assert_not_called()

    def test_registers_tools_when_auth_succeeds(self):
        mcp = MagicMock()
        # Make @mcp.tool work as a passthrough decorator
        mcp.tool.return_value = lambda fn: fn
        mcp.tool.side_effect = None

        mock_service = MagicMock()

        with (
            patch.dict(
                "os.environ",
                {
                    "GMAIL_CREDENTIALS_PATH": "/path/to/creds.json",
                    "GMAIL_TOKEN_PATH": "/path/to/token.json",
                },
            ),
            patch("gmail_mcp.tools.GmailAuth") as mock_auth_cls,
        ):
            mock_auth_cls.return_value.get_service.return_value = mock_service
            register_gmail_tools(mcp)

        # mcp.tool should have been called multiple times for each tool
        assert mcp.tool.call_count > 0 or mcp.tool.return_value.call_count > 0

    def test_skips_when_auth_raises_generic_exception(self):
        mcp = MagicMock()

        with (
            patch.dict(
                "os.environ",
                {
                    "GMAIL_CREDENTIALS_PATH": "/path/to/creds.json",
                    "GMAIL_TOKEN_PATH": "/path/to/token.json",
                },
            ),
            patch("gmail_mcp.tools.GmailAuth") as mock_auth_cls,
        ):
            mock_auth_cls.return_value.get_service.side_effect = RuntimeError("OAuth failed")
            register_gmail_tools(mcp)

        mcp.tool.assert_not_called()
