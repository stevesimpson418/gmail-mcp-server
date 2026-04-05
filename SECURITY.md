# Security Policy

## Reporting a vulnerability

If you discover a security vulnerability, please report it through
[GitHub's private vulnerability reporting](https://github.com/stevesimpson418/gmail-mcp-server/security/advisories/new).

**Do not open a public issue for security vulnerabilities.**

## What to expect

- **Acknowledgement** within 48 hours of your report
- **Assessment and fix** within 30 days for confirmed vulnerabilities
- **Coordinated disclosure** — we will work with you on timing before any public announcement

## Scope

This is a local stdio MCP server. The primary security concerns are:

- OAuth token and credential handling
- Input validation on tool parameters
- Dependency vulnerabilities

## Supported versions

Only the latest release is supported with security updates.
