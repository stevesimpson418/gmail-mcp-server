# CLAUDE.md — Project Intelligence

## Project Overview

Gmail MCP server built with FastMCP. Provides Claude with native tool-level access to Gmail
via OAuth2. Runs locally via stdio transport — all tokens and credentials stay on the user's machine.

## Tech Stack

- **Language:** Python 3.14+
- **Package manager:** uv (never use pip directly)
- **MCP framework:** FastMCP 2.0+
- **Google APIs:** google-api-python-client, google-auth-oauthlib
- **Linting/formatting:** Ruff (config in ruff.toml)
- **Testing:** pytest + pytest-cov
- **Git hooks:** Lefthook (ruff, markdownlint, shellcheck, shfmt, commitlint)
- **CI:** GitHub Actions (lint + test matrix)

## Project Structure

```text
src/gmail_mcp/                # Source code (src layout)
  server.py                   # Entry point — FastMCP init + tool registration
  tools.py                    # MCP tool definitions (register_gmail_tools)
  client.py                   # Gmail API client wrapper
  auth.py                     # OAuth2 authentication flow
  exceptions.py               # Custom exception classes
tests/                        # Pytest test suite
  conftest.py                 # Shared fixtures (mock service, sample messages)
  test_auth.py                # OAuth authentication tests
  test_client.py              # Gmail client tests
  test_tools.py               # Tool registration tests
credentials/                  # OAuth credentials (gitignored)
```

## Key Commands

```bash
uv sync --dev                                          # Install all deps
uv run pytest -v                                       # Run tests
uv run pytest --cov=gmail_mcp --cov-report=term-missing  # Coverage
uv run ruff check src/ tests/                          # Lint
uv run ruff format src/ tests/                         # Format
lefthook install                                       # Install git hooks
```

## Conventions

- **Commits:** Conventional Commits format — `type(scope): description`
- **Line length:** 100 characters
- **Quotes:** Double quotes (enforced by ruff)
- **Imports:** Sorted by isort via ruff, first-party package declared in ruff.toml
- **Tests:** Mirror source structure, use fixtures in conftest.py
- **Entry point:** `server.py:main()` — registered as console script in pyproject.toml

## Architecture Pattern

1. `server.py` creates the FastMCP instance and calls `register_gmail_tools(mcp)`
2. `tools.py` defines all MCP tools using `@mcp.tool()` decorators inside `register_gmail_tools()`
3. `client.py` wraps the Gmail API (keeps tool definitions thin)
4. `auth.py` handles OAuth2 flow and token refresh
5. `exceptions.py` defines domain-specific exceptions

Tools should be thin wrappers that delegate to the client. Keep business logic in the client.

## Development Workflow

- **New features:** Use `/feature-dev:feature-dev` if available — it handles codebase
  analysis, architecture planning, and guided implementation.
- **Branching:** Create a feature branch (`feat/<description>`) before starting work.
  Never commit directly to main — branch protection enforces PRs.
- **TDD:** Write tests alongside code. Run `uv run pytest -v` early and often.
- **Review cycle:** Run `/pr-review-toolkit:review-pr code` before every commit.
  Run `/pr-review-toolkit:review-pr all parallel` before pushing or creating a PR.
- **Merging:** PRs auto-merge to main once CI passes (squash merge). After merge,
  run `/commit-commands:clean_gone` to clean up local branches. Release-please will
  automatically update the Release PR with the new changes.
- **Releases:** Automated via [release-please](https://github.com/googleapis/release-please).
  Conventional commits on main are tracked automatically. Release-please maintains an open
  "Release PR" that bumps `version` in `pyproject.toml` and updates `CHANGELOG.md`. When
  ready to release, merge the Release PR — this creates the git tag and GitHub Release.
  To perform a release: check for an open release-please PR, review the changelog, and merge it.
