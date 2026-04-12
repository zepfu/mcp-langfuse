# mcp-langfuse

Spec-driven MCP server for the Langfuse public API.

## What it does

- Loads a vendored snapshot of the official Langfuse OpenAPI spec.
- Registers one MCP tool per Langfuse public operation.
- Uses Basic Auth with Langfuse public and secret keys.
- Returns both MCP text content and structured JSON output for tool calls.

## Configuration

Set these environment variables before running the server:

- `LANGFUSE_BASE_URL`
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_TIMEOUT_SECONDS`
- `LANGFUSE_VERIFY_SSL`
- `LANGFUSE_TOOL_PROFILES`
- `LANGFUSE_TOOL_FAMILIES_ENABLE`
- `LANGFUSE_TOOL_FAMILIES_DISABLE`
- `LANGFUSE_TOOLS_ENABLE`
- `LANGFUSE_TOOLS_DISABLE`
- `LANGFUSE_ENABLE_WRITE_TOOLS`
- `LANGFUSE_ENABLE_DESTRUCTIVE_TOOLS`
- `LANGFUSE_ENABLE_ADMIN_TOOLS`
- `LANGFUSE_ENABLE_LEGACY_TOOLS`

Defaults:

- `LANGFUSE_BASE_URL=https://cloud.langfuse.com`
- `LANGFUSE_TIMEOUT_SECONDS=30`
- `LANGFUSE_VERIFY_SSL=true`
- `LANGFUSE_TOOL_PROFILES=minimal`
- write, destructive, admin, and legacy tool gates default to `false`

Common profiles:

- `minimal`: small read-only observability set
- `observe_read`: broader observability and metrics
- `ingest`: ingestion, OTEL, and media
- `evals`: annotation, scoring, comments, prompts
- `datasets`: dataset and run management
- `prompts`: prompt management only
- `project_admin`: project-scoped admin families
- `org_admin`: organization and SCIM families
- `admin`: all admin families
- `legacy`: legacy endpoints
- `full`: every current public API family

Examples:

```bash
LANGFUSE_TOOL_PROFILES=observe_read,prompts python3.14 -m uv run mcp-langfuse
```

```bash
LANGFUSE_TOOL_PROFILES= \
LANGFUSE_TOOLS_ENABLE=langfuse_projects_delete \
python3.14 -m uv run mcp-langfuse
```

## Development

```bash
python3.14 -m uv sync
python3.14 -m uv run pytest
python3.14 -m uv run ruff check .
python3.14 -m uv run mypy
python3.14 -m uv run vulture
python3.14 -m uv run pre-commit install
python3.14 -m uv run pre-commit run --all-files
```

## Run

```bash
python3.14 -m uv run mcp-langfuse
```

## Tool Reference

The generated MCP tool reference lives in `TOOLS.md`.
