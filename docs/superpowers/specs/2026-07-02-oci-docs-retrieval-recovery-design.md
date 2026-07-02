# OCI Docs Retrieval Recovery Design

## Problem

The OCI documentation workflow can fail in two related ways even when canonical OCI pages
remain readable:

- The JSON search endpoint can return HTTP 403, and the public HTML fallback can also yield no
  usable results.
- `answer_question` examines only the first `max_sources` ranked candidates. If any of those
  pages are unreadable, it does not continue to lower-ranked candidates that may be readable.

The supported `oci-docs read` command has demonstrated that cited canonical pages can remain
available during this failure mode. Recovery therefore belongs in the shared search and answer
orchestration rather than in CLI-only retry behavior.

## Goals

- Allow independent search sources to recover from a blocked or empty primary search.
- Continue reading ranked answer candidates until the requested number of readable sources is
  collected or the bounded candidate list is exhausted.
- Preserve the existing MCP and CLI command flags, response models, ranking behavior, and
  low-confidence answer contract.
- Keep all ordinary tests deterministic and independent of live Oracle endpoints.

## Non-Goals

- Circumvent Oracle access controls or emulate a browser beyond the existing request headers.
- Add unbounded retries, new external search providers, or live-network unit tests.
- Change citation formatting, evidence ranking, CLI options, or public response fields.
- Refactor unrelated retrieval adapters.

## Selected Approach

Use bounded orchestration hardening in the shared server path. Official JSON search, the public
HTML search page, Architecture Center, and Oracle Blogs are treated as independently recoverable
sources. Successful results are merged and ranked before answer generation. Answer generation
then backfills unreadable candidates from the existing bounded ranked list.

This approach was selected over strengthening only the JSON HTTP request because request-header
or retry variations remain vulnerable to anti-bot changes and do not solve unreadable answer
candidates. It was selected over CLI-only recovery because MCP callers need the same behavior and
duplicating orchestration in the CLI would create inconsistent contracts.

## Architecture and Data Flow

### Search orchestration

`search_documentation` remains the public coordination boundary and keeps a single
`httpx.AsyncClient` open for the entire federated search.

1. An internal official-document search helper requests the JSON endpoint.
2. If the request raises an HTTP error, returns a 4xx or 5xx response, contains a malformed
   payload, or produces no usable OCI documentation results, the helper requests the public HTML
   search page.
3. `search_documentation` invokes Architecture Center and Oracle Blogs independently of the
   official-document outcome.
4. All successful results pass through the existing combined deduplication and ranking path.
5. A synthetic error result is returned only when every configured source fails or yields no
   usable result.

The official-document helper returns `list[SearchResult]` and absorbs recoverable source-local
failures as an empty list. It does not introduce a new public model.

### Answer source collection

`answer_question` keeps the existing search limit of `min(50, max_sources * 3)` and the existing
intent-aware ranking. Its document loop changes from slicing the first `max_sources` candidates to
walking the bounded ranked list:

1. Read the next candidate in rank order.
2. Skip content recognized by `_is_unreadable_documentation`.
3. Append readable content as a `SourceDocument`.
4. Stop as soon as `len(documents) == max_sources`.
5. If the candidate list is exhausted first, build the answer from the readable subset.

`build_cited_answer` remains unchanged. If no readable documents are collected, it continues to
return the existing low-confidence response with no citations and the current missing-information
message.

## Error Handling and Observability

- HTTP exceptions, error status codes, malformed payloads, and empty results are recoverable at
  the individual source boundary.
- A source-local failure is logged with enough context to identify the source and failure class.
- Partial search success returns normal ranked results without calling `ctx.error`.
- `ctx.error` is called once when the overall federated search has no usable result.
- Page-read failures continue to use `read_documentation_impl`; unreadable responses are skipped
  and do not terminate answer collection.
- No retry loop is added, so request count remains bounded by the configured search sources and
  answer candidate limit.

## Files and Responsibilities

- `oci_documentation_mcp_server/server_oci.py`
  - Extract or extend the internal official-document fallback helper.
  - Ensure supplemental searches run even when official search fails or falls back.
  - Backfill readable answer documents from lower-ranked candidates.
- `tests/test_server_oci.py`
  - Add deterministic regression coverage for partial search failure, all-source failure, answer
    backfilling, and early stopping.

No change is expected in `oci_documentation_mcp_server/cli.py`,
`oci_documentation_mcp_server/server_utils.py`, or the public response models.

## Test Design

Add or refine tests that prove:

1. A JSON 403 followed by successful public HTML fallback still allows supplemental results to be
   merged.
2. Failed JSON and HTML searches do not suppress successful Architecture Center or Oracle Blog
   results.
3. A transport error in official search does not suppress supplemental results.
4. All search sources failing or returning empty results produces the existing error-result shape
   and one overall `ctx.error` call.
5. With `max_sources=1`, an unreadable first candidate and readable second candidate produce a
   cited answer from the second candidate.
6. Reading stops immediately after `max_sources` readable documents are collected.

Existing CLI tests and response-model tests remain compatibility coverage. Focused verification is
followed by the full non-live suite, Ruff lint and formatting checks, and Pyright.

## Acceptance Criteria

- A blocked, malformed, or empty primary search cannot prevent another configured source from
  returning ranked results.
- An unreadable top-ranked page cannot prevent a cited answer when a lower-ranked readable page is
  available within the bounded candidate list.
- Partial failures do not produce a user-facing overall search error.
- All-source failure retains the existing response shape and diagnostic behavior.
- Existing CLI flags, MCP signatures, response fields, citations, and ranking contracts remain
  unchanged.
- All new regression tests and the repository verification suite pass.
