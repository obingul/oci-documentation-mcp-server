# Evidence Search Foundation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first implementation slice for relating OCI docs, Architecture Center, and Oracle Blogs results into normalized evidence candidates.

**Architecture:** Add optional source/evidence metadata to the existing `SearchResult` model, then implement focused parser/client helpers for Architecture Center and Oracle Blogs. Keep MCP tool surface changes out of this slice so tests can prove the source contracts first.

**Tech Stack:** Python 3.10+, Pydantic v2, httpx, pytest, existing `oci_documentation_mcp_server` package.

---

## Chunk 1: Normalized Evidence Models

### Task 1: Extend Models Without Breaking Existing Search

**Files:**
- Modify: `oci_documentation_mcp_server/models.py`
- Test: `tests/test_oci_evidence_models.py`

- [x] Write failing tests that create `SearchResult` values for `official_docs`, `architecture_center`, and `oracle_blog`.
- [x] Verify the tests fail because the new enum/model fields do not exist.
- [x] Add `SourceType`, `IntentType`, `EvidenceCandidate`, `EvidenceBundle`, and optional metadata fields on `SearchResult`.
- [x] Verify model tests pass.

## Chunk 2: Architecture Center Source

### Task 2: Parse And Build Architecture Center Requests

**Files:**
- Create: `oci_documentation_mcp_server/architecture_center.py`
- Create: `tests/resources/oracle_solutions_assets.json`
- Test: `tests/test_architecture_center.py`

- [x] Write failing tests for building the assets URL and parsing fixture hits into `SearchResult`.
- [x] Verify tests fail because the module does not exist.
- [x] Implement URL builder and response parser for `/apps/ohcsearchclient/api/v1/search/assets`.
- [x] Verify Architecture Center tests pass.

## Chunk 3: Oracle Blogs Source

### Task 3: Parse Blog Search And RSS Feeds

**Files:**
- Create: `oci_documentation_mcp_server/oracle_blogs.py`
- Create: `tests/resources/oracle_blog_search_results.json`
- Create: `tests/resources/oracle_blog_feed.xml`
- Test: `tests/test_oracle_blogs.py`

- [x] Write failing tests for building the blog search URL, parsing search JSON, and parsing RSS XML.
- [x] Verify tests fail because the module does not exist.
- [x] Implement URL builder, search parser, and RSS parser.
- [x] Verify Oracle Blogs tests pass.

## Chunk 4: Evidence Bundle Helpers

### Task 4: Rank And Bundle Evidence

**Files:**
- Create: `oci_documentation_mcp_server/evidence.py`
- Test: `tests/test_evidence.py`

- [x] Write failing tests for intent-aware source ranking and URL dedupe.
- [x] Verify tests fail because helper functions do not exist.
- [x] Implement simple rule-based intent classification, source-priority scoring, dedupe, and bundle construction.
- [x] Verify evidence tests pass.

## Final Verification

- [x] Run focused tests:
  `uv run pytest tests/test_oci_evidence_models.py tests/test_architecture_center.py tests/test_oracle_blogs.py tests/test_evidence.py -q`
- [x] Run existing OCI tests:
  `uv run pytest tests/test_oci_search.py tests/test_server_oci.py -q`
- [x] Run lint/type checks for changed package and tests if available:
  `uv run ruff check oci_documentation_mcp_server tests/test_oci_evidence_models.py tests/test_architecture_center.py tests/test_oracle_blogs.py tests/test_evidence.py`
  `uv run pyright oci_documentation_mcp_server tests/test_oci_evidence_models.py tests/test_architecture_center.py tests/test_oracle_blogs.py tests/test_evidence.py`

## Notes

- This workspace is not a git repository, so commit steps are intentionally omitted.
- Keep all new source fields optional to preserve current MCP clients.
- Do not fetch live Oracle endpoints in unit tests; use fixtures only.
