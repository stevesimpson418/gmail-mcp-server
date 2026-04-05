# Gmail MCP Server

[![CI](https://github.com/stevesimpson418/gmail-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/stevesimpson418/gmail-mcp-server/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/stevesimpson418/gmail-mcp-server/graph/badge.svg)](https://codecov.io/gh/stevesimpson418/gmail-mcp-server)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A local [MCP](https://modelcontextprotocol.io/) server that gives Claude native, tool-level access
to **Gmail**. Runs locally via stdio transport — all tokens and credentials stay on your machine.

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) for dependency management
- A Google account with the Gmail API enabled

## Quick Start

```bash
# Clone the repo
git clone https://github.com/stevesimpson418/gmail-mcp-server.git
cd gmail-mcp-server

# Install dependencies (creates .venv/ in the project directory)
uv sync
```

> **New to uv?** `uv sync` reads `pyproject.toml`, creates a `.venv/` virtualenv inside the
> project folder, and installs all dependencies into it. You don't need to activate it —
> `uv run <command>` handles that automatically.

## Setting up Gmail

### 1. Create a Google Cloud project

Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project
(or select an existing one).

### 2. Enable the Gmail API

Navigate to **APIs & Services > Library**, search for **Gmail API**, and click **Enable**.

### 3. Configure the OAuth consent screen

Before creating credentials, Google requires you to configure the OAuth consent screen. Go to
**APIs & Services > OAuth consent screen** (or **Google Auth Platform** if prompted).

1. Click **Get Started** (or **Configure Consent Screen**)
2. Fill in the required fields:
   - **App name** — a name for your own reference (e.g. "Gmail MCP Server")
   - **User support email** — your email address
3. Select an **Audience**:
   - **Internal** — only available if you're in a Google Workspace organisation
   - **External** — select this for personal Google accounts. The app starts in **testing
     mode**, which is fine for personal use — you just need to add yourself as a test user
4. **Contact information** — your email (Google uses this to notify you of project changes)
5. Click **Save**

> **About testing mode:** External apps in testing mode are limited to users you explicitly
> add to the test user list. This is perfectly fine for a local MCP server — you only need
> your own account. Tokens for test users expire after 7 days, requiring re-consent. If this
> becomes inconvenient, you can publish the app (no verification needed for sensitive scopes
> used with fewer than 100 users in testing mode, but publishing removes the 7-day expiry).

### 4. Add test users

Go to **APIs & Services > OAuth consent screen > Test users** (or **Audience** in the new
Google Auth Platform UI) and add your Google account email address.

### 5. Add OAuth scopes

Go to **APIs & Services > OAuth consent screen > Scopes** (or **Data Access** in the new UI)
and add the following scope:

<!-- markdownlint-disable MD013 -->

| Scope | Why it's needed |
|-------|----------------|
| `https://www.googleapis.com/auth/gmail.modify` | Read messages, modify labels (archive, star, mark read/unread, apply/remove labels), manage drafts, send emails, and move messages to trash. This is the minimum single scope that covers all server operations — narrower scopes like `gmail.readonly` or `gmail.send` don't cover label modification or trash. |

<!-- markdownlint-enable MD013 -->

This server does **not** request `mail.google.com` (full unrestricted access) — `gmail.modify`
is scoped to read/write operations and cannot permanently delete messages.

### 6. Create OAuth 2.0 credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Application type: **Desktop app**
4. Give it a name for your own reference (e.g. "Gmail MCP — My Laptop")
5. Click **Create**, then **Download JSON**
6. Save the file as `credentials/gmail_credentials.json` in this project

> **Security note:** The `credentials/` directory is gitignored — your credentials and tokens
> will never be committed to the repository.

### 7. Run the OAuth consent flow

```bash
uv run gmail-mcp-auth
```

A browser window will open — sign in with the Google account you added as a test user and
grant the requested permissions. The token is saved to `credentials/token.json` and
auto-refreshes after this.

To use custom paths:

```bash
uv run gmail-mcp-auth --credentials /path/to/creds.json --token /path/to/token.json
```

## Adding to Claude Desktop

Add the following to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS).

> **Tip:** Run `uv run which python` from the project directory to get the exact path for `command`.

```json
{
  "mcpServers": {
    "gmail": {
      "command": "/Users/you/gmail-mcp-server/.venv/bin/python",
      "args": ["-m", "gmail_mcp.server"],
      "env": {
        "GMAIL_CREDENTIALS_PATH": "/Users/you/gmail-mcp-server/credentials/gmail_credentials.json",
        "GMAIL_TOKEN_PATH": "/Users/you/gmail-mcp-server/credentials/token.json"
      }
    }
  }
}
```

The `env` block tells the server where to find your credentials at runtime. No `.env` file is
needed — the config passes these values directly.

Restart Claude Desktop after saving. You should see all Gmail tools in the tools menu.

## Adding to Claude Code CLI

Use the `claude mcp add` command to register the server. This works from any directory.

```bash
claude mcp add gmail-mcp-server \
  --transport stdio \
  --env GMAIL_CREDENTIALS_PATH=/path/to/gmail-mcp-server/credentials/gmail_credentials.json \
  --env GMAIL_TOKEN_PATH=/path/to/gmail-mcp-server/credentials/token.json \
  -- /path/to/gmail-mcp-server/.venv/bin/python -m gmail_mcp.server
```

Replace `/path/to/gmail-mcp-server` with the actual path where you cloned the repo.

> **Tip:** Run `uv run which python` from the project directory to get the exact `.venv/bin/python`
> path for the command.

By default this saves to `~/.claude.json` (user scope — available across all projects). To scope
it to a single project instead, add `--scope project` which writes to `.mcp.json` in your
project root.

To verify the server is registered:

```bash
claude mcp list
```

Restart Claude Code after adding. The Gmail tools should appear in the `/mcp` menu.

> **Note:** Claude Code CLI uses a different configuration from Claude Desktop. The `claude mcp add`
> command is the recommended way to register MCP servers — do not add them to
> `~/.claude/settings.json` as that file is used for permissions and hooks only.

## Updating

To pull the latest version and update dependencies:

```bash
cd /path/to/gmail-mcp-server
git pull
uv sync
```

Restart Claude Desktop or Claude Code CLI after updating.

If a new version changes OAuth scopes, you'll need to re-consent by running
`uv run gmail-mcp-auth` again.

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

### Local `.env` file

When running the server manually outside Claude Desktop/Code (e.g., for development or
debugging), you can create a `.env` file in the project root so the server picks up
credential paths without passing environment variables:

```text
GMAIL_CREDENTIALS_PATH=credentials/gmail_credentials.json
GMAIL_TOKEN_PATH=credentials/token.json
```

This is only needed for local development. The Claude Desktop and Claude Code CLI configs
pass these values directly via the `env` block.

### Packaging & Distribution

This server is currently distributed as source via git. To install:

```bash
git clone https://github.com/stevesimpson418/gmail-mcp-server.git
cd gmail-mcp-server
uv sync
```

This is the standard distribution model for local-stdio MCP servers today. The project is
already configured for wheel builds via hatchling, so future distribution options include:

- **PyPI** — publish to PyPI, then install with `uv tool install gmail-mcp-server` or
  `pip install gmail-mcp-server`. Would require adding a publish workflow to CI.
- **uvx** — once on PyPI, `uvx gmail-mcp-server` runs the server without cloning the repo.
  Claude Desktop/Code config would point to the uvx-managed binary instead of a local `.venv`.

## Releases

This project uses [release-please](https://github.com/googleapis/release-please) for automated
versioning and releases. The version is determined by
[Conventional Commits](https://www.conventionalcommits.org/):

- `fix:` commits bump the **patch** version (e.g. 0.1.0 → 0.1.1)
- `feat:` commits bump the **minor** version (e.g. 0.1.1 → 0.2.0)
- `BREAKING CHANGE` in the commit footer bumps the **major** version

When commits land on `main`, release-please opens (or updates) a Release PR that:

- Bumps the version in `pyproject.toml`
- Updates `CHANGELOG.md` with grouped entries

Merging the Release PR creates a git tag and GitHub Release automatically.

## License

MIT
