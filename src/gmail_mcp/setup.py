"""CLI entry point for Gmail OAuth2 setup."""

from __future__ import annotations

import argparse
import sys

from gmail_mcp.auth import GmailAuth


def main(argv: list[str] | None = None) -> None:
    """Authenticate with Gmail and save an OAuth token."""
    parser = argparse.ArgumentParser(description="Authenticate with Gmail and save an OAuth token.")
    parser.add_argument(
        "--credentials",
        default="credentials/gmail_credentials.json",
        help="Path to OAuth credentials JSON from Google Cloud Console (default: %(default)s)",
    )
    parser.add_argument(
        "--token",
        default="credentials/token.json",
        help="Path to save the OAuth token (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    auth = GmailAuth(args.credentials, args.token)
    try:
        auth.get_service()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Token saved to {args.token}")


if __name__ == "__main__":
    main()
