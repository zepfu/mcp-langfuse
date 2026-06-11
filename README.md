# mcp-langfuse

Spec-driven MCP server for the Langfuse public API.

## What it does

- Loads a vendored snapshot of the official Langfuse OpenAPI spec.
- Registers one MCP tool per Langfuse public operation.
- Uses Basic Auth with Langfuse public and secret keys.
- Returns both MCP text content and structured JSON output for tool calls.
- Exposes only the tools enabled by the current profile and flag configuration.

## Run

This is a stdio MCP server. It does not open an HTTP port.

```bash
python3.14 -m uv run mcp-langfuse
```

## Server Configuration

The server reads settings from:

- process environment variables passed by the MCP client
- a `.env` file in the current working directory

If you want the server to auto-load `.env`, configure the client to start the process with `cwd`
set to the repository root. If your client passes `env` directly, `cwd` is optional.

### Required Settings

- `LANGFUSE_PUBLIC_KEY`: Langfuse public API key used as the Basic Auth username
- `LANGFUSE_SECRET_KEY`: Langfuse secret API key used as the Basic Auth password

### Optional Settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `LANGFUSE_BASE_URL` | `https://cloud.langfuse.com` | Base URL for the Langfuse API |
| `LANGFUSE_TIMEOUT_SECONDS` | `30` | Request timeout for outbound API calls |
| `LANGFUSE_VERIFY_SSL` | `true` | Enable or disable TLS certificate verification |
| `LANGFUSE_RETRY_ATTEMPTS` | `2` | Retries for `GET` requests only, on HTTP 429/503. Honors an integer `Retry-After` header; otherwise uses exponential backoff capped at 10s |
| `LANGFUSE_MAX_RESPONSE_BYTES` | `200000` | Responses whose data exceeds this byte length are replaced by `{"truncated": true, "data_bytes": N, "preview": "..."}` |
| `LANGFUSE_TOOL_PROFILES` | `minimal` | Comma-separated profile list used to seed the visible tool set |
| `LANGFUSE_TOOL_FAMILIES_ENABLE` | unset | Additional Langfuse API families to expose |
| `LANGFUSE_TOOL_FAMILIES_DISABLE` | unset | Langfuse API families to hide |
| `LANGFUSE_TOOLS_ENABLE` | unset | Individual MCP tools to force-enable |
| `LANGFUSE_TOOLS_DISABLE` | unset | Individual MCP tools to force-disable |
| `LANGFUSE_ENABLE_WRITE_TOOLS` | `false` | Allow non-`GET`, non-`DELETE` operations |
| `LANGFUSE_ENABLE_DESTRUCTIVE_TOOLS` | `false` | Allow `DELETE` operations (sufficient on its own; does not require the write flag) |
| `LANGFUSE_ENABLE_ADMIN_TOOLS` | `false` | Allow admin-family tools |
| `LANGFUSE_ENABLE_LEGACY_TOOLS` | `false` | Allow legacy API families |

### Tool Selection Model

Tool loading happens before MCP `tools/list`, so clients only discover enabled tools.

Selection precedence is:

1. Start from `LANGFUSE_TOOL_PROFILES`
2. Add `LANGFUSE_TOOL_FAMILIES_ENABLE`
3. Remove `LANGFUSE_TOOL_FAMILIES_DISABLE`
4. Apply the write, destructive, admin, and legacy safety gates
5. Apply `LANGFUSE_TOOLS_ENABLE` and `LANGFUSE_TOOLS_DISABLE`

Notes:

- `LANGFUSE_TOOLS_ENABLE` can force a tool on even if its family is not selected or a safety gate would normally hide it.
- `LANGFUSE_TOOLS_DISABLE` always hides that tool.
- If a client attempts to call a hidden but known tool directly, the server returns a
  `tool_not_enabled` error.
- `LANGFUSE_TOOL_PROFILES=""` (set but empty) selects **no** profiles. This pairs with
  `LANGFUSE_TOOLS_ENABLE` to build allowlist-only configurations; the server logs a startup
  warning when zero tools are enabled.
- HTTP redirects are treated as configuration errors: the client does not follow them. Fix
  `LANGFUSE_BASE_URL` instead.
- Python 3.14 is a deliberate floor. The project targets a standardized toolchain with a
  lockfile resolved against 3.14; older interpreters are untested and unsupported.

### Profiles

Common profiles:

- `minimal`: small default read-only observability set
- `observe_read`: broader read-only observability and metrics
- `ingest`: ingestion, OTEL, and media
- `evals`: annotation, scoring, comments, prompts
- `datasets`: dataset and run management
- `prompts`: prompt management only
- `project_admin`: project-scoped admin families
- `org_admin`: organization and SCIM families
- `admin`: all admin families
- `legacy`: legacy endpoints
- `full`: every current public API family

The generated tool catalog in `TOOLS.md` documents the current families and the MCP tool names
behind them.

### `.env` Example

```bash
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_TOOL_PROFILES=observe_read,prompts
LANGFUSE_ENABLE_WRITE_TOOLS=false
LANGFUSE_ENABLE_DESTRUCTIVE_TOOLS=false
LANGFUSE_ENABLE_ADMIN_TOOLS=false
LANGFUSE_ENABLE_LEGACY_TOOLS=false
```

### MCP Client Entry Example

Any stdio MCP client needs to launch the same command and supply the environment. A typical entry
looks like this:

```json
{
  "command": "python3.14",
  "args": ["-m", "uv", "run", "--project", "/path/to/mcp-langfuse", "mcp-langfuse"],
  "cwd": "/path/to/mcp-langfuse",
  "env": {
    "LANGFUSE_PUBLIC_KEY": "pk-lf-...",
    "LANGFUSE_SECRET_KEY": "sk-lf-...",
    "LANGFUSE_TOOL_PROFILES": "observe_read,prompts",
    "LANGFUSE_ENABLE_WRITE_TOOLS": "false",
    "LANGFUSE_ENABLE_ADMIN_TOOLS": "false"
  }
}
```

### Launch Examples

```bash
LANGFUSE_TOOL_PROFILES=observe_read,prompts \
python3.14 -m uv run mcp-langfuse
```

```bash
LANGFUSE_TOOL_PROFILES= \
LANGFUSE_TOOLS_ENABLE=langfuse_projects_delete \
python3.14 -m uv run mcp-langfuse
```

```bash
LANGFUSE_TOOL_PROFILES=admin \
LANGFUSE_ENABLE_WRITE_TOOLS=true \
LANGFUSE_ENABLE_DESTRUCTIVE_TOOLS=true \
LANGFUSE_ENABLE_ADMIN_TOOLS=true \
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

## Tool Reference

The generated MCP tool reference lives in `TOOLS.md`.
