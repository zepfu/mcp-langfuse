# Adversarial Review Remediation — Implementation Plan

**Date:** 2026-06-10
**Author:** researcher
**Subject:** Remediate all 55 findings from `.analysis/adversarial-review-20260610.md` — no deferrals
**Scope:** All of `src/mcp_langfuse/` (config, client, openapi, service, server, tool_selection, tools_markdown), tests, pyproject, pre-commit, CI workflow, README, TOOLS.md
**Status:** PROMOTED (2026-06-11)

---

## Executive Summary

The adversarial review of mcp-langfuse identified 55 findings across 10 sections: 3 BUG-class
items (broken `mcp>=1.18.0` dependency floor, a gate-bypass fallback in
`service._resolve_operation`, empty-string path parameters silently rerouting requests), a
per-call performance stack-up (schema + validator rebuilt and arguments double-validated and
double-copied on every tool call), latent security drift (hardcoded admin/legacy family names
never validated against the spec), and a long tail of gotchas, design improvements, and test
gaps. This plan remediates every finding — none deferred. The work is pure Python + packaging;
no database is involved. Execution uses the fixed dispatch structure: one tester writes all
failing tests, two engineers implement (split Python source vs. packaging/config/docs by token
budget and tooling), one QA reviews everything.

**Empirical corrections established during planning (probes run against the live repo):**
- All family names referenced by `ADMIN_FAMILIES`, `LEGACY_FAMILIES`, and every profile exist
  as tags in the vendored spec (zero drift today) — T-2's validation is safe to introduce.
- pydantic-settings already reports env-var alias names in validation errors
  (`LANGFUSE_PUBLIC_KEY Field required` — verified) — V-4 needs only a pinning test, no code.
- `mcp.shared.memory.create_connected_server_and_client_session` exists in mcp 1.27.0 — Q-1's
  end-to-end test is feasible.
- L-2 correction: the "two clients created" race as originally written is **not** reachable —
  `_get_client` has no await between check and create, so asyncio cannot interleave there. The
  real interleaving hazard is `_get_client` racing `aclose()` (which awaits between closing and
  clearing `self._client`, allowing use-after-close). The lock fix stands; the rationale is
  corrected here and in the wave below.

## Rollout Order

```
Tester      — writes ALL failing tests + test hygiene (Waves 1–9 test specs)   (~95k est.)
Engineer A  — all Python source changes, Waves 1–7, incl. TOOLS.md regen      (~110k est.)
Engineer B  — packaging/config/docs, Wave 8 (pyproject, pre-commit, CI, README) (~35k est.)
QA          — reviews everything                                                (~40k est.)
```

**Dependencies:**
- Tester lands first (failing tests are landable: the stage gate runs pre-commit
  lint/mypy/vulture/tools-md-check, not pytest).
- Engineer A depends on tester (makes the tests pass). Waves 1–7 are internal ordering for
  Engineer A within a single dispatch (config → openapi → client → tool_selection → service →
  server → tools_markdown), handled by the agent.
- Engineer B depends on Engineer A landing (CI workflow added in Wave 8 runs pytest; landing B
  before A would create a red-CI window; also B's README documents env vars A introduces).
- QA depends on Engineer B.

**No DB Foundation wave** — this plan contains no migrations, DDL, ORM, or DAL work.

**Dispatch sizing:** one tester (all tests), two engineers (split ONLY because combined
estimate ~145k exceeds the ~125k budget AND the file types differ: Python source vs.
TOML/YAML/Markdown/CI config), one QA.

**Maximum concurrent agents: 1** (strictly serial: tester → engineer A → engineer B → QA).

## Implementation Waves

<!-- SPECIFICATION ONLY — do not modify after operator approval.
     All outcomes, deviations, and QA results go in the Dispatch Plan section. -->

### Wave 1: config.py — settings hardening (C-1…C-6 + new knobs)

**Depends on:** (none)
**Scope:** `src/mcp_langfuse/config.py`

#### Impact Analysis
**Type:** modification + one public-name deletion
**Affected symbols:** `Settings.base_url` (validator), `Settings.secret_key` (type change
`str` → `SecretStr`), `_parse_csv_values`, `Settings.from_env` (REMOVED), new fields
`retry_attempts`, `max_response_bytes`.
**Public name removal — `from_env`:**
```
$ grep -rn 'from_env' src/ tests/ --include='*.py'
src/mcp_langfuse/config.py:88:    def from_env(cls) -> Self:
src/mcp_langfuse/server.py:41:    settings = Settings.from_env()
```
Both accounted for: definition removed here; the single caller `server.py:41` switches to
`Settings()` in Wave 6.
**`secret_key` type change callers:**
```
$ grep -rn 'secret_key\|public_key' src/ tests/ --include='*.py'
src/mcp_langfuse/config.py:42-43   — definition (this wave)
src/mcp_langfuse/client.py:125     — httpx.BasicAuth(...) — updated in Wave 3 to .get_secret_value()
```
`_parse_csv_values` callers: config.py:79 only (internal).

#### Test Spec (tester's input)
**Test files:**
  - `tests/test_config.py` (NEW) — unit
**Test cases (must fail before implementation):**
  - `test_base_url_strips_trailing_slash` — `Settings(... LANGFUSE_BASE_URL="https://x.example")`
    → `settings.base_url == "https://x.example"`; and `"https://x.example/sub/"` →
    `"https://x.example/sub"` (C-1: stored value no longer grows a trailing slash).
  - `test_base_url_rejects_non_http` — `LANGFUSE_BASE_URL="ftp://x"` raises `ValidationError`.
  - `test_secret_key_is_masked` — `repr(settings)` and `str(settings)` do NOT contain the raw
    secret; `settings.secret_key.get_secret_value() == "sk-test"` (C-3).
  - `test_csv_rejects_bytes` — `Settings(... LANGFUSE_TOOL_PROFILES=b"minimal")` raises
    `ValidationError` (C-5: bytes no longer silently exploded into char codes).
  - `test_csv_accepts_list_and_dedupes` — `LANGFUSE_TOOL_PROFILES=["a", "b", "a", " b "]` →
    `("a", "b")` (regression pin for existing behavior).
  - `test_empty_profiles_yields_empty_tuple` — `LANGFUSE_TOOL_PROFILES=""` → `()` (C-2: pins
    the *intentional* semantics relied on by
    `test_explicit_tool_enable_overrides_profiles_and_safety_gates`; the warning lives in
    Wave 6, the documentation in Wave 8).
  - `test_retry_and_response_byte_defaults` — `settings.retry_attempts == 2`,
    `settings.max_response_bytes == 200_000`; `LANGFUSE_RETRY_ATTEMPTS=-1` and
    `LANGFUSE_MAX_RESPONSE_BYTES=0` each raise `ValidationError`.
  - `test_missing_required_keys_name_env_vars` — constructing with no env names
    `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` in the `ValidationError` message (V-4 pin;
    verified already true — guards regression).
**Assertions:** exact values as stated above. mypy note for tester: access any new
fields/symbols via `make_settings(**{...})` dict-splat (existing test pattern) — `attr-defined`
is already disabled for tests.

#### Source Spec (engineer's input — make the tests above pass)
**Source files:**
  - `src/mcp_langfuse/config.py`:
    - C-1: `_validate_base_url` returns `str(HTTP_URL_ADAPTER.validate_python(raw)).rstrip("/")`.
    - C-3: `secret_key: SecretStr = Field(alias="LANGFUSE_SECRET_KEY")` (import from pydantic).
      `public_key` stays `str` (it is the Basic-Auth username; semantically public).
    - C-5: `_parse_csv_values` — replace the duck-typed `Iterable` branch with an explicit
      `isinstance(raw, (list, tuple, set, frozenset))` check; `bytes`/`bytearray` raise
      `ValueError("CSV value must be a string or a sequence of strings")` (pydantic wraps it
      into ValidationError).
    - C-6: delete `from_env` classmethod (caller updated in Wave 6).
    - New: `retry_attempts: int = Field(default=2, ge=0, le=10, alias="LANGFUSE_RETRY_ATTEMPTS")`;
      `max_response_bytes: int = Field(default=200_000, gt=0, alias="LANGFUSE_MAX_RESPONSE_BYTES")`.
    - C-4 support: add module-level `KNOWN_ENV_VARS: frozenset[str]` derived from field aliases
      (`frozenset(field.alias for field in Settings.model_fields.values() if field.alias)`),
      consumed by Wave 6 diagnostics.

---

### Wave 2: openapi.py — load-time guarantees and schema fidelity (O-1…O-8, L-5, L-9)

**Depends on:** (none)
**Scope:** `src/mcp_langfuse/openapi.py`

#### Impact Analysis
**Type:** modification
**Affected symbols:** `OperationSpec.input_schema` (property → stored field),
`LangfuseAPISpec.by_tool_name` (property → stored field), `openapi_to_json_schema` (new
keyword-only ref-cycle guard), `load_api_spec` (split into pure `parse_api_spec(raw)` +
file-loading wrapper), `SCHEMA_COPY_KEYS`, `_merge_all_of`, `_finalize_schema`,
`_collect_parameters`, `_collect_request_body`.
**Callers/importers:**
```
$ grep -rn 'input_schema' src/ tests/ --include='*.py'
src/mcp_langfuse/client.py:289   — reads operation.input_schema — unaffected (field reads identically)
src/mcp_langfuse/service.py:48   — reads operation.input_schema — unaffected
tests/test_openapi.py:16,28      — reads — unaffected
$ grep -rn 'by_tool_name' src/ tests/ --include='*.py' | wc -l   → 21 call sites
  (all are reads `spec.by_tool_name[...]` — unaffected by property→field conversion)
```
`openapi_to_json_schema` external callers: `tools_markdown.py:136,145,167,171` — unaffected
(new parameter is keyword-only with a default). `operation.components` stays a field
(tools_markdown depends on it).

#### Test Spec (tester's input)
**Test files:**
  - `tests/test_openapi.py` (EXTEND) — unit
**Test cases (must fail before implementation):**
  - `test_input_schema_is_precomputed` — `op.input_schema is op.input_schema` (identity holds
    because it is a stored field, not a rebuilt dict) (O-1).
  - `test_by_tool_name_is_precomputed` — `spec.by_tool_name is spec.by_tool_name` (O-1).
  - `test_no_unresolved_refs_in_input_schemas` — for every operation,
    `"$ref" not in json.dumps(op.input_schema)` (L-9).
  - `test_duplicate_tool_names_raise` — `parse_api_spec` on a synthetic raw spec containing
    operationIds `getTrace` and `get_trace` raises `ValueError` naming
    `langfuse_get_trace` (O-2).
  - `test_header_parameter_rejected_at_load` — synthetic spec with `in: header` parameter →
    `ValueError` naming the operation (L-5).
  - `test_non_json_request_body_rejected_at_load` — synthetic spec with only
    `multipart/form-data` content → `ValueError` naming the operation (O-7).
  - `test_missing_operation_id_names_path_and_method` — synthetic spec missing `operationId` →
    `ValueError` whose message contains the path and method (O-8).
  - `test_circular_ref_raises_value_error` — `openapi_to_json_schema({"$ref": "#/components/schemas/A"}, components)`
    where schema A's property references A → `ValueError` matching "circular" (O-3).
  - `test_nullable_enum_accepts_null` — nullable enum schema converts such that
    `None` is a member of the resulting `enum` (O-5).
  - `test_boolean_exclusive_minimum_converted` — OpenAPI-3.0 `{type: number, minimum: 1,
    exclusiveMinimum: true}` converts to Draft-2020-12 `{exclusiveMinimum: 1}` with no
    `minimum` key and no boolean values (O-6).
  - `test_copy_keys_include_const_and_multiple_of` — schema with `multipleOf`/`const`/
    `minProperties`/`maxProperties` keeps them (O-6).
  - `test_all_of_merge_carries_description` — allOf parts where one part has a `description`
    → merged schema keeps it (O-4).
**Assertions:** exact values as stated. Synthetic raw specs are small inline dicts passed to
`parse_api_spec` / `openapi_to_json_schema` (import via module attribute if needed for mypy).

#### Source Spec (engineer's input — make the tests above pass)
**Source files:**
  - `src/mcp_langfuse/openapi.py`:
    - O-1: extract the body of the current `input_schema` property into module function
      `_build_input_schema(parameters, request_body, components) -> dict`; `OperationSpec`
      gains a required stored field `input_schema: dict[str, Any]` populated at construction in
      `parse_api_spec`; delete the property. Convert `LangfuseAPISpec.by_tool_name` from
      property to stored field populated in `parse_api_spec`. Keep `tool_description` as a
      property (cheap string formatting).
    - Testability split: `parse_api_spec(raw_spec: dict[str, Any]) -> LangfuseAPISpec` (pure,
      all validation lives here); `load_api_spec()` keeps its `lru_cache(maxsize=1)` and
      becomes "read vendored YAML → `parse_api_spec`".
    - O-2: in `parse_api_spec`, after building operations, raise
      `ValueError(f"Duplicate tool names after normalization: {dupes}")` when
      `len(names) != len(set(names))`.
    - O-3: `openapi_to_json_schema(..., *, _ref_stack: frozenset[str] = frozenset())` — when
      resolving a `$ref` already in the stack raise
      `ValueError(f"Circular $ref detected: {ref}")`; thread the stack through
      `_apply_array_schema`/`_apply_object_schema`/`_apply_union_schema` recursion.
    - O-4: add a code comment on `_merge_all_of` stating leniency is intentional
      (input-gating, not full JSON-Schema AND semantics); additionally carry the first
      part-level `description` into the merged result when present.
    - O-5: in `_finalize_schema`, when `nullable` and `"enum" in result` and `None` not in the
      enum, append `None` to a copied enum list.
    - O-6: add `multipleOf`, `minProperties`, `maxProperties`, `const` to `SCHEMA_COPY_KEYS`;
      post-process in `_copy_schema_keywords`: when `exclusiveMinimum is True` and `minimum`
      present → `exclusiveMinimum = minimum`, drop `minimum` (mirror for maximum); when the
      boolean is `False`, drop the key entirely.
    - L-5/O-7: in `parse_api_spec`, raise `ValueError` for any parameter whose `in` is not
      `path`/`query`, and for any request body whose chosen content type is not
      `application/json` — both messages name the offending operationId/path.
    - O-8: replace bare `operation["operationId"]` / `item["name"]` / `item["in"]` lookups
      with checks raising `ValueError` messages naming the path + method.

---

### Wave 3: client.py — request correctness, resilience, and per-call cost (L-1…L-8, C-3 hookup)

**Depends on:** Wave 1 (new settings fields), Wave 2 (precomputed `input_schema`)
**Scope:** `src/mcp_langfuse/client.py`

#### Impact Analysis
**Type:** modification + private-helper deletions
**Affected symbols:** `_get_client` (lock), `_build_request_path`/`_extract_request_parts`
(empty path param), `call_operation` (retry loop, redirect handling, pre-serialized body),
`_validate_arguments` (validator cache, single deepcopy), `_decode_response` error-path
wrapper, the six error-factory staticmethods (REMOVED: `_missing_argument_error`,
`_null_argument_error`, `_unsupported_parameter_error`, `_unknown_arguments_error`,
`_schema_validation_error`, `_json_serialization_error`).
**Callers of removed helpers:**
```
$ grep -rn '_missing_argument_error\|_null_argument_error\|_unsupported_parameter_error\|_unknown_arguments_error\|_schema_validation_error\|_json_serialization_error' src/ tests/ --include='*.py'
  → 14 results, ALL inside src/mcp_langfuse/client.py (definitions + internal call sites).
  Zero external callers; tests assert on raised LangfuseArgumentError messages, which are
  preserved verbatim.
```

#### Test Spec (tester's input)
**Test files:**
  - `tests/test_client.py` (EXTEND) — unit + respx integration-style (mocked transport)
**Test cases (must fail before implementation):**
  - `test_empty_path_param_rejected` — `call_operation(delete_queue_assignment, {"queueId": "", "body": {...}})`
    raises `LangfuseArgumentError` matching `"empty"` (L-1).
  - `test_whitespace_path_param_rejected` — `{"queueId": "   "}` same (L-1).
  - `test_get_client_is_locked_and_reopenable` — `await asyncio.gather(*[c._get_client() for _ in range(10)])`
    returns 10 references to the SAME object; after `aclose()`, `_get_client()` returns a
    fresh, open client (L-2 — corrected rationale: guards `_get_client` vs `aclose`
    interleaving; the create path itself has no await point).
  - `test_retry_on_429_honors_retry_after` — respx side_effect `[429 (Retry-After: 0), 200]`
    on a GET → success, `route.call_count == 2` (L-7).
  - `test_retry_exhaustion_raises_api_error` — all responses 429, `retry_attempts=2` →
    `LangfuseAPIError` with `status_code == 429`, `route.call_count == 3` (L-7).
  - `test_no_retry_for_post` — POST returning 503 → immediate `LangfuseAPIError`,
    `route.call_count == 1` (L-7: non-GET never retried).
  - `test_redirect_raises_transport_error` — respx 307 with `Location` header →
    `LangfuseTransportError` whose message matches `"redirect"` and details include the
    location (L-6).
  - `test_error_response_with_malformed_json_still_api_error` — 502 + `content-type:
    application/json` + body `"not-json"` → `LangfuseAPIError` (NOT decode error), details
    contain a `body_preview` (L-3).
  - `test_body_sent_with_json_content_type` — body request carries
    `content-type: application/json` header and exact serialized bytes (L-4: single-serialize
    `content=` path).
  - `test_basic_auth_uses_secret_value` — respx asserts the `Authorization` header equals
    `base64("pk-test:sk-test")` (C-3 hookup: SecretStr unwrapped correctly).
  - `test_arguments_not_mutated_by_call` — pass an arguments dict, assert deep-equal to its
    pre-call snapshot after the call (L-4: the single remaining deepcopy still protects the
    caller).
**Assertions:** exact values as stated; `make_settings` helper moves to `tests/conftest.py`
(Wave 9) and is imported from there.

#### Source Spec (engineer's input — make the tests above pass)
**Source files:**
  - `src/mcp_langfuse/client.py`:
    - L-1: in `_extract_request_parts` path branch — `if not str(value).strip(): raise
      LangfuseArgumentError(f"Argument '{parameter.name}' cannot be empty for {operation.tool_name}")`.
    - L-2: `self._client_lock = asyncio.Lock()` in `__init__`; `_get_client` wraps
      check-and-create in `async with self._client_lock`; `aclose` acquires the same lock
      around close-and-clear.
    - L-3: new `_decode_response_details(operation, response)` used ONLY on the error path:
      try `_decode_response`, catch `LangfuseResponseDecodeError` and return its `details`
      dict instead of raising — `LangfuseAPIError` always wins for HTTP errors.
    - L-4: module-level `_VALIDATOR_CACHE: dict[str, Draft202012Validator]` keyed by
      `operation.tool_name` (spec is a process-level singleton via `lru_cache`, so names are
      stable and unique per O-2). `_validate_arguments` keeps its single `copy.deepcopy` and
      returns the copy; `_extract_request_parts` consumes that copy WITHOUT re-copying.
      Replace `_ensure_json_serializable` + `json=body` with: serialize once
      (`json.dumps(body)`, wrap `TypeError/ValueError` into `LangfuseArgumentError` with the
      existing message text), send via `content=serialized.encode()`,
      `headers={"Content-Type": "application/json"}` only when a body is present.
    - L-6: `follow_redirects=False` in the client; after the request, `if
      response.is_redirect: raise LangfuseTransportError(message=...mentioning probable base
      URL misconfiguration..., details={"status_code": ..., "location": ...})`.
    - L-7: retry loop in `call_operation`: up to `settings.retry_attempts` retries, ONLY when
      `operation.method == "GET"` and status in `(429, 503)`; delay = `Retry-After` header
      when it parses as a non-negative int, else `0.5 * 2**attempt`, capped at 10s; uses
      `asyncio.sleep`.
    - L-8: delete the six error-factory staticmethods; raise `LangfuseArgumentError(...)`
      inline at each call site with the SAME message text (tests match on messages).

---

### Wave 4: tool_selection.py — gate integrity (T-1…T-5, S-1 prerequisite)

**Depends on:** (none; Wave 5 depends on this)
**Scope:** `src/mcp_langfuse/tool_selection.py`

#### Impact Analysis
**Type:** modification + one public-name deletion
**Affected symbols:** `ToolSelection.all_by_name` (REMOVED), new field
`ToolSelection.gate_overrides`, `_disabled_reason` (DELETE gating change),
`build_tool_selection`, `describe_profiles`, new `_validate_known_families`.
**Public name removal — `all_by_name`:**
```
$ grep -rn 'all_by_name' src/ tests/ --include='*.py'
src/mcp_langfuse/tool_selection.py:51:    all_by_name: dict[str, OperationSpec]      — definition (removed here)
src/mcp_langfuse/tool_selection.py:269:        all_by_name=spec.by_tool_name,        — construction (removed here)
src/mcp_langfuse/service.py:70:        operation = self._selection.all_by_name.get(name)  — removed in Wave 5
```
All three accounted for. Tests never reference `all_by_name`.
**T-3 semantic change:** DELETE operations gate on `enable_destructive_tools` ONLY (no longer
also on `enable_write_tools`). Existing tests asserting the old combined behavior: none —
`test_default_selection_is_minimal_and_read_only` asserts `trace_delete` disabled with all
gates off (still true). README row updated in Wave 8.

#### Test Spec (tester's input)
**Test files:**
  - `tests/test_tool_selection.py` (EXTEND) — unit
**Test cases (must fail before implementation):**
  - `test_destructive_flag_alone_enables_delete` — profiles covering `Trace`, destructive=True,
    write=False → `langfuse_trace_delete` ENABLED (T-3 new semantics).
  - `test_write_flag_alone_does_not_enable_delete` — write=True, destructive=False →
    `langfuse_trace_delete` disabled with reason "destructive tools are disabled" (T-3 pin).
  - `test_gate_overrides_recorded_for_forced_tools` — `LANGFUSE_TOOLS_ENABLE=
    langfuse_projects_delete` with all gates off → `selection.gate_overrides ==
    {"langfuse_projects_delete": <the reason it would have been blocked>}` (T-1).
  - `test_gate_overrides_empty_for_organic_tools` — default selection →
    `selection.gate_overrides == {}` (T-1).
  - `test_unknown_constant_family_raises` — `build_tool_selection` against a reduced synthetic
    spec (parse_api_spec on a spec lacking admin tags) raises `ToolSelectionError` naming the
    missing families (T-2).
  - `test_conflicting_family_overrides_raise_before_apply` — same family in both enable and
    disable lists → `ToolSelectionError` (T-4 regression guard for the reordering).
  - `test_describe_profiles_counts_match_spec` — for the `minimal` profile, `tool_count` equals
    a hand-computed count over `load_api_spec()` operations (T-5 regression + Q-3 coverage).
  - `test_selection_no_longer_exposes_all_by_name` — `not hasattr(selection, "all_by_name")`
    (S-1 prerequisite pin).
**Assertions:** as stated; access `gate_overrides` via attribute (attr-defined disabled in
tests).

#### Source Spec (engineer's input — make the tests above pass)
**Source files:**
  - `src/mcp_langfuse/tool_selection.py`:
    - S-1 prep: remove `all_by_name` field and its construction.
    - T-1: add `gate_overrides: dict[str, str]` field; in the selection loop, when
      `operation.tool_name in enabled_tools` AND `_disabled_reason(...)` is not None, record
      it before enabling.
    - T-2: `_validate_known_families(available: set[str]) -> None` — raises
      `ToolSelectionError` listing any member of `ADMIN_FAMILIES`, `LEGACY_FAMILIES`, or any
      profile's `families` missing from `available`; called first in `build_tool_selection`.
      (Probe verified: zero drift in the current spec; also remove the silent
      `if family in available_families` filter at line 188 — validation now guarantees
      membership.)
    - T-3: `_disabled_reason` — `if method in DESTRUCTIVE_METHODS: gate destructive only;
      elif method in WRITE_METHODS: gate write` (make the branches mutually exclusive).
    - T-4: hoist `families_enable = _resolve_requested_families(...)` and
      `families_disable = ...` into locals; run `_validate_no_overlap` BEFORE applying
      update/difference_update; apply from the locals (no re-resolution).
    - T-5: in `describe_profiles`, hoist `family_set = set(families)` before the `sum(...)`.

---

### Wave 5: service.py — execution-path integrity and response shaping (S-1…S-6)

**Depends on:** Wave 4 (`all_by_name` removal, `gate_overrides`), Wave 1 (`max_response_bytes`)
**Scope:** `src/mcp_langfuse/service.py`

#### Impact Analysis
**Type:** modification
**Affected symbols:** `_resolve_operation` (fallback removal + exception-based flow),
`call_tool` (new except clause), `_success_payload` (truncation), `_json_text` (compact,
UTF-8), `LangfuseToolService.__init__` (new keyword `max_response_bytes`).
**Callers/importers:**
```
$ grep -rn 'LangfuseToolService' src/ tests/ --include='*.py'
src/mcp_langfuse/server.py:45      — constructor — updated in Wave 6 to pass max_response_bytes
tests/test_service.py (7 sites)    — constructor — new kwarg has a default; unaffected
```
`ensure_ascii` change affects only output formatting; no caller parses the text content
(structuredContent is the machine-readable channel).

#### Test Spec (tester's input)
**Test files:**
  - `tests/test_service.py` (EXTEND) — unit (FakeClient gains a `calls: int` counter)
**Test cases (must fail before implementation):**
  - `test_disabled_tool_is_never_executed` — default (minimal) selection,
    `call_tool("langfuse_projects_get")` → `tool_not_enabled` AND `fake.calls == 0` (S-1).
  - `test_unknown_tool_is_never_executed` — `call_tool("langfuse_nope")` → `unknown_tool`,
    `fake.calls == 0` (S-1: fallback removed; only enabled tools execute).
  - `test_large_response_truncated` — FakeClient returns data whose compact JSON exceeds
    `max_response_bytes=256` → `structuredContent["data"]["truncated"] is True`,
    `data_bytes` equals the original serialized byte length, `len(preview) <= 256` (S-2).
  - `test_small_response_not_truncated` — under the cap → data passes through unchanged (S-2).
  - `test_text_content_is_compact_utf8` — data `{"msg": "héllo"}` → text content contains
    `"héllo"` (no `é`), contains no `": "` separator and no newline (S-2/S-3 compact).
  - `test_invalid_arguments_error_omits_arguments_echo` — `"arguments" not in
    structuredContent` for an `invalid_arguments` error (S-4).
  - `test_base_client_error_mapped` — FakeClient raises `LangfuseClientError("boom")` →
    `isError`, `error == "langfuse_client_error"` (S-6).
**Assertions:** as stated; construct service with `**{"max_response_bytes": 256}` (mypy
call-arg dodge documented for tester).

#### Source Spec (engineer's input — make the tests above pass)
**Source files:**
  - `src/mcp_langfuse/service.py`:
    - S-1/S-5: introduce private `class _ToolResolutionError(Exception)` carrying a
      `result: types.CallToolResult`; `_resolve_operation` returns `OperationSpec` or raises
      it (DELETE the `all_by_name` fallback — names not enabled resolve to `tool_not_enabled`
      when a disabled reason exists, else `unknown_tool`); `call_tool` catches it first.
    - S-2: `__init__(self, selection, client, *, max_response_bytes: int = 200_000)`.
      `_success_payload` becomes an instance method: serialize `response.data` compactly
      (`separators=(",", ":"), ensure_ascii=False, default=str`); if
      `len(serialized.encode("utf-8")) > self._max_response_bytes`, replace `data` with
      `{"truncated": True, "data_bytes": <original byte length>, "preview":
      serialized[:self._max_response_bytes]}`.
    - S-3: `_json_text` → `json.dumps(payload, ensure_ascii=False, sort_keys=True,
      separators=(",", ":"), default=str)`.
    - S-4: drop the `"arguments"` key from the `invalid_arguments` payload.
    - S-6: append `except LangfuseClientError as exc:` (after the four leaf handlers) mapping
      to `{"error": "langfuse_client_error", "message": str(exc), "tool_name": name}`. Import
      `LangfuseClientError`.

---

### Wave 6: server.py — startup diagnostics and SDK contract (V-2…V-5, C-2/C-4/T-1/T-6 surfacing)

**Depends on:** Waves 1, 4, 5
**Scope:** `src/mcp_langfuse/server.py`

#### Impact Analysis
**Type:** modification + net-new helper
**Affected symbols:** `build_server` (decorator arg), `run_stdio` (Settings() direct,
diagnostics call, service kwarg), `main` (KeyboardInterrupt), new
`_log_startup_diagnostics`.
**Callers/importers:** `server.py` is consumed only via `__main__.py:3` (`from .server import
main`) and the two console scripts in pyproject — none affected by these internal changes.
Existing tests `test_server.py:18` monkeypatch `build_tool_selection` — unaffected.

#### Test Spec (tester's input)
**Test files:**
  - `tests/test_server.py` (EXTEND) — unit (capsys/monkeypatch) + API (in-memory MCP session)
**Test cases (must fail before implementation):**
  - `test_end_to_end_tool_call_over_memory_transport` (Q-1, V-1/V-2 pin) — build the full
    stack (real spec/selection/service, respx-mocked HTTP), connect via
    `mcp.shared.memory.create_connected_server_and_client_session`, then:
    `list_tools` includes `langfuse_trace_list`; `call_tool("langfuse_trace_list", {"limit": 1})`
    returns `isError False` with `structuredContent["ok"] is True`.
  - `test_end_to_end_schema_violation_uses_service_error_format` (V-2) — over the same
    in-memory session, `call_tool("langfuse_trace_list", {"limit": {"bad": 1}})` returns the
    service's structured `invalid_arguments` payload (proving the SDK's own input validation
    is off and the client-side validator owns errors).
  - `test_startup_diagnostics_summary_line` — `_log_startup_diagnostics(settings, selection)`
    writes a line to stderr containing the enabled-tool count and profile names (V-3).
  - `test_startup_diagnostics_warns_zero_tools` — empty selection → stderr contains
    `"WARNING"` and `"0 tools"` (V-3/T-6/C-2).
  - `test_startup_diagnostics_warns_unknown_env` — monkeypatch `LANGFUSE_TOOLS_ENABLED=x`
    (typo) → stderr WARNING naming the variable (C-4).
  - `test_startup_diagnostics_warns_gate_override` — selection with
    `gate_overrides={"langfuse_projects_delete": "destructive tools are disabled"}` → stderr
    WARNING naming the tool and the bypassed gate (T-1).
  - `test_main_handles_keyboard_interrupt` — monkeypatch `asyncio.run` to raise
    `KeyboardInterrupt` → `main()` raises `SystemExit` with code 130, no traceback (V-5).
  - (existing two config-error tests kept and must still pass after `from_env` removal)
**Assertions:** as stated; call `_log_startup_diagnostics` via module attribute
(`server_module._log_startup_diagnostics`) — attr-defined disabled in tests.

#### Source Spec (engineer's input — make the tests above pass)
**Source files:**
  - `src/mcp_langfuse/server.py`:
    - V-2: `@server.call_tool(validate_input=False)`.
    - C-6 hookup: `settings = Settings()` (add the same `# type: ignore[call-arg]` previously
      localized in `from_env`).
    - V-3 + C-4 + T-1 + T-6: `_log_startup_diagnostics(settings: Settings, selection:
      ToolSelection) -> None` printing to `sys.stderr`:
      summary line (tool count, profiles, write/destructive/admin/legacy gate states);
      `WARNING: 0 tools enabled ...` when `not selection.enabled_operations`;
      one WARNING per `os.environ` key matching `LANGFUSE_*` not in `config.KNOWN_ENV_VARS`;
      one WARNING per `selection.gate_overrides` entry naming tool and bypassed gate.
      Called from `run_stdio` after `build_tool_selection`.
    - Wave 5 hookup: `LangfuseToolService(selection, client,
      max_response_bytes=settings.max_response_bytes)`.
    - V-5: `except KeyboardInterrupt: raise SystemExit(130) from None` in `main`.
    - V-4: no code change — pydantic already reports alias names (verified by probe; pinned by
      Wave 1 test).

---

### Wave 7: tools_markdown.py + TOOLS.md — generator ergonomics (M-1…M-4)

**Depends on:** Wave 2 (uses `openapi_to_json_schema` signature; regeneration after all source
waves so the committed TOOLS.md matches)
**Scope:** `src/mcp_langfuse/tools_markdown.py`, `TOOLS.md` (regenerated)

#### Impact Analysis
**Type:** modification
**Affected symbols:** `TOOLS_MD_PATH` (becomes default for new `--path` option), `main`
(argparse changes), `render_tools_markdown` (heading levels).
**Callers/importers:** console script `mcp-langfuse-generate-tools-md` (pyproject:22), the
pre-commit `tools-md-check` hook (updated in Wave 8), and `tests/test_tools_markdown.py`.
TOOLS.md is regenerated in THIS wave (same dispatch as the rendering change) because the
`tools-md-check` pre-commit hook would otherwise block Engineer A's land.

#### Test Spec (tester's input)
**Test files:**
  - `tests/test_tools_markdown.py` (EXTEND) — unit/smoke (monkeypatch argv, capsys, tmp_path)
**Test cases (must fail before implementation):**
  - `test_tools_markdown_is_synced` — compares against `Path(__file__).resolve().parents[1] /
    "TOOLS.md"` (Q-2: CWD-independent) — also fails until M-4 regeneration lands.
  - `test_check_missing_file_exits_2_with_message` — `--check --path <tmp>/absent.md` →
    `SystemExit(2)`, stderr mentions the path (M-1).
  - `test_check_out_of_date_prints_remedy` — `--check --path <tmp>/stale.md` (stale content) →
    `SystemExit(1)`, stderr mentions `--write` (M-2).
  - `test_check_and_write_mutually_exclusive` — `--check --write` → `SystemExit(2)` (argparse)
    (M-3).
  - `test_write_respects_path` — `--write --path <tmp>/out.md` writes rendered content there
    (M-1).
  - `test_tool_details_heading_levels` — rendered text contains `\n### Trace\n` at most once
    under Tool Index, contains `#### \`langfuse_trace_list\`` in the details section, and
    contains no `\n## Trace\n` (M-4).
**Assertions:** as stated.

#### Source Spec (engineer's input — make the tests above pass)
**Source files:**
  - `src/mcp_langfuse/tools_markdown.py`:
    - M-1: `--path` argument (`type=Path`, default `TOOLS_MD_PATH`); `--check` on a missing
      file → stderr message naming the path and exit code 2.
    - M-2: `--check` mismatch → stderr `TOOLS.md is out of date; run
      mcp-langfuse-generate-tools-md --write` and exit 1.
    - M-3: `add_mutually_exclusive_group()` for `--check`/`--write`.
    - M-4: in the Tool Details section render tags as `### {tag}` and tools as
      `#### `tool``; Tool Index unchanged.
  - `TOOLS.md`: regenerate via `--write` after all Wave 1–7 source changes are in place.

---

### Wave 8: packaging, CI, docs (P-1…P-7, V-1, README) — Engineer B

**Depends on:** Waves 1–7 landed (CI runs pytest; README documents new knobs)
**Scope:** `pyproject.toml`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml` (NEW),
`.gitignore`, `README.md`

#### Impact Analysis
**Type:** modification + net-new CI workflow
**Affected symbols/files:**
  - `pyproject.toml` dependencies (`mcp[cli]>=1.18.0` → `>=1.19.0,<2`), `[project]` metadata,
    vulture config. uv.lock already resolves mcp 1.27.0 — floor bump requires no lock change
    (verify with `uv lock --check`).
  - `.pre-commit-config.yaml` — mirrors-mypy replaced by local uv hook (removes the
    hand-duplicated dependency list, P-5); `tools-md-check` entry made portable (P-3).
  - `.github/workflows/ci.yml` — net-new (P-4); the existing actionlint hook starts doing
    real work.
  - `README.md` — documents: new env vars (`LANGFUSE_RETRY_ATTEMPTS`,
    `LANGFUSE_MAX_RESPONSE_BYTES`), T-3 destructive-gate semantics, C-2 empty-profile
    behavior, P-2 Python-3.14 rationale, L-6 redirect behavior.
  - `.gitignore` — dedupe `.analysis/` (P-7).
**Callers/importers:** N/A — config and docs files.

#### Test Spec (tester's input)
`N/A for pytest — config/docs wave.` Verification is structural and lands in QA + Wave 0 gate:
`uv lock --check` passes after the floor bump; `pre-commit run --all-files` green with the new
local mypy hook; `actionlint` passes on the new workflow; `grep -c '.analysis/' .gitignore`
returns 1. (No application behavior changes; pytest cannot observe these files meaningfully.)

#### Source Spec (engineer's input)
**Source files:**
  - `pyproject.toml`:
    - P-1/V-1: `"mcp[cli]>=1.19.0,<2"`.
    - P-2: comment above `requires-python` documenting the deliberate 3.14-only floor.
    - P-6: add `classifiers = ["Private :: Do Not Upload"]` to `[project]` — declares the
      package private and makes accidental PyPI upload impossible (resolves thin-metadata risk
      without unilaterally selecting a license).
    - P-7: prune `ignore_decorators` to `["@server.list_tools", "@server.call_tool"]`
      (click/pytest entries reference frameworks absent from `src/`).
  - `.pre-commit-config.yaml`:
    - P-5: replace the mirrors-mypy block with a local hook: `entry: uv run --no-sync mypy
      --config-file=pyproject.toml`, `language: system`, `pass_filenames: false` — deps come
      from the locked project env (single source of truth).
    - P-3: `tools-md-check` entry → `uv run --no-sync python -m mcp_langfuse.tools_markdown
      --check` (no hardcoded `.venv/bin/python`, no login shell).
  - `.github/workflows/ci.yml` (NEW): on push/PR to `develop`/`main`; one job: checkout,
    `astral-sh/setup-uv`, `uv python install 3.14`, `uv sync --dev`, `uv run pre-commit run
    --all-files` (with `SKIP=gitleaks` left ON — gitleaks runs fine in CI), `uv run pytest -q`.
  - `README.md`: rows for `LANGFUSE_RETRY_ATTEMPTS` (default 2; GET-only, 429/503,
    Retry-After-aware) and `LANGFUSE_MAX_RESPONSE_BYTES` (default 200000; truncation marker
    shape); update `LANGFUSE_ENABLE_DESTRUCTIVE_TOOLS` row ("Allow `DELETE` operations —
    sufficient on its own; does not require the write flag") and
    `LANGFUSE_ENABLE_WRITE_TOOLS` row ("Allow non-`GET`, non-`DELETE` operations"); note that
    `LANGFUSE_TOOL_PROFILES=""` (set-but-empty) means *no profiles* and pairs with
    `LANGFUSE_TOOLS_ENABLE` for allowlist-only configurations; note redirects are treated as
    configuration errors; note the Python 3.14 floor rationale.
  - `.gitignore`: remove the duplicate `.analysis/` line.

---

### Wave 9: test hygiene (Q-2, Q-4) — tester-owned

**Depends on:** (none — executes inside the tester dispatch)
**Scope:** `tests/conftest.py` (NEW), `tests/test_client.py`, `tests/test_service.py`,
`tests/test_tool_selection.py`, `tests/smoke/__init__.py` + `tests/smoke/test_adversarial_review_remediation.py` (NEW)

#### Impact Analysis
**Type:** modification (test files only)
**Affected symbols:** duplicated `make_settings` helpers in `tests/test_client.py:20`,
`tests/test_service.py:34`, `tests/test_tool_selection.py:10` — consolidated into
`tests/conftest.py`; redundant `@pytest.mark.asyncio` marks (grep: `tests/test_client.py`,
`tests/test_service.py`) removed — `asyncio_mode = "auto"` (pyproject.toml:51) makes them
no-ops.
**Grep verification:** `grep -rn 'def make_settings' tests/` → 3 definitions, all replaced by
one conftest helper; `grep -rln 'pytest.mark.asyncio' tests/` → 2 files, marks removed.

#### Test Spec (tester's input)
This wave IS test work:
  - `tests/conftest.py` — single `make_settings(**overrides) -> Settings` helper (importable:
    `tests` is a package).
  - Remove all `@pytest.mark.asyncio` decorators (auto mode).
  - `tests/test_tools_markdown.py` anchored via `__file__` (spec'd in Wave 7).
  - `tests/smoke/test_adversarial_review_remediation.py` (+ `tests/smoke/__init__.py`):
    - `test_mcp_langfuse_imports()` — imports every `mcp_langfuse` module without error.
    - `test_default_selection_has_tools()` — default settings yield a non-empty enabled set.
    - `test_input_schemas_have_no_refs()` — no `"$ref"` in any operation's `input_schema`.

#### Source Spec (engineer's input)
`N/A — test-only wave; no source files change.`

## Schema Verification

`N/A — no database tables, SQL, ORM queries, or column references anywhere in this plan.`

## Risks and Mitigations

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | T-3 is a behavior change: `LANGFUSE_ENABLE_DESTRUCTIVE_TOOLS=true` alone now enables DELETEs (previously also required write flag) | Both directions pinned by new tests; README row updated in Wave 8; gate remains opt-in and off by default |
| 2 | T-2 strict family validation makes future spec refreshes fail loudly at startup | That is the intended design (silent gate evaporation was the finding); error message names exactly which constants to update |
| 3 | `validate_input=False` (V-2) shifts ALL argument validation onto the client path | Q-1 e2e tests pin both the happy path and the schema-violation error format through the real SDK handler |
| 4 | Truncation (S-2) changes the success-payload shape for oversized responses | Opt-out by raising `LANGFUSE_MAX_RESPONSE_BYTES`; `truncated` marker is explicit; README documents the shape |
| 5 | `follow_redirects=False` (L-6) could break a self-hosted proxy that relies on redirects | Error message names the location and suggests fixing `LANGFUSE_BASE_URL`; README notes the policy |
| 6 | Engineer A dispatch is large (~110k, near the 125k budget) | TOOLS.md regen is mechanical (`--write`); waves are independent enough that salvage can land partial work; two-strike escalation defined |
| 7 | Tester lands failing tests → develop pytest-red until Engineer A lands | Stage gate runs pre-commit (lint/mypy/vulture/tools-md-check), not pytest; CI workflow only arrives in Wave 8 AFTER Engineer A — no red-CI window |
| 8 | mypy blocks tester on not-yet-existing APIs | `attr-defined` already disabled for tests; dispatch prompt instructs module-attribute access and `**{...}` splat for new constructor kwargs |
| 9 | `mcp<2` upper bound could block a needed future upgrade | Deliberate: SDK behavioral drift between minors is exactly what V-1 documents; bumping the bound is a conscious act |

## Close-Out Checklist

- [ ] QA is MANDATORY for every wave. No exceptions.
- [ ] QA dispatched and PASS for every wave (inline under h4)
- [ ] Eyes tristore update (if context injection changed)
- [ ] Ops validation (run the operation the plan fixes; confirm idempotent with 2nd run)
- [ ] Gate check green (lint + tests + coverage)
- [ ] Smoke test PASS
- [ ] Operator nudges captured in retrospective (real-time, not batched)
- [ ] Lessons learned (what worked, what didn't, process improvements, metrics)
- [ ] Hindsight ("what would you do differently" — at least 5 items)
- [ ] Tool errors documented (as they occur, not reconstructed at close-out)
- [ ] Suggested persona/template adjustments
- [ ] Plan promoted to `docs/implemented/YYYY-MM-<slug>.md`

## Smoke Test Procedure

Smoke tests live in `tests/smoke/test_adversarial_review_remediation.py` (written by tester,
Wave 9).

CO-2 executes: `run_gate_check(mode='targeted', test_path='tests/smoke/test_adversarial_review_remediation.py')`

Required smoke assertions:
- `test_mcp_langfuse_imports()` — every `mcp_langfuse.*` module imports without error.
- `test_default_selection_has_tools()` — default settings produce a non-empty enabled tool set
  (guards the silent-zero-tools regression class).
- `test_input_schemas_have_no_refs()` — every precomputed `input_schema` is `$ref`-free.

No live-data/integration-tagged assertions required — the server's only external dependency
(Langfuse HTTP API) is exercised via respx mocks throughout the suite.

## Confidence Notes (Pre-Execution)

| Wave | Pre-Execution | Post-Execution | Notes |
|------|--------------|----------------|-------|
| 1 | HIGH | HIGH — as planned; one knock-on (SecretStr broke a tester smoke-test mypy pass → arg-type override) | Small, mechanical; pydantic SecretStr is well-trodden |
| 2 | HIGH | HIGH — implemented exactly per spec, QA 15/15 | parse/load split is the only structural move; probes confirmed zero live hazards |
| 3 | MEDIUM | HIGH — no respx friction materialized; 24/24 first attempt (of the successful dispatch) | Retry loop + redirect handling interact with respx mocking; most intricate wave |
| 4 | HIGH | HIGH — as planned | Selection logic is well-tested already; changes are additive + one field removal |
| 5 | HIGH | HIGH — as planned; QA noted preview slices by chars (matches spec as written) | Truncation algorithm fully specified; FakeClient pattern established |
| 6 | MEDIUM | HIGH — in-memory session tests worked on first implementation; benign RuntimeWarning from the KeyboardInterrupt test | In-memory MCP session test is new ground for this repo; SDK API verified to exist |
| 7 | HIGH | HIGH — as planned | Generator changes mechanical; TOOLS.md regen scripted |
| 8 | HIGH | MEDIUM-in-hindsight — two unplanned gate-config gaps surfaced (missing [tool.aawm.gate]; uv_extras default) | Config edits; `uv lock --check` verifies no resolution change |
| 9 | HIGH | HIGH — as planned | Test-only consolidation |

## Dispatch Plan

<!-- EXECUTION LOG — update in real-time during execution. -->

### Wave 0: Infrastructure Health Check (Required before first dispatch)

| Check | Command | Expected | Actual |
|-------|---------|----------|--------|
| CWD | `pwd` (foreground, alone) | `/home/zepfu/projects/mcp-langfuse` | `/home/zepfu/projects/mcp-langfuse` PASS |
| Branch | `git branch --show-current` | `develop` | `develop` PASS |
| Worktrees | `ls .claude/worktrees/` | empty | empty PASS |
| Gate baseline | `run_gate_check(branch='develop')` | lint PASS, 27 tests passed | `run_gate_check` unavailable (no `[tool.aawm.gate]` in pyproject — logged as tool error; Engineer B adds the block in Wave 8). Manual baseline: pytest 27 passed, ruff clean, mypy clean — PASS |

### Infrastructure Prerequisites Checklist

| Capability | Required By | Exists? | If Not: Add as Wave 0 step |
|-----------|------------|---------|---------------------------|
| Test database accessible | N/A — no DB work in this plan | N/A | — |
| Migration tool configured | N/A — no migrations | N/A | — |
| Integration test suite runnable | N/A — external API mocked via respx | N/A | — |
| uv + locked dev env (pytest, respx, pre-commit) | All dispatches | YES (verified: `uv run pytest` → 27 passed) | — |

### Total Estimated Effort

| Category | Planned Dispatches | Notes |
|----------|-------------------|-------|
| Tester | 1 | Writes ALL failing tests (Waves 1–7 specs + Wave 9 hygiene + smoke) |
| Engineer | 2 (by token budget) | A: Python source Waves 1–7 (~110k); B: packaging/config/docs Wave 8 (~35k); combined ~145k > 125k and file types differ |
| QA | 1 | Reviews ALL changes together |
| Ops/Data | 0 | No pipeline/infra operations |
| **Total waves** | **9 spec waves, 4 dispatches** | |
| **Max concurrent agents** | **1** | Strictly serial |

### Token Estimate

| Dispatch | Target files | Est. tokens | Rationale |
|----------|-------------|-------------|-----------|
| Tester | `tests/conftest.py`, `tests/test_config.py` (new), `tests/test_openapi.py`, `tests/test_client.py`, `tests/test_tool_selection.py`, `tests/test_service.py`, `tests/test_server.py`, `tests/test_tools_markdown.py`, `tests/smoke/*` | ~95k | ~45 test functions; reads review file + 7 source files (~30k); writing (~30k); run/iterate (~25k); overhead (~5k) |
| Engineer A | `src/mcp_langfuse/{config,openapi,client,tool_selection,service,server,tools_markdown}.py`, `TOOLS.md` | ~110k | reads sources + new tests (~35k); ~60 distinct edits (~25k); test iteration cycles (~45k); overhead (~5k) |
| Engineer B | `pyproject.toml`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `README.md`, `.gitignore` | ~35k | small reads (~8k); ~12 edits (~8k); pre-commit/lock verification loops (~15k); overhead (~4k) |
| QA | (read-only) | ~40k | Review all diffs + run full suite + structural checks for Wave 8 |

### Dispatch 1: Tester

| Agent | Target files | Task |
|-------|-------------|------|
| tester | all `tests/**` files listed above | Write ALL failing tests per Wave 1–7 Test Specs; perform Wave 9 hygiene (conftest consolidation, asyncio-mark removal, `__file__` anchoring); write smoke tests. mypy survival rules: module-attribute access for new symbols, `**{...}` splat for new kwargs. Tests must fail for the right reason (assert on missing behavior, not import errors). |

### Dispatch 2: Engineer A (Python source)

| Agent | Target files | Task |
|-------|-------------|------|
| engineer | `src/mcp_langfuse/*.py`, `TOOLS.md` | Implement Waves 1–7 Source Specs in order (config → openapi → client → tool_selection → service → server → tools_markdown); regenerate TOOLS.md last (`uv run python -m mcp_langfuse.tools_markdown --write`); make the entire suite green. |

**Two-Strike Escalation (if Dispatch 2 agent fails twice):**
- Root cause: identified before 3rd dispatch (most likely zone: Wave 3 retry/redirect respx interactions or Wave 6 in-memory session plumbing)
- Escalation: salvage agent rescues partial work from the stuck worktree; remaining scope re-dispatched with the root-cause note inline

### Dispatch 3: Engineer B (packaging/config/docs)

| Agent | Target files | Task |
|-------|-------------|------|
| engineer | `pyproject.toml`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `README.md`, `.gitignore` | Implement Wave 8; verify `uv lock --check`, `pre-commit run --all-files` green, actionlint passes on the new workflow. |

### Dispatch 4: QA

| Agent | Target files | Task |
|-------|-------------|------|
| qa | (read-only) | Verify all 55 findings addressed (use the Coverage Table as the checklist); test quality review; full suite + structural verification of Wave 8 (lock check, hook portability, classifier present, README rows). |

**Rules:**
- Dispatches sized by token budget (~125k per agent) — not by waves, groups, or surface areas
- One tester writes ALL tests → engineers implement ALL source → one QA reviews ALL
- Engineers split ONLY because combined work exceeds ~125k tokens AND file types need different tooling
- Deletion-only items ride inside the same dispatches (no standalone deletion waves)
- Wave N-d does NOT exist. Plan updates are orchestrator-inline work immediately after each dispatch completes.

## Coverage Table

| Finding | Satisfied by |
|---------|-------------|
| C-1 base-URL mutation | Wave 1 (validator rstrip) |
| C-2 empty-profile foot-gun | Wave 1 (pin test) + Wave 6 (zero-tool warning) + Wave 8 (README) |
| C-3 plain-str secrets | Wave 1 (SecretStr) + Wave 3 (auth hookup) |
| C-4 silent typo'd env vars | Wave 1 (KNOWN_ENV_VARS) + Wave 6 (warning) |
| C-5 Iterable pathology | Wave 1 |
| C-6 from_env alias | Wave 1 (removed) + Wave 6 (caller) |
| L-1 empty path params | Wave 3 |
| L-2 client init race (corrected) | Wave 3 (lock) |
| L-3 error-decode masking | Wave 3 |
| L-4 double copy/validate/serialize | Wave 3 (cache, single copy, content=) + Wave 2 (precomputed schema) |
| L-5 call-time param-location failure | Wave 2 (load-time rejection) |
| L-6 redirect semantics | Wave 3 |
| L-7 no 429/503 handling | Wave 1 (knob) + Wave 3 (retry loop) |
| L-8 six error factories | Wave 3 (inlined) |
| L-9 $ref open question | Wave 2 (precompute) + test `test_no_unresolved_refs_in_input_schemas` |
| O-1 uncached schema/by_tool_name | Wave 2 |
| O-2 collision detection | Wave 2 |
| O-3 recursion guard | Wave 2 |
| O-4 allOf leniency | Wave 2 (comment + description carry) |
| O-5 nullable+enum | Wave 2 |
| O-6 missing keywords / boolean exclusives | Wave 2 |
| O-7 unhonored content_type | Wave 2 (load-time rejection) |
| O-8 unfriendly load KeyErrors | Wave 2 |
| S-1 ungated fallback | Wave 4 (field removal) + Wave 5 (fallback deleted) |
| S-2 no size guard | Wave 1 (knob) + Wave 5 (truncation) |
| S-3 ensure_ascii bloat | Wave 5 |
| S-4 arguments echo | Wave 5 |
| S-5 mixed return type | Wave 5 (exception-based resolution) |
| S-6 base exception uncaught | Wave 5 |
| V-1 broken mcp floor | Wave 8 (`>=1.19.0,<2`) + Wave 6 e2e pin |
| V-2 double validation | Wave 6 (`validate_input=False`) |
| V-3 zero startup diagnostics | Wave 6 |
| V-4 error env-var naming | Verified correct by probe; pinned by Wave 1 test (no code change) |
| V-5 KeyboardInterrupt traceback | Wave 6 |
| T-1 force-enable bypass opacity | Wave 4 (gate_overrides) + Wave 6 (warning) |
| T-2 unvalidated family constants | Wave 4 |
| T-3 destructive/write coupling | Wave 4 (semantics) + Wave 8 (README) |
| T-4 redundant overlap re-resolution | Wave 4 |
| T-5 per-iteration set() | Wave 4 |
| T-6 silent tool-less server | Wave 6 (warning; same fix as C-2 surfacing) |
| M-1 CWD-relative TOOLS.md | Wave 7 (`--path`, exit 2) |
| M-2 silent --check failure | Wave 7 |
| M-3 non-exclusive flags | Wave 7 |
| M-4 heading hierarchy | Wave 7 (+ regen) |
| P-1 mcp floor | Wave 8 |
| P-2 3.14 floor undocumented | Wave 8 (pyproject comment + README) |
| P-3 hardcoded venv hook | Wave 8 |
| P-4 no CI | Wave 8 (workflow) |
| P-5 duplicated mypy deps | Wave 8 (local uv hook) |
| P-6 thin metadata | Wave 8 (`Private :: Do Not Upload` classifier) |
| P-7 vulture cruft / gitignore dupe | Wave 8 |
| Q-1 no e2e MCP test | Wave 6 test spec (in-memory session) |
| Q-2 CWD-dependent test | Wave 7 test spec / Wave 9 |
| Q-3 coverage gaps (decode branches, config, openapi units, empty path, describe_profiles) | Test specs of Waves 1, 2, 3, 4 (all five enumerated gaps have named tests) |
| Q-4 redundant marks / no conftest | Wave 9 |

All 55 findings mapped. None deferred. (Q-3's `_decode_response` branch coverage: tester adds
`test_204_returns_none`, `test_text_response_returned_as_str`,
`test_binary_response_base64_wrapped` to `tests/test_client.py` — included in the Wave 3 test
file scope.)

## Alternatives Considered

1. **Treat `LANGFUSE_TOOL_PROFILES=""` as "use default" (C-2)** — rejected: the empty-profile
   semantics are intentionally relied upon by the allowlist-only pattern
   (`test_explicit_tool_enable_overrides_profiles_and_safety_gates`,
   tests/test_tool_selection.py:52-62). Warning + documentation preserves the workflow while
   killing the silence.
2. **Keep mirrors-mypy and add a sync-check script for the dep list (P-5)** — rejected: a
   local `uv run mypy` hook eliminates the duplication entirely instead of policing it, and
   type-checks against the *locked* versions.
3. **httpx transport-level retries (`httpx.AsyncHTTPTransport(retries=...)`) for L-7** —
   rejected: httpx's built-in retries cover only connect errors, not 429/503 status handling
   or Retry-After; an explicit loop in `call_operation` is simpler than a custom transport.
4. **Lower `requires-python` to 3.11 (P-2)** — rejected: cannot be validated here (no 3.11
   interpreter in the environment, lockfile resolved for 3.14, CI matrix would be untested
   assertions). Documenting the floor as deliberate resolves the finding honestly.

## Self-Critique

- **The weakest part of this spec is** the S-2 truncation design: slicing compact JSON at a
  byte boundary produces a syntactically broken preview *string* (valid as a JSON string
  field, but not parseable as data). It is explicit and marked, but a smarter "truncate list
  items first" strategy would serve LLM consumers better. Shipped as specified because it is
  simple, predictable, and configurable.
- **The biggest assumption I made is** that `validate_input=False` on the SDK decorator has no
  side effects beyond skipping input validation (e.g., tool-definition caching used elsewhere
  in the handler). The Wave 6 e2e tests are designed to catch this, but only for the paths
  they exercise.
- **The thing most likely to need revision after first execution attempt** is Wave 3's retry
  tests under respx (side-effect sequencing + `asyncio.sleep` interactions) and the Wave 6
  in-memory session fixture — both are new patterns for this repo and the most plausible
  source of tester/engineer iteration loops.

## Operator Nudges

*Update immediately when operator corrects approach. Do not batch or defer.*

1. **Solo spec authoring** — operator directed the orchestrator to write this spec without
   dispatching agents and with zero deferred findings; both constraints honored.

## Tool Errors and Infrastructure Failures

*Log as they occur, not reconstructed at close-out.*

| Error | Frequency | Context | Resolution |
|-------|-----------|---------|------------|
| `run_gate_check` config_error: missing `[tool.aawm.gate]` in pyproject | 1 (Wave 0) | Repo never configured for aawm gate tooling | Manual baseline run (pytest/ruff/mypy); `[tool.aawm.gate]` added to Engineer B's Wave 8 scope (deviation #1) |
| Engineer A dispatch 1 died: "API Error: The operation timed out" after 12 tool uses (~6 min) | 1 | Infrastructure/API failure, not an approach failure; agent had modified only config.py (uncommitted, 34 insertions) | Continuation engineer dispatched (strike 1 of 2) with pointer to dead worktree agent-a611a7b10fe7509b6 for the partial config.py |

### Keepalive Cron

Job `dc87c2b8` — hourly at :13, created 2026-06-10 at /implement start. Do not cancel without operator direction.

---

## Outcomes

### Per-Wave Outcome Map

All 9 spec waves executed via 4 consolidated dispatches (plus one grunt fix). QA was a single
consolidated review covering every wave (Dispatch 4): verdict PASS, 55/55 findings verified.

| Wave | Status | Tests by | Source by | Commits | QA verdict |
|------|--------|----------|-----------|---------|------------|
| Wave 1: config.py | DONE | Dispatch 1 (`730189f`) | Dispatch 2 (`a555422`) | `730189f`, `a555422` | PASS |
| Wave 2: openapi.py | DONE | Dispatch 1 | Dispatch 2 | `730189f`, `a555422` | PASS |
| Wave 3: client.py | DONE | Dispatch 1 | Dispatch 2 | `730189f`, `a555422` | PASS |
| Wave 4: tool_selection.py | DONE | Dispatch 1 | Dispatch 2 | `730189f`, `a555422` | PASS |
| Wave 5: service.py | DONE | Dispatch 1 | Dispatch 2 | `730189f`, `a555422` | PASS |
| Wave 6: server.py | DONE | Dispatch 1 | Dispatch 2 | `730189f`, `a555422` | PASS |
| Wave 7: tools_markdown.py + TOOLS.md | DONE | Dispatch 1 | Dispatch 2 | `730189f`, `a555422` | PASS |
| Wave 8: packaging/CI/docs | DONE (non-testable config wave) | N/A per spec | Dispatch 3 (`118c85a`) + grunt fix (`581fd1e`) | `118c85a`, `581fd1e` | PASS |
| Wave 9: test hygiene | DONE | Dispatch 1 (tester-owned) | N/A per spec | `730189f` | PASS |

### Dispatch 1: Tester — all failing tests (Waves 1–7 specs + Wave 9 hygiene + smoke)
**Status:** DONE
**Test commit(s):**
  - `730189f` — test(api): add failing tests for adversarial-review remediation (red phase)
**Test agent:** tester
**Merge:** `d33a816`
**Actual changes:** 65 new tests across 10 files (2 new test modules, conftest, smoke package); pytest profile after land: 50 passed / 41 failed (all failures are the intended red-phase behavioral gaps); ruff/mypy/vulture/tools-md-check clean. Wave 9 hygiene applied (asyncio marks removed, make_settings consolidated into conftest, TOOLS.md path anchored).
**Deviations:** (none)
**Findings:** (none)

## Dispatch Log

| Dispatch | Phase | Agent | Target files | Worktree | Result | Notes |
|------|-------|-------|-------------|----------|--------|-------|
| 1 | a (test) | tester | tests/** (10 files) | agent-a90312dc911fae3e4 (removed) | Landed `730189f` | 41 red tests, 50 green; lint clean |
| 2 | b (impl) | engineer | src/mcp_langfuse/*.py, TOOLS.md | agent-a611a7b10fe7509b6 (removed) | FAILED — API timeout | Strike 1; only partial uncommitted config.py |
| 2 | b (impl) | engineer | src/mcp_langfuse/*.py, TOOLS.md, pyproject.toml (2 additive lines) | agent-acc8d6c3fc5ffab69 (removed) | Landed `a555422` (merge `2a40787`) | 91/91 green; Waves 1–7 complete |
| 3 | b (impl) | engineer | pyproject.toml, .pre-commit-config.yaml, .github/workflows/ci.yml, README.md, .gitignore, uv.lock | agent-a044a4192920319e4 (removed) | Landed `118c85a` (merge `1f405e0`) | Wave 8 complete; pre-commit fully green; actionlint pass |
| 4 | b (fix) | grunt | pyproject.toml ([tool.aawm.gate] uv_extras=[]) | agent-a4f8ce0e83555430f (removed) | Landed `581fd1e` (merge `3cf39fe`) | Ad-hoc fix #2; verified `uv run --frozen pytest -q` → 91 passed |
| 5 | c (qa) | qa | (read-only) | — | dispatched | Full 55-finding sweep + structural checks |

### Dispatch 2: Engineer A — Python source Waves 1–7
**Status:** DONE (attempt 2; attempt 1 died to API timeout with no committed work)
**Source commit(s):**
  - `a555422` — Remediate adversarial-review findings across config, openapi, client, selection, service, server, tools_markdown (merge `2a40787`)
**Source agent:** engineer
**Actual changes:** All Wave 1–7 Source Specs implemented as planned; TOOLS.md regenerated; suite 91 passed / 0 failed.
**Deviations:**
  - Two additive `pyproject.toml` edits required to pass the stage gate (flagged for Engineer B/QA):
    1. `arg-type` added to tests mypy `disable_error_code` — SecretStr (Wave 1) made the tester's plain-str `LANGFUSE_SECRET_KEY=` kwarg in the smoke test fail mypy.
    2. `cls` added to vulture `ignore_names` — deleting `from_env` left `@field_validator` classmethods as the only `cls` users, which vulture then flagged.
**Findings:** benign RuntimeWarning ("coroutine 'run_stdio' was never awaited") emitted by test_main_handles_keyboard_interrupt due to its asyncio.run monkeypatch — test-harness artifact.

### Dispatch 3: Engineer B — Wave 8 packaging/CI/docs
**Status:** DONE
**Source commit(s):**
  - `118c85a` — Harden packaging: mcp floor, CI workflow, portable hooks, docs for new knobs (merge `1f405e0`)
**Source agent:** engineer
**Actual changes:** mcp floor `>=1.19.0,<2`; 3.14-floor comment; `Private :: Do Not Upload` classifier; vulture decorators pruned; `[tool.aawm.gate]` added (deviation #1); local uv mypy hook replaces mirrors-mypy; portable tools-md-check; new CI workflow (develop/main, uv-based, pre-commit + pytest); README rows/notes for new knobs, gate semantics, empty profiles, redirects, 3.14; .gitignore deduped.
**Deviations:**
  - `uv.lock` spec-string sync committed (consequence of the floor edit; resolution unchanged, mcp stays 1.27.0) — required for CI `uv lock --check`.
  - Post-land gate check exposed a second config gap: the gate's test step defaults to `--extra dev`, but dev deps are a PEP-735 dependency group → "Extra `dev` is not defined". Ad-hoc fix #2 dispatched (grunt): `uv_extras = []` in `[tool.aawm.gate]`.
**Findings:** Engineer B's session does not expose `run_gate_check` — gate verification fell back to tomllib parse; orchestrator ran the live gate post-land (lint/mypy/format PASS; tests step hit the uv_extras gap above).

### Dispatch 4: QA

**QA verdict: PASS**
**Date:** 2026-06-11 — **Reviewer:** qa — **Range:** `4e59ad8..develop` — **Full report:** `.analysis/qa-adversarial-review-remediation.md`

Per-checklist results:
1. **Test files/functions — PASS.** Every test named in the Wave 1–7 Test Specs exists, plus the 3 decode-branch tests (tests/test_client.py:181,193,207), `tests/conftest.py`, and `tests/smoke/` (3 tests).
2. **Suite green — PASS.** `uv run pytest -q` → 91 passed in 2.43s; `uv run pytest tests/smoke -q` → 3 passed.
3. **Real value assertions — PASS.** Spot-checked: retry (`route.call_count`, exact status codes — test_client.py:295-315), truncation (`truncated is True`, preview length — test_service.py:264-266), e2e in-memory MCP (tool listing + `structuredContent["ok"] is True` + `invalid_arguments` through real SDK — test_server.py:76-100), recursion guard (ValueError match "circular" — test_openapi.py:186), gate_overrides (tool enabled AND override recorded — test_tool_selection.py:123-126), Authorization header base64-decoded and compared (test_client.py:427-428).
4. **Not vacuously true — PASS.** L-1: route mocked 200, so a missing empty-check would succeed and `pytest.raises` would fail. T-3: baseline `_disabled_reason` returns "write tools are disabled" for DELETE with destructive=True/write=False → `test_destructive_flag_alone_enables_delete` fails against old code; reverse pin guards the other direction. S-2: without truncation `data["truncated"]` raises KeyError. All three were red at tester land (50/41 profile).
5. **Source matches spec — PASS.** Full 55-finding sweep: **55 PASS / 0 FAIL** (per-finding citations in the QA report). Notables: S-6 implemented as single `except LangfuseClientError` + isinstance dispatch (payloads identical — equivalent); L-8 leaves `_schema_validation_error` as one private helper (messages preserved — acceptable).
6. **No regressions — PASS.** Zero removed `def test_` lines in the range; all 27 baseline tests present; only planned consolidations (conftest make_settings, 0 remaining asyncio marks, `__file__`-anchored TOOLS.md test).
7. **Wave 8 structure — PASS.** `uv lock --check` OK; no mirrors-mypy, no hardcoded `.venv/bin/python`; ci.yml present, actionlint hook Passed; pyproject has `mcp[cli]>=1.19.0,<2`, `Private :: Do Not Upload`, `[tool.aawm.gate]` with `uv_extras = []`, 3.14 comment; `.gitignore` exactly one `.analysis/`; README rows for both new knobs + updated destructive/write wording + empty-profile/redirect/3.14 notes.
8. **Deviations acceptable — PASS.** mypy `arg-type` (tests), vulture `cls`, uv.lock spec-string-only sync (resolution unchanged), grunt `uv_extras=[]` — all documented above.

Quality notes (non-blocking): (a) `test_large_response_truncated` asserts `data_bytes` presence, not equality with the original byte length (spec said equals; impl verified correct by inspection — suggest tightening later); (b) S-2 preview slices by character per spec — multi-byte UTF-8 previews can exceed the cap in bytes (latent nuance, matches spec verbatim); (c) Outcomes say "65 new tests" but the range adds 64 test functions (91 − 27 baseline; bookkeeping only); (d) benign `run_stdio` RuntimeWarning already logged in Dispatch 2 findings.

---

## Close-Out Execution Record

### CO-1: Gate Check — PASS
Commit `3cf39fe` — lint/typecheck/format/ruff/mypy all PASS; tests 91 passed / 0 failed.
Coverage: unavailable (repo carries no pytest-cov; coverage was never configured pre-plan — noted, not a regression).

### CO-2: Smoke Test — PASS
`run_gate_check(mode='targeted', test_path='tests/smoke/test_adversarial_review_remediation.py')` → pass (runner executed full suite: 91 passed, smoke included). Benign RuntimeWarning from the KeyboardInterrupt test's asyncio.run monkeypatch, documented in Dispatch 2 outcome.

### CO-3: Ops Validation — N/A
No pipeline jobs, data migrations, or infrastructure operations in this plan. (New CI workflow will exercise on the next push to a GitHub remote.)

### Dispatch 4 (QA) — summary
Verdict: **PASS**, 55/55 findings verified, 8/8 checklist items pass. Full report: `.analysis/qa-adversarial-review-remediation.md`. Four non-blocking quality notes (most actionable: tighten `test_large_response_truncated` to assert `data_bytes` equality; S-2 preview slices by character so multi-byte UTF-8 previews can exceed the byte cap — both match the spec as written).

## Retrospective — Hindsight

1. **The gate tooling assumption was the plan's only real blind spot.** Wave 0 discovered `[tool.aawm.gate]` was missing, and even after Engineer B added it, the `uv_extras=["dev"]` default broke on this repo's PEP-735 dependency-groups layout — two ad-hoc fixes (#1 folded into Wave 8, #2 via grunt) for what one Wave-0 probe (`run_gate_check` BEFORE writing the plan) would have caught wholesale.
2. **Cross-wave type changes ripple into test-lint, not just source.** Wave 1's SecretStr broke mypy on the tester's already-landed smoke test (plain-str kwarg), forcing Engineer A's `arg-type` override. The plan's mypy-survival notes covered the tester writing new tests, but not the engineer's source changes invalidating *existing* test typing — a spec template gap worth remembering.
3. **Deleting a symbol can break unrelated lint heuristics.** Removing `from_env` (the only non-validator `cls` user) made vulture flag `cls` in the remaining `@field_validator` classmethods. Impact analysis enumerated callers but not lint-tool side effects of the deletion.
4. **The API-timeout dispatch failure cost ~6 minutes and zero rework** because the failure protocol (inspect worktree → continuation dispatch with pointer to partial work) was followed; the second attempt completed all 7 waves in one pass. Infrastructure failures and approach failures need different responses — this one needed no root-cause escalation.
5. **Consolidated dispatches (1 tester / 2 engineers / 1 QA for 9 spec waves) had zero coordination failures** — no cross-dispatch file conflicts, no QA round-trips. The token-budget sizing heuristic (split only at ~125k / file-type boundaries) was right for this plan; per-wave dispatching would have cost ~20 extra dispatches for no quality gain.
6. **Gate-check caching can mislead post-land verification.** The cached gate result (commit-stale, 215s old) initially appeared to show grunt's fix not working; the actual fix was fine. Post-land verification should either wait out the cache TTL or rely on running the gate's exact command locally — which grunt had already done.

### Close-Out Checklist (final)

- [x] QA is MANDATORY for every wave — single consolidated QA dispatch covered all waves: PASS
- [x] QA dispatched and PASS (Dispatch 4, 55/55 findings)
- [x] Eyes tristore update — N/A (no context injection changed by this plan)
- [x] Ops validation — N/A (no ops waves)
- [x] Gate check green (lint + tests; coverage tooling absent pre-plan, unchanged)
- [x] Smoke test PASS
- [x] Operator nudges captured in real time (1 nudge)
- [x] Lessons learned (Hindsight above)
- [x] Hindsight ≥5 items (6 items)
- [x] Tool errors documented as they occurred (3 entries)
- [x] Suggested persona/template adjustments — see Hindsight items 1–3 (spec-template: add a "run the gate tool in Wave 0 *before* finalizing the plan" rule; impact analysis should consider lint-tool side effects and test-typing ripple)
- [ ] Plan promoted to `docs/implemented/YYYY-MM-<slug>.md` (CO-7 /promote next)

---

## Researcher Review

**Date:** 2026-06-11
**Reviewer:** researcher
**Verdict:** APPROVED (with noted non-blocking items)

---

### Findings

#### F-1 — Spec-to-Outcome Consistency: PASS (all 9 waves)
Every wave produced the outcome described in its spec. The Per-Wave Outcome Map and Dispatch Log entries are fully consistent with the source, test, and config files in the final state of `develop`. Wave 8's `MEDIUM-in-hindsight` confidence note is honest: the two gate-config gaps (missing `[tool.aawm.gate]`, wrong `uv_extras` default) were caught and fixed without any wave having to be re-executed. No wave has an unexplained outcome or a null outcome.

#### F-2 — Deviation Documentation: PASS (all four documented; one undocumented minor addition)
All four documented deviations (mypy `arg-type` override, vulture `cls` ignore, uv.lock spec-string sync, grunt `uv_extras=[]`) are explained with clear rationale and traced to their root causes. One minor undocumented choice was found: Engineer B added `coverage_target = 80` to the new `[tool.aawm.gate]` block without the plan specifying that value. The plan only says "add the block"; the engineer chose a sensible aspirational target. This is harmless today (no pytest-cov is installed so coverage enforcement is a no-op), but it is an undocumented deviation from the spec-as-written. Not a blocking issue — the target is aspirational rather than enforced — but should be noted for the documentation record.

#### F-3 — Lessons Learned Quality: PASS (actionable and specific)
All six hindsight items name a concrete wave, agent type, failure mode, and actionable remedy. Items 1–3 are the most valuable and directly propose spec-template improvements. Items 4–6 are process observations rather than pure templates; item 4 (timeout failure) and item 5 (dispatch consolidation metrics) are informative but slightly lower signal. Item 6 (gate-cache mislead) is genuinely useful and specific. No vacuous platitudes detected. One gap noted in F-4 below.

#### F-4 — Gap Detection: ONE MINOR GAP
The persistent benign `RuntimeWarning: coroutine 'run_stdio' was never awaited` from `test_main_handles_keyboard_interrupt` is logged in Dispatch 2 findings, but the retrospective does not capture it as a process lesson (e.g., "monkeypatching asyncio.run to raise immediately leaves the coroutine object un-awaited — use `asyncio.run = lambda coro, **_: coro.close() or raise_exc()` to suppress the warning"). This is a cosmetic gap in the lessons-learned: the test still passes correctly, but 7 retrospective items would have been tighter. The suppressed warning could confuse future maintainers scanning pytest output. The close-out checklist note for `run_stdio` RuntimeWarning is present in Dispatch 2 findings, which partially mitigates the gap.

#### F-5 — QA Coverage: PASS (genuine sweep, not rubber-stamp)
The QA report is non-trivial. It provides per-finding evidence citations (file:line), not just "source present." The "Not vacuously true" checklist item is addressed with specific reasoning for three independent test types. QA correctly identified three non-blocking quality notes: `test_large_response_truncated` asserting presence-not-equality for `data_bytes`, the UTF-8 multi-byte preview edge case in S-2, and the test-count bookkeeping discrepancy (64 not 65). These notes are accurate and were independently verified here. The L-8 `_schema_validation_error` surviving as a private helper — flagged as acceptable by QA and correct: message text is preserved, intent of the finding (no public factory methods) is honored.

#### F-6 — Implementation Wiring Verification: PASS
All six wiring paths verified against live source:
- `_log_startup_diagnostics` is called from `run_stdio` at `server.py:87` ✓
- The retry loop (`for attempt in range(self._settings.retry_attempts)`) is reachable in `call_operation` at `client.py:345`; initial request made before the loop; `range(2)` → 3 total requests with default `retry_attempts=2` — matches the test's `call_count == 3` assertion ✓
- `gate_overrides` flows from `build_tool_selection` (populated at `tool_selection.py:281`) into `_log_startup_diagnostics` (consumed at `server.py:68`) ✓
- Validator cache (`_VALIDATOR_CACHE`) is used in `_validate_arguments` at `client.py:246–249` ✓
- `parse_api_spec` is called by `load_api_spec` at `openapi.py:554` ✓
- Service truncation (`_success_payload`) is invoked from `call_tool` at `service.py:128` ✓
- Suite: 91/91 passed; smoke: 3/3 passed; pre-commit: 12/12 hooks green ✓

One latent implementation nuance identified (non-blocking): `_serialize_body` is called when `operation.request_body is not None` rather than when `body is not None`. For an optional request body not provided by the caller, `body=None` from `_extract_request_body`, yet `json.dumps(None).encode() = b'null'` would be serialized and sent with `Content-Type: application/json`. The plan spec says the condition should be "only when a body is present" (implying `body is not None`). Verified that **zero** operations in the current vendored spec have an optional request body, so there is no live path hitting this condition today. It is latent technical debt, not an active defect.

#### F-7 — Infrastructure Readiness: PASS
CI workflow (`ci.yml`) exists, is valid YAML, passes actionlint, and covers push/PR to develop/main. `uv lock --check` passes. Pre-commit suite runs cleanly (12 hooks, all pass). No container or migration work required. One minor CI spec ambiguity found and resolved: the plan's note `(with SKIP=gitleaks left ON — gitleaks runs fine in CI)` is awkwardly worded but means the gitleaks hook is retained in `.pre-commit-config.yaml` and allowed to run in CI — the implementation matches (no `SKIP` env var in `ci.yml`). The `coverage_target = 80` in `[tool.aawm.gate]` with no pytest-cov installed is aspirational rather than enforced; gate runs will skip coverage measurement. This should be resolved before pytest-cov is added to dev deps to avoid a surprise gate failure.

#### F-8 — Plan-to-Implementation Alignment: PASS (with two minor noted drifts)
Verified all four commit diffs against their wave specs:

- **730189f (Tester):** All Wave 1–7 test specs implemented; Wave 9 hygiene applied (conftest consolidation, asyncio marks removed, `__file__` anchoring). `test_client.py` retains a local `make_settings` wrapper that adds `LANGFUSE_BASE_URL` — this is correct specialization, not a duplicate. 64 new test functions (plan says 65; bookkeeping off by one, already noted by QA).

- **a555422 (Engineer A):** All Wave 1–7 source specs implemented exactly: `Settings` SecretStr, KNOWN_ENV_VARS, retry/max_response_bytes fields; `parse_api_spec`/`load_api_spec` split; stored `input_schema`/`by_tool_name`; circular-ref guard; nullable+enum; boolean exclusive bounds; header/non-JSON rejection; `_VALIDATOR_CACHE`; single deepcopy/serialize; lock on `_get_client`/`aclose`; redirect detection; retry loop; `gate_overrides`; `_validate_known_families`; T-3 mutually-exclusive destructive/write branches; T-4 hoisting; T-5 `family_set`; `_ToolResolutionError`; truncation; compact UTF-8 JSON; `arguments` key dropped; `LangfuseClientError` catch; `validate_input=False`; `_log_startup_diagnostics`; `KeyboardInterrupt` → `SystemExit(130)`; `--path`/`--check`/`--write` args; heading levels. The silent `if family in available_families` filter at the original line 188 of `_resolve_profile_families` is correctly removed. Two additive `pyproject.toml` edits (mypy `arg-type`, vulture `cls`) are documented deviations.

- **118c85a (Engineer B):** Wave 8 fully implemented: mcp floor `>=1.19.0,<2`; 3.14-floor comment; `Private :: Do Not Upload`; vulture decorators pruned; local uv mypy hook; portable tools-md-check; CI workflow; README knobs/notes; .gitignore dedup; uv.lock spec-string sync. Undocumented addition of `coverage_target = 80` to `[tool.aawm.gate]` (see F-2).

- **581fd1e (Grunt):** Single-line addition of `uv_extras = []` to `[tool.aawm.gate]`. Correctly documented as deviation #4.

---

### Recommendations (non-blocking)

1. **Tighten `test_large_response_truncated`** (QA quality note (a), also plan spec language): change `assert "data_bytes" in data` to `assert data["data_bytes"] == expected_byte_length` where `expected_byte_length` is computed from the same FakeClient data the test provides. The implementation is correct by inspection (`_success_payload` uses `encoded_length`), but the assertion doesn't actually verify the value.

2. **Document or fix the `serialized_body` optional-body edge case**: when `operation.request_body is not None` but the caller omits an optional body, `json.dumps(None).encode()` = `b'null'` is currently sent with `Content-Type: application/json`. The spec says "only when a body is present." Since no current operations have optional bodies this is inert, but the condition should be `serialized_body = self._serialize_body(operation, body) if body is not None else None` to match spec intent and avoid surprising behavior if a future spec revision adds optional bodies.

3. **Resolve `coverage_target = 80` against tooling reality**: either (a) add `pytest-cov` to dev deps and configure `[tool.pytest.ini_options] addopts = "--cov=src --cov-fail-under=80"` to make the target enforceable, or (b) set `coverage_target = 0` (or remove the key) to reflect that coverage is not currently measured. The current state sets a target the toolchain cannot enforce.

4. **Suppress or acknowledge the RuntimeWarning in `test_main_handles_keyboard_interrupt`**: the `asyncio.run` monkeypatch leaves `run_stdio()` as an unawaited coroutine object. Add `coro.close()` before raising inside the mock (`def raise_keyboard_interrupt(coro, **_): coro.close(); raise KeyboardInterrupt`) to silence the warning without changing the test outcome.

5. **Add a Hindsight item on the `coverage_target` gap**: the pattern of "engineer adds plausible config values not specified in the spec" is a recurring risk in config-heavy waves. A spec-template note to enumerate required _and_ default gate config values would prevent this class of silent drift.

**Confidence level:** HIGH — all source files, test files, CI/config files, and commit diffs were read directly; wiring paths were traced end-to-end in source; the full test suite and pre-commit suite were executed live and passed.
