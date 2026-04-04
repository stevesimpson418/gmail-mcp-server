# Gmail MCP Server

[![CI](https://github.com/stevesimpson418/gmail-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/stevesimpson418/gmail-mcp-server/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/stevesimpson418/gmail-mcp-server/graph/badge.svg)](https://codecov.io/gh/stevesimpson418/gmail-mcp-server)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A local [MCP](https://modelcontextprotocol.io/) server that gives Claude native, tool-level access to **Gmail**. Runs locally via stdio transport — all tokens and credentials stay on your machine.

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) for dependency management
- A Google account with the Gmail API enabled

## Quick Start

```bash
# Clone the repo
git clone https://github.com/stevesimpson418/gmail-mcp-server.git
cd gmail-mcp-server

# Install dependencies
uv sync

# Configure your credentials
cp .env.example .env
# Edit .env — see setup instructions below
```

## Setting up Gmail

1. Create a [Google Cloud project](https://console.cloud.google.com/)
2. Enable the **Gmail API**: APIs & Services > Library > Gmail API
3. Create **OAuth 2.0 credentials**: APIs & Services > Credentials > Create > OAuth client ID
   - Application type: **Desktop app**
   - Download the JSON file and save it as `credentials/gmail_credentials.json`
4. Run the OAuth consent flow once to generate a token:

```bash
uv run python -c "
from gmail_mcp.auth import GmailAuth
auth = GmailAuth('credentials/gmail_credentials.json', 'credentials/token.json')
auth.get_service()
print('Token saved to credentials/token.json')
"
```

A browser window will open — sign in and grant permissions. The token auto-refreshes after this.

Update your `.env`:

```text
GMAIL_CREDENTIALS_PATH=credentials/gmail_credentials.json
GMAIL_TOKEN_PATH=credentials/token.json
```

## Adding to Claude Desktop

Add the following to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS).

> **Note:** Use the absolute path to the Python binary inside your virtualenv for `command`.

```json
{
  "mcpServers": {
    "gmail": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "gmail_mcp.server"],
      "env": {
        "GMAIL_CREDENTIALS_PATH": "/absolute/path/to/credentials/gmail_credentials.json",
        "GMAIL_TOKEN_PATH": "/absolute/path/to/credentials/token.json"
      }
    }
  }
}
```

Restart Claude Desktop after saving. You should see all Gmail tools in the tools menu.

## Adding to Claude Code

Add to your Claude Code settings (`.claude/settings.json` or global):

```json
{
  "mcpServers": {
    "gmail": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "gmail_mcp.server"],
      "env": {
        "GMAIL_CREDENTIALS_PATH": "/absolute/path/to/credentials/gmail_credentials.json",
        "GMAIL_TOKEN_PATH": "/absolute/path/to/credentials/token.json"
      }
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `search_gmail(query, max_results?)` | Search messages using Gmail query syntax (e.g. `is:unread in:inbox`) |
| `read_gmail_message(message_id)` | Read a full message including body text |
| `read_gmail_thread(thread_id)` | Read all messages in a thread |
| `list_gmail_labels()` | List all labels (system and user-created) |
| `list_gmail_attachments(message_id)` | List attachments on a message |
| `read_gmail_attachment(message_id, attachment_id, filename, mime_type)` | Read attachment content inline |
| `archive_gmail_messages(message_ids)` | Archive messages (remove from inbox) |
| `bulk_archive_gmail(query)` | Search and archive all matching messages in one call |
| `apply_gmail_label(message_ids, label_name)` | Apply a label to messages |
| `remove_gmail_label(message_ids, label_name)` | Remove a label from messages |
| `create_gmail_label(name, text_color?, background_color?)` | Create a new label |
| `mark_gmail_read(message_ids)` | Mark messages as read |
| `mark_gmail_unread(message_ids)` | Mark messages as unread |
| `star_gmail_message(message_ids)` | Star messages |
| `mark_gmail_important(message_ids)` | Mark messages as important |
| `create_gmail_draft(to, subject, body, thread_id?, cc?)` | Create a draft email |
| `send_gmail(to, subject, body, cc?)` | Send an email directly |
| `send_gmail_draft(draft_id)` | Send a previously created draft |
| `trash_gmail_messages(message_ids)` | Move messages to trash (recoverable for 30 days) |

### Usage Examples

**Triage your inbox:**

```text
1. search_gmail(query="is:unread in:inbox")          → see what's new
2. read_gmail_message(message_id="msg_123")           → read the full message
3. archive_gmail_messages(message_ids=["msg_123"])     → archive after reading
```

**Bulk cleanup:**

```text
bulk_archive_gmail(query="from:noreply@marketing.com in:inbox")
bulk_archive_gmail(query="is:unread in:inbox older_than:7d subject:newsletter")
```

**Draft a reply:**

```text
create_gmail_draft(
    to="alice@example.com",
    subject="Re: Meeting",
    body="Sounds good, see you then!",
    thread_id="thread_abc"
)
```

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest -v

# Run tests with coverage
uv run pytest --cov=gmail_mcp --cov-report=term-missing

# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Install git hooks
lefthook install
```

## License

MIT
