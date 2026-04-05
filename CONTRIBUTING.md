# Contributing

Thanks for your interest in contributing! This guide covers everything you need to get started.

## Development setup

1. Clone the repo and install dependencies:

   ```bash
   git clone https://github.com/stevesimpson418/gmail-mcp-server.git
   cd gmail-mcp-server
   uv sync --dev
   ```

2. Install git hooks:

   ```bash
   lefthook install
   ```

3. Run the test suite to verify your setup:

   ```bash
   uv run pytest -v
   ```

## Making changes

1. **Create a feature branch** from `main` — e.g. `feat/add-search-filter` or `fix/token-refresh`
2. **Write tests alongside your code** — TDD is preferred
3. **Run tests and lint before committing:**

   ```bash
   uv run pytest -v
   uv run ruff check src/ tests/
   uv run ruff format src/ tests/
   ```

4. **Use Conventional Commits** for all commit messages:
   - `feat(tools): add label search tool`
   - `fix(auth): handle expired refresh token`
   - `docs(readme): update setup instructions`

   The `type(scope): description` format is enforced by commitlint via lefthook.

5. **Open a pull request** against `main` — fill in the PR template

## Code style

- **Formatter/linter:** Ruff (config in `ruff.toml`)
- **Line length:** 100 characters
- **Quotes:** Double quotes
- **Imports:** Sorted by isort (via ruff)

Lefthook runs ruff automatically on commit, so most style issues are caught before push.

## Architecture

See [CLAUDE.md](CLAUDE.md) for the full architecture pattern. The short version:

- `server.py` — entry point, creates FastMCP instance
- `tools.py` — MCP tool definitions (thin wrappers)
- `client.py` — Gmail API logic
- `auth.py` — OAuth2 flow
- `exceptions.py` — domain exceptions

Tools should be thin wrappers that delegate to the client.

## Reporting bugs

Use the [Bug Report](https://github.com/stevesimpson418/gmail-mcp-server/issues/new?template=bug_report.yml) template.

## Suggesting features

Use the [Feature Request](https://github.com/stevesimpson418/gmail-mcp-server/issues/new?template=feature_request.yml) template.
