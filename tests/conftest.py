"""Shared fixtures for Gmail MCP tests."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def gmail_service():
    """A MagicMock that behaves like googleapiclient Gmail service."""
    return MagicMock()


@pytest.fixture
def sample_message_metadata():
    """A metadata-format message as returned by the Gmail API."""
    return {
        "id": "msg_001",
        "threadId": "thread_001",
        "snippet": "Hey, just following up...",
        "labelIds": ["INBOX", "UNREAD"],
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Follow up"},
                {"name": "From", "value": "alice@example.com"},
                {"name": "Date", "value": "Fri, 04 Apr 2026 10:00:00 +0000"},
            ]
        },
    }


@pytest.fixture
def sample_message_full():
    """A full-format message with plain text body."""
    body_text = "Hello, this is the message body."
    encoded_body = base64.urlsafe_b64encode(body_text.encode()).decode()

    return {
        "id": "msg_002",
        "threadId": "thread_002",
        "snippet": "Hello, this is the message...",
        "labelIds": ["INBOX"],
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test email"},
                {"name": "From", "value": "bob@example.com"},
                {"name": "To", "value": "me@example.com"},
                {"name": "Cc", "value": ""},
                {"name": "Date", "value": "Fri, 04 Apr 2026 12:00:00 +0000"},
            ],
            "mimeType": "text/plain",
            "body": {"data": encoded_body, "size": len(body_text)},
        },
    }


@pytest.fixture
def sample_multipart_message():
    """A multipart message with text/plain and text/html parts."""
    plain_text = "Plain text body"
    html_text = "<html><body>HTML body</body></html>"

    return {
        "id": "msg_003",
        "threadId": "thread_003",
        "snippet": "Plain text body",
        "labelIds": ["INBOX"],
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Multipart test"},
                {"name": "From", "value": "carol@example.com"},
                {"name": "To", "value": "me@example.com"},
                {"name": "Cc", "value": ""},
                {"name": "Date", "value": "Fri, 04 Apr 2026 14:00:00 +0000"},
            ],
            "mimeType": "multipart/alternative",
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": base64.urlsafe_b64encode(plain_text.encode()).decode(),
                        "size": len(plain_text),
                    },
                },
                {
                    "mimeType": "text/html",
                    "body": {
                        "data": base64.urlsafe_b64encode(html_text.encode()).decode(),
                        "size": len(html_text),
                    },
                },
            ],
        },
    }


@pytest.fixture
def sample_labels():
    """Gmail labels API response."""
    return {
        "labels": [
            {"id": "INBOX", "name": "INBOX", "type": "system"},
            {"id": "SENT", "name": "SENT", "type": "system"},
            {"id": "UNREAD", "name": "UNREAD", "type": "system"},
            {"id": "STARRED", "name": "STARRED", "type": "system"},
            {"id": "IMPORTANT", "name": "IMPORTANT", "type": "system"},
            {"id": "Label_1", "name": "Work", "type": "user"},
            {"id": "Label_2", "name": "Personal", "type": "user"},
        ]
    }
