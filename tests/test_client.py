"""Tests for Gmail API client."""

from __future__ import annotations

import base64

import pytest

from gmail_mcp.client import GmailClient
from gmail_mcp.exceptions import GmailAPIError


class TestSearchMessages:
    def test_returns_empty_list_when_no_messages(self, gmail_service):
        gmail_service.users().messages().list().execute.return_value = {"messages": []}
        client = GmailClient(gmail_service)

        result = client.search_messages("is:unread")

        assert result == []

    def test_returns_summaries_for_found_messages(self, gmail_service, sample_message_metadata):
        gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg_001"}]
        }
        gmail_service.users().messages().get().execute.return_value = sample_message_metadata
        client = GmailClient(gmail_service)

        result = client.search_messages("is:unread", max_results=10)

        assert len(result) == 1
        assert result[0]["id"] == "msg_001"
        assert result[0]["subject"] == "Follow up"
        assert result[0]["from"] == "alice@example.com"

    def test_raises_gmail_api_error_on_failure(self, gmail_service):
        gmail_service.users().messages().list().execute.side_effect = Exception("API error")
        client = GmailClient(gmail_service)

        with pytest.raises(GmailAPIError, match="Failed to search messages"):
            client.search_messages("is:unread")


class TestReadMessage:
    def test_parses_full_message(self, gmail_service, sample_message_full):
        gmail_service.users().messages().get().execute.return_value = sample_message_full
        client = GmailClient(gmail_service)

        result = client.read_message("msg_002")

        assert result["id"] == "msg_002"
        assert result["subject"] == "Test email"
        assert result["body"] == "Hello, this is the message body."
        assert result["has_attachments"] is False

    def test_parses_multipart_message_prefers_plain(self, gmail_service, sample_multipart_message):
        gmail_service.users().messages().get().execute.return_value = sample_multipart_message
        client = GmailClient(gmail_service)

        result = client.read_message("msg_003")

        assert result["body"] == "Plain text body"

    def test_raises_gmail_api_error_on_failure(self, gmail_service):
        gmail_service.users().messages().get().execute.side_effect = Exception("Not found")
        client = GmailClient(gmail_service)

        with pytest.raises(GmailAPIError, match="Failed to read message"):
            client.read_message("msg_bad")


class TestReadThread:
    def test_returns_thread_with_messages(self, gmail_service, sample_message_full):
        gmail_service.users().threads().get().execute.return_value = {
            "messages": [sample_message_full]
        }
        client = GmailClient(gmail_service)

        result = client.read_thread("thread_002")

        assert result["thread_id"] == "thread_002"
        assert result["message_count"] == 1
        assert result["messages"][0]["id"] == "msg_002"

    def test_raises_gmail_api_error_on_failure(self, gmail_service):
        gmail_service.users().threads().get().execute.side_effect = Exception("Thread error")
        client = GmailClient(gmail_service)

        with pytest.raises(GmailAPIError, match="Failed to read thread"):
            client.read_thread("thread_bad")


class TestLabelOperations:
    def test_list_labels(self, gmail_service, sample_labels):
        gmail_service.users().labels().list().execute.return_value = sample_labels
        client = GmailClient(gmail_service)

        result = client.list_labels()

        assert len(result) == 7
        assert result[0]["name"] == "INBOX"

    def test_list_labels_raises_on_failure(self, gmail_service):
        gmail_service.users().labels().list().execute.side_effect = Exception("Labels error")
        client = GmailClient(gmail_service)

        with pytest.raises(GmailAPIError, match="Failed to list labels"):
            client.list_labels()

    def test_create_label(self, gmail_service):
        gmail_service.users().labels().create().execute.return_value = {
            "id": "Label_new",
            "name": "Test Label",
        }
        client = GmailClient(gmail_service)

        result = client.create_label("Test Label")

        assert result["id"] == "Label_new"
        assert result["name"] == "Test Label"

    def test_create_label_with_colors(self, gmail_service):
        gmail_service.users().labels().create().execute.return_value = {
            "id": "Label_color",
            "name": "Urgent",
        }
        client = GmailClient(gmail_service)

        result = client.create_label("Urgent", text_color="#ffffff", background_color="#cc3a21")

        assert result["name"] == "Urgent"

    def test_create_label_rejects_partial_color(self, gmail_service):
        client = GmailClient(gmail_service)

        with pytest.raises(ValueError, match="Both text_color and background_color"):
            client.create_label("Bad", text_color="#ffffff")

    def test_create_label_invalidates_cache(self, gmail_service, sample_labels):
        gmail_service.users().labels().list().execute.return_value = sample_labels
        gmail_service.users().labels().create().execute.return_value = {
            "id": "Label_new",
            "name": "New Label",
        }
        gmail_service.users().messages().batchModify().execute.return_value = None
        client = GmailClient(gmail_service)

        # Populate cache
        client.apply_label(["msg_001"], "Work")
        assert client._label_cache is not None

        # Create label should invalidate cache
        client.create_label("New Label")
        assert client._label_cache is None

    def test_apply_label_resolves_name(self, gmail_service, sample_labels):
        gmail_service.users().labels().list().execute.return_value = sample_labels
        gmail_service.users().messages().batchModify().execute.return_value = None
        client = GmailClient(gmail_service)

        result = client.apply_label(["msg_001"], "Work")

        assert result["modified"] == 1

    def test_remove_label(self, gmail_service, sample_labels):
        gmail_service.users().labels().list().execute.return_value = sample_labels
        gmail_service.users().messages().batchModify().execute.return_value = None
        client = GmailClient(gmail_service)

        result = client.remove_label(["msg_001"], "Work")

        assert result["modified"] == 1

    def test_label_cache_retries_on_miss(self, gmail_service):
        """Labels created externally (e.g. Gmail UI) should be found on retry."""
        # First call: cache doesn't have "New Label"
        # Second call (retry): cache refreshed and finds it
        gmail_service.users().labels().list().execute.side_effect = [
            {
                "labels": [
                    {"id": "INBOX", "name": "INBOX", "type": "system"},
                ]
            },
            {
                "labels": [
                    {"id": "INBOX", "name": "INBOX", "type": "system"},
                    {"id": "Label_new", "name": "New Label", "type": "user"},
                ]
            },
        ]
        gmail_service.users().messages().batchModify().execute.return_value = None
        client = GmailClient(gmail_service)

        result = client.apply_label(["msg_001"], "New Label")

        assert result["modified"] == 1
        assert gmail_service.users().labels().list().execute.call_count == 2

    def test_resolve_label_raises_for_unknown(self, gmail_service, sample_labels):
        gmail_service.users().labels().list().execute.return_value = sample_labels
        client = GmailClient(gmail_service)

        with pytest.raises(ValueError, match="Label 'Nonexistent' not found"):
            client.apply_label(["msg_001"], "Nonexistent")

    def test_label_cache_is_reused(self, gmail_service, sample_labels):
        gmail_service.users().labels().list().execute.return_value = sample_labels
        gmail_service.users().messages().batchModify().execute.return_value = None
        client = GmailClient(gmail_service)

        client.apply_label(["msg_001"], "Work")
        client.apply_label(["msg_002"], "Personal")

        # list_labels should only be called once due to caching
        gmail_service.users().labels().list().execute.assert_called_once()


class TestArchiveOperations:
    def test_archive_messages(self, gmail_service):
        gmail_service.users().messages().batchModify().execute.return_value = None
        client = GmailClient(gmail_service)

        result = client.archive_messages(["msg_001", "msg_002"])

        assert result["modified"] == 2

    def test_bulk_archive_no_matches(self, gmail_service):
        gmail_service.users().messages().list().execute.return_value = {"messages": []}
        client = GmailClient(gmail_service)

        result = client.bulk_archive("from:nobody@example.com")

        assert result["archived"] == 0
        assert result["query"] == "from:nobody@example.com"

    def test_bulk_archive_with_matches(self, gmail_service):
        gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg_001"}, {"id": "msg_002"}]
        }
        gmail_service.users().messages().batchModify().execute.return_value = None
        client = GmailClient(gmail_service)

        result = client.bulk_archive("from:noreply@example.com")

        assert result["archived"] == 2

    def test_bulk_archive_pagination(self, gmail_service):
        # First page has nextPageToken, second page doesn't
        gmail_service.users().messages().list().execute.side_effect = [
            {
                "messages": [{"id": "msg_001"}, {"id": "msg_002"}],
                "nextPageToken": "token_page2",
            },
            {
                "messages": [{"id": "msg_003"}],
            },
        ]
        gmail_service.users().messages().batchModify().execute.return_value = None
        client = GmailClient(gmail_service)

        result = client.bulk_archive("from:noreply@example.com")

        assert result["archived"] == 3

    def test_bulk_archive_raises_on_failure(self, gmail_service):
        gmail_service.users().messages().list().execute.side_effect = Exception("Search failed")
        client = GmailClient(gmail_service)

        with pytest.raises(GmailAPIError, match="Failed to bulk archive"):
            client.bulk_archive("from:bad@example.com")


class TestModifyMessages:
    def test_empty_message_ids_returns_zero(self, gmail_service):
        client = GmailClient(gmail_service)

        result = client._modify_messages([])

        assert result["modified"] == 0

    def test_raises_on_api_failure(self, gmail_service):
        gmail_service.users().messages().batchModify().execute.side_effect = Exception("API error")
        client = GmailClient(gmail_service)

        with pytest.raises(GmailAPIError, match="Failed to modify messages"):
            client._modify_messages(["msg_001"])


class TestReadState:
    def test_mark_read(self, gmail_service):
        gmail_service.users().messages().batchModify().execute.return_value = None
        client = GmailClient(gmail_service)

        result = client.mark_read(["msg_001"])

        assert result["modified"] == 1

    def test_mark_unread(self, gmail_service):
        gmail_service.users().messages().batchModify().execute.return_value = None
        client = GmailClient(gmail_service)

        result = client.mark_unread(["msg_001"])

        assert result["modified"] == 1


class TestStarImportant:
    def test_star_messages(self, gmail_service):
        gmail_service.users().messages().batchModify().execute.return_value = None
        client = GmailClient(gmail_service)

        result = client.star_messages(["msg_001"])

        assert result["modified"] == 1

    def test_mark_important(self, gmail_service):
        gmail_service.users().messages().batchModify().execute.return_value = None
        client = GmailClient(gmail_service)

        result = client.mark_important(["msg_001"])

        assert result["modified"] == 1


class TestComposeSend:
    def test_create_draft(self, gmail_service):
        gmail_service.users().drafts().create().execute.return_value = {
            "id": "draft_001",
            "message": {"id": "msg_draft_001", "threadId": "thread_new"},
        }
        client = GmailClient(gmail_service)

        result = client.create_draft("alice@example.com", "Hello", "Hi there!")

        assert result["draft_id"] == "draft_001"
        assert result["message_id"] == "msg_draft_001"

    def test_create_draft_with_thread_and_cc(self, gmail_service):
        gmail_service.users().drafts().create().execute.return_value = {
            "id": "draft_002",
            "message": {"id": "msg_draft_002", "threadId": "thread_reply"},
        }
        client = GmailClient(gmail_service)

        result = client.create_draft(
            "alice@example.com",
            "Re: Hello",
            "Reply body",
            thread_id="thread_reply",
            cc="bob@example.com",
        )

        assert result["draft_id"] == "draft_002"
        assert result["thread_id"] == "thread_reply"

    def test_create_draft_raises_on_failure(self, gmail_service):
        gmail_service.users().drafts().create().execute.side_effect = Exception("Draft error")
        client = GmailClient(gmail_service)

        with pytest.raises(GmailAPIError, match="Failed to create draft"):
            client.create_draft("to@example.com", "Subject", "Body")

    def test_send_email(self, gmail_service):
        gmail_service.users().messages().send().execute.return_value = {
            "id": "msg_sent_001",
            "threadId": "thread_sent",
        }
        client = GmailClient(gmail_service)

        result = client.send_email("bob@example.com", "Test", "Test body")

        assert result["message_id"] == "msg_sent_001"

    def test_send_email_raises_on_failure(self, gmail_service):
        gmail_service.users().messages().send().execute.side_effect = Exception("Send error")
        client = GmailClient(gmail_service)

        with pytest.raises(GmailAPIError, match="Failed to send email"):
            client.send_email("to@example.com", "Subject", "Body")

    def test_send_draft(self, gmail_service):
        gmail_service.users().drafts().send().execute.return_value = {
            "id": "msg_sent_002",
            "threadId": "thread_sent_2",
        }
        client = GmailClient(gmail_service)

        result = client.send_draft("draft_001")

        assert result["message_id"] == "msg_sent_002"

    def test_send_draft_raises_on_failure(self, gmail_service):
        gmail_service.users().drafts().send().execute.side_effect = Exception("Draft send error")
        client = GmailClient(gmail_service)

        with pytest.raises(GmailAPIError, match="Failed to send draft"):
            client.send_draft("draft_bad")


class TestTrashMessages:
    def test_trash_succeeds(self, gmail_service):
        gmail_service.users().messages().trash().execute.return_value = None
        client = GmailClient(gmail_service)

        result = client.trash_messages(["msg_001", "msg_002"])

        assert result["succeeded"] == 2
        assert result["failed"] == 0
        assert result["errors"] == []

    def test_trash_partial_failure(self, gmail_service):
        call_count = 0

        def trash_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            mock = type("Mock", (), {})()
            if call_count == 1:
                mock.execute = lambda: None
            else:
                mock.execute = lambda: (_ for _ in ()).throw(Exception("Not found"))
            return mock

        gmail_service.users().messages().trash = trash_side_effect
        client = GmailClient(gmail_service)

        result = client.trash_messages(["msg_001", "msg_002"])

        assert result["succeeded"] == 1
        assert result["failed"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["message_id"] == "msg_002"
        assert "Not found" in result["errors"][0]["error"]


class TestAttachments:
    def test_list_attachments_with_file(self, gmail_service):
        gmail_service.users().messages().get().execute.return_value = {
            "payload": {
                "parts": [
                    {
                        "filename": "report.pdf",
                        "mimeType": "application/pdf",
                        "body": {"attachmentId": "att_1", "size": 12345},
                        "partId": "2",
                    }
                ]
            }
        }
        client = GmailClient(gmail_service)

        result = client.list_attachments("msg_001")

        assert len(result) == 1
        assert result[0]["filename"] == "report.pdf"
        assert result[0]["attachment_id"] == "att_1"

    def test_list_attachments_raises_on_failure(self, gmail_service):
        gmail_service.users().messages().get().execute.side_effect = Exception("Attachment error")
        client = GmailClient(gmail_service)

        with pytest.raises(GmailAPIError, match="Failed to list attachments"):
            client.list_attachments("msg_bad")

    def test_read_text_attachment(self, gmail_service):
        raw = base64.urlsafe_b64encode(b"name,value\nalice,42")
        gmail_service.users().messages().attachments().get().execute.return_value = {
            "data": raw.decode()
        }
        client = GmailClient(gmail_service)

        result = client.read_attachment_content("msg_001", "att_1", "data.csv", "text/csv")

        assert result["encoding"] == "text"
        assert "alice,42" in result["content"]

    def test_read_application_json_as_text(self, gmail_service):
        raw = base64.urlsafe_b64encode(b'{"key": "value"}')
        gmail_service.users().messages().attachments().get().execute.return_value = {
            "data": raw.decode()
        }
        client = GmailClient(gmail_service)

        result = client.read_attachment_content("msg_001", "att_1", "data.json", "application/json")

        assert result["encoding"] == "text"
        assert '"key"' in result["content"]

    def test_read_binary_attachment(self, gmail_service):
        raw = base64.urlsafe_b64encode(b"\x89PNG\r\n")
        gmail_service.users().messages().attachments().get().execute.return_value = {
            "data": raw.decode()
        }
        client = GmailClient(gmail_service)

        result = client.read_attachment_content("msg_001", "att_1", "img.png", "image/png")

        assert result["encoding"] == "base64"

    def test_get_attachment_raises_on_failure(self, gmail_service):
        gmail_service.users().messages().attachments().get().execute.side_effect = Exception(
            "Download error"
        )
        client = GmailClient(gmail_service)

        with pytest.raises(GmailAPIError, match="Failed to get attachment"):
            client.get_attachment("msg_bad", "att_bad")


class TestBuildMimeMessage:
    def test_basic_message(self):
        raw = GmailClient._build_mime_message("to@example.com", "Subject", "Body")
        decoded = base64.urlsafe_b64decode(raw).decode()

        assert "to@example.com" in decoded
        assert "Subject" in decoded
        assert "Body" in decoded

    def test_message_with_cc(self):
        raw = GmailClient._build_mime_message(
            "to@example.com", "Subject", "Body", cc="cc@example.com"
        )
        decoded = base64.urlsafe_b64decode(raw).decode()

        assert "cc@example.com" in decoded


class TestExtractBody:
    def test_simple_body(self):
        payload = {"body": {"data": base64.urlsafe_b64encode(b"Hello").decode()}}
        assert GmailClient._extract_body(payload) == "Hello"

    def test_empty_payload(self):
        assert GmailClient._extract_body({}) == ""

    def test_nested_multipart(self):
        inner_text = base64.urlsafe_b64encode(b"Nested text").decode()
        payload = {
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {"mimeType": "text/plain", "body": {"data": inner_text}},
                    ],
                }
            ]
        }
        assert GmailClient._extract_body(payload) == "Nested text"

    def test_html_only_fallback(self):
        html_data = base64.urlsafe_b64encode(b"<html>HTML only</html>").decode()
        payload = {
            "parts": [
                {"mimeType": "text/html", "body": {"data": html_data}},
            ]
        }
        assert GmailClient._extract_body(payload) == "<html>HTML only</html>"


class TestExtractAttachmentMetadata:
    def test_nested_parts(self):
        payload = {
            "parts": [
                {
                    "mimeType": "multipart/mixed",
                    "parts": [
                        {
                            "filename": "nested.txt",
                            "mimeType": "text/plain",
                            "body": {"attachmentId": "att_nested", "size": 100},
                            "partId": "1.1",
                        }
                    ],
                }
            ]
        }
        result = GmailClient._extract_attachment_metadata(payload)
        assert len(result) == 1
        assert result[0]["filename"] == "nested.txt"
