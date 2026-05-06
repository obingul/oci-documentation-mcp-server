# OCI MCP Client UX Design

Date: 2026-05-06
Status: approved direction, written spec
Scope: client-facing MCP experience for OCI documentation users

## Goal

Make the OCI Documentation MCP server feel like an answer-ready documentation assistant inside MCP clients, not a thin search wrapper. The server should help clients search, choose, read, cite, and recover with minimal extra prompting.

## Primary Users

- Developers using MCP clients such as Cursor, Claude Desktop, VS Code, or Kiro.
- AI assistants that need reliable OCI documentation sources for answers.

## Recommended Direction

Prioritize the answer-ready tool flow:

1. A client searches OCI docs with a natural user question.
2. Search results include enough metadata for the client to rank and explain why a result matters.
3. The client reads the selected page or sections.
4. Responses include URLs and concise context that are easy to cite.
5. Failures return actionable recovery guidance.

## Proposed UX Improvements

### Tool Descriptions

Refine tool descriptions so clients know when and how to call each tool.

- `search_documentation`: use first for broad OCI documentation discovery.
- `read_documentation`: use when the client has a specific OCI docs URL.
- `read_sections`: use after reading or searching when only named page sections are needed.

The server instructions should explicitly recommend this sequence: search, read the best result, then cite the documentation URL.

### Search Results

Enhance search result fields so clients can make better choices without reading every page.

Candidate fields:

- `rank_order`: current search order.
- `url`: canonical docs URL.
- `title`: result title.
- `context`: short excerpt or summary.
- `sections`: matched or likely relevant section titles.
- `service`: inferred OCI service name when available.
- `doc_type`: inferred category such as concept, task, reference, API, or release note.
- `next_action`: short hint such as `read_documentation` or `read_sections`.

Keep existing fields stable where possible, and add optional fields for backward compatibility.

### Error And Recovery Messages

Replace generic failures with actionable messages.

Examples:

- Invalid URL: say that only `https://docs.oracle.com/en-us/iaas/` documentation URLs are supported, and suggest using `search_documentation` first.
- No results: suggest broadening the query, including the OCI service name, or searching for a task phrase.
- Search backend failure: include status, query id, and a retry suggestion.
- Empty parsed result: report that Oracle returned content but no documentation results were recognized.

### Client Onboarding

Update README client setup after the full OCI rebrand.

- OCI-branded install snippets for common clients.
- One-minute smoke test prompt.
- Example prompts grouped by task: search, read, section extraction, citation.
- Brief troubleshooting for network, User-Agent, and unsupported URLs.

## Non-Goals

- Building a visual dashboard.
- Adding non-OCI providers.
- Reworking the whole MCP protocol layer.
- Implementing local indexing or semantic search in the first pass.

## Acceptance Criteria

- MCP tool descriptions make the intended client workflow obvious.
- Search results are easier for clients to rank and cite.
- Error responses include a concrete next step.
- README no longer exposes AWS-branded client examples.
- Existing tests continue to pass, with new tests for enriched results and recovery messages.

## Suggested Implementation Order

1. Update models with optional client-friendly metadata fields.
2. Improve OCI parser enrichment for service, doc type, sections, and excerpts.
3. Refine FastMCP instructions and tool parameter descriptions.
4. Improve error responses and no-result behavior.
5. Update README client onboarding examples.
6. Add focused tests for response shape and recovery text.

## Open Questions

- Should `next_action` be a plain string or a structured object with tool name and arguments?
- Should `read_documentation` return a structured response later, or remain markdown text for compatibility?
- How much service/doc-type inference should be parser-based versus conservative heuristics?
