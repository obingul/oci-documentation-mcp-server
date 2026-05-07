# Combine Oracle Source Pipeline Implementation Plan
> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Files:**
- Modify: `oci_documentation_mcp_server/models.py`
- Modify: `oci_documentation_mcp_server/util.py`
- Modify: `oci_documentation_mcp_server/evidence.py`
- Modify: `oci_documentation_mcp_server/server_oci.py`
- Modify: `tests/test_oci_search.py`
- Modify: `tests/test_evidence.py`
- Modify: `tests/test_server_oci.py`
- Modify: `README.md`

- [x] **Step 1: Write failing parser/source-role tests**
  - In `tests/test_oci_search.py`, assert `/en/learn/` maps to `SourceType.LEARN`, `/en/paas/` maps to `SourceType.PAAS_DOCS`, `/solutions/` maps to `SourceType.ARCHITECTURE_CENTER`, and `/en-us/iaas/` remains `SourceType.OFFICIAL_DOCS`.

- [x] **Step 2: Run parser/source-role tests red**
  - Run: `uv run pytest tests/test_oci_search.py -q`

- [x] **Step 3: Implement source types and URL mapping**
  - Add `LEARN = "learn"` and `PAAS_DOCS = "paas_docs"` to `SourceType`.
  - Update `_source_type_for_url()` in `util.py` to map Learn and PaaS roots.

- [x] **Step 4: Run parser/source-role tests green**
  - Run: `uv run pytest tests/test_oci_search.py -q`

- [x] **Step 5: Write failing intent-ranking tests**
  - In `tests/test_evidence.py`, add assertions for reference, how-to, architecture, latest, and example intent ordering across PaaS, Learn, Architecture Center, Blog, and general official docs.

- [x] **Step 6: Run ranking tests red**
  - Run: `uv run pytest tests/test_evidence.py -q`

- [x] **Step 7: Implement intent-aware source priorities**
  - Update `_source_priority()` in `evidence.py` so PaaS wins reference, Learn wins how-to/example, Architecture Center wins architecture/comparison, and Blog wins latest.

- [x] **Step 8: Run ranking tests green**
  - Run: `uv run pytest tests/test_evidence.py -q`

- [x] **Step 9: Write failing aggregation test if needed**
  - In `tests/test_server_oci.py`, assert `search_documentation()` includes generic docs results plus Architecture Center results using existing helper functions when the primary search succeeds.

- [x] **Step 10: Implement minimal aggregation**
  - If the existing `architecture_center.py` helper can be called without broad new API design, add a private `_search_architecture_center()` helper in `server_oci.py`, combine and dedupe results with generic docs results, then rank by intent.
  - Leave Oracle Blog live aggregation out of this slice unless an existing server helper already exists; blog entries remain supported in evidence ranking and model output.

- [x] **Step 11: Document source roles**
  - Update `README.md` to describe source roles and combined ranking behavior.

- [x] **Step 12: Verify all checks**
  - Run: `uv run pytest -q`
  - Run: `uv run ruff check oci_documentation_mcp_server tests`
  - Run: `uv run pyright oci_documentation_mcp_server tests`
