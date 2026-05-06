# Convert AWS Documentation MCP Server to OCI Documentation Implementation Plan
> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

## Goal

Convert this repository from an AWS Documentation MCP server into an OCI Documentation MCP server. The finished server should search, read, and section-read Oracle Cloud Infrastructure documentation from official Oracle documentation sources, with AWS-specific package names, environment variables, modules, tests, and README content removed or renamed.

## Scope

In scope:
- Full package rebrand from `awslabs.aws_documentation_mcp_server` to `oci_documentation_mcp_server`.
- OCI documentation tools:
  - `read_documentation`
  - `read_sections`
  - `search_documentation`
- Provider-neutral shared fetch/format helpers that say `OCI Documentation`, not `AWS Documentation`.
- Test suite conversion from AWS fixtures and domains to OCI fixtures and domains.
- README, package metadata, Docker, healthcheck, and changelog/reference cleanup.

Out of scope unless discovered in Task 1:
- `recommend`; remove it unless OCI has an official equivalent that can be verified and tested.
- AWS global and AWS China compatibility.
- Publishing/release automation.

## Critical Unknown

OCI's public search page returns HTML, but live verification showed that the browser app loads results from a JSON backend at `https://docs.oracle.com/apps/ohcsearchclient/api/v2/search/pages`. Use context-mode for any web/API exploration; do not use `curl` or `wget`.

The preferred discovery output is:
- canonical OCI docs base URL
- accepted URL patterns for OCI docs pages
- backend search endpoint URL, request parameters, and required AJAX headers
- JSON parsing rules for hits, titles, links, snippets, and pagination if present
- HTML fallback parsing rules for result blocks, titles, links, and snippets if needed
- representative fixtures saved under `tests/resources/`

## Target Architecture

- `oci_documentation_mcp_server/server.py`: logging setup and direct OCI server entrypoint.
- `oci_documentation_mcp_server/server_oci.py`: FastMCP server and OCI tool wrappers.
- `oci_documentation_mcp_server/server_utils.py`: shared HTTP fetch, content-type handling, pagination, section extraction, and search-result cache if still needed.
- `oci_documentation_mcp_server/util.py`: Oracle docs HTML cleanup, Markdown conversion, section extraction, search parsing helpers.
- `oci_documentation_mcp_server/models.py`: generic `SearchResult` and `SearchResponse`; remove `RecommendationResult` unless `recommend` survives.

## Task 1: Verify OCI Documentation Contract

- Create: `docs/oci-documentation-contract.md`
- Create: `tests/resources/oci_compute_instance_raw.html`
- Create: `tests/resources/oci_search_compute_results.json`
- Create: `tests/resources/oci_search_compute_results.html`
- Modify: none yet
- Test: none yet

- [ ] Use context-mode to inspect official OCI documentation pages and search behavior. Use `mcp__context_mode__ctx_execute` or `ctx_fetch_and_index` if available; do not use `curl`/`wget`.
- [ ] Verify a stable sample read URL, likely under `https://docs.oracle.com/en-us/iaas/`.
- [ ] Verify a stable sample search request for a query such as `compute instance`.
- [ ] Save one representative OCI docs HTML fixture to `tests/resources/oci_compute_instance_raw.html`.
- [ ] Save one representative JSON search response fixture to `tests/resources/oci_search_compute_results.json`.
- [ ] Keep one representative HTML search response fixture at `tests/resources/oci_search_compute_results.html` for fallback parser coverage.
- [ ] Write `docs/oci-documentation-contract.md` with:
  - base docs URL
  - URL validation rules
  - search URL or fallback strategy
  - expected search result fields
  - any known limitations
- [ ] Commit:
  - `git add docs/oci-documentation-contract.md tests/resources/oci_*`
  - `git commit -m "Document OCI documentation source contract"`

## Task 2: Rebrand Package and Entrypoint

- Create: `oci_documentation_mcp_server/__init__.py`
- Move/copy then update:
  - `awslabs/aws_documentation_mcp_server/models.py` -> `oci_documentation_mcp_server/models.py`
  - `awslabs/aws_documentation_mcp_server/server.py` -> `oci_documentation_mcp_server/server.py`
  - `awslabs/aws_documentation_mcp_server/server_utils.py` -> `oci_documentation_mcp_server/server_utils.py`
  - `awslabs/aws_documentation_mcp_server/util.py` -> `oci_documentation_mcp_server/util.py`
- Create: `oci_documentation_mcp_server/server_oci.py`
- Modify: `pyproject.toml`
- Test: `tests/test_server.py`, `tests/test_models.py`

- [ ] Write failing import tests in `tests/test_server.py` that import `oci_documentation_mcp_server.server.main`.
- [ ] Write failing model import tests in `tests/test_models.py` that import from `oci_documentation_mcp_server.models`.
- [ ] Run: `uv run pytest tests/test_server.py tests/test_models.py -q`; expect import failures.
- [ ] Create the new package files.
- [ ] Update imports from `awslabs.aws_documentation_mcp_server` to `oci_documentation_mcp_server`.
- [ ] Update `pyproject.toml`:
  - package name to `oci-documentation-mcp-server`
  - console script to `oci-documentation-mcp-server = "oci_documentation_mcp_server.server:main"`
  - description to OCI wording
  - project URLs away from AWS Labs links or mark local/TBD
  - commitizen version path to `oci_documentation_mcp_server/__init__.py`
- [ ] Run: `uv run pytest tests/test_server.py tests/test_models.py -q`; expect pass.
- [ ] Commit:
  - `git add pyproject.toml oci_documentation_mcp_server tests/test_server.py tests/test_models.py`
  - `git commit -m "Rebrand package for OCI documentation MCP server"`

## Task 3: Implement OCI Tool Surface

- Create/Modify: `oci_documentation_mcp_server/server_oci.py`
- Modify: `oci_documentation_mcp_server/server.py`
- Test: `tests/test_server_oci.py`

- [ ] Create `tests/test_server_oci.py`.
- [ ] Add tests for `read_documentation` accepting valid OCI docs URLs from `docs/oci-documentation-contract.md`.
- [ ] Add tests for rejecting non-Oracle or non-OCI URLs.
- [ ] Add tests for `read_sections` delegating to `read_sections_impl`.
- [ ] Add tests for `search_documentation` calling the OCI search helper and returning `SearchResponse`.
- [ ] Run: `uv run pytest tests/test_server_oci.py -q`; expect failures.
- [ ] Implement `server_oci.py` with `FastMCP(name="oci-documentation-mcp-server")`.
- [ ] Expose only verified tools:
  - `read_documentation`
  - `read_sections`
  - `search_documentation`
- [ ] Remove partition dispatch from `server.py`; it should import and run `server_oci.main`.
- [ ] Run: `uv run pytest tests/test_server_oci.py tests/test_server.py -q`; expect pass.
- [ ] Commit:
  - `git add oci_documentation_mcp_server/server.py oci_documentation_mcp_server/server_oci.py tests/test_server_oci.py`
  - `git commit -m "Add OCI MCP tool surface"`

## Task 4: Convert Shared Fetching and Formatting

- Modify: `oci_documentation_mcp_server/server_utils.py`
- Modify: `oci_documentation_mcp_server/util.py`
- Test: `tests/test_server_utils.py`, `tests/test_util.py`

- [ ] Rename output text from `AWS Documentation from ...` to `OCI Documentation from ...`.
- [ ] Replace user-agent branding with `OCI Documentation Server`.
- [ ] Keep `MCP_USER_AGENT` override support.
- [ ] Add Oracle docs cleanup selectors based on the fixture from Task 1.
- [ ] Ensure `format_documentation_result` pagination still returns:
  - source URL
  - content window
  - clear continuation guidance when truncated
  - no-more-content message when `start_index` is past content length
- [ ] Ensure `extract_sections_from_html` works against OCI heading structure. If OCI pages use heading levels other than `h2`, support the minimal verified heading levels from the fixture.
- [ ] Run: `uv run pytest tests/test_server_utils.py tests/test_util.py -q`; expect failures first, then pass after implementation.
- [ ] Commit:
  - `git add oci_documentation_mcp_server/server_utils.py oci_documentation_mcp_server/util.py tests/test_server_utils.py tests/test_util.py`
  - `git commit -m "Adapt documentation parsing and formatting for OCI"`

## Task 5: Implement OCI Search

- Modify: `oci_documentation_mcp_server/server_oci.py`
- Modify: `oci_documentation_mcp_server/util.py`
- Modify: `oci_documentation_mcp_server/models.py`
- Create: `tests/test_oci_search.py`
- Modify or remove: `tests/test_metadata_handling.py`

- [ ] Write fixture-based tests for parsing OCI search results from the Task 1 fixture.
- [ ] Tests should assert:
  - result URL belongs to the verified OCI docs domain/path
  - title is populated
  - context/snippet is populated when available
  - `rank_order` is stable and 1-based
  - `query_id` is present even if locally generated
  - `limit` is honored
- [ ] Decide whether OCI search supports facets. If not, keep `facets=None` and remove AWS facet tests.
- [ ] Run: `uv run pytest tests/test_oci_search.py tests/test_metadata_handling.py -q`; expect failures.
- [ ] Implement OCI search request builder and parser.
- [ ] Isolate JSON parsing into a helper such as `parse_oci_search_response`.
- [ ] Keep HTML fallback parsing in a helper such as `parse_oci_search_results`.
- [ ] Preserve the existing `SearchResponse` shape unless the verified OCI contract requires a small compatible adjustment.
- [ ] Run: `uv run pytest tests/test_oci_search.py tests/test_metadata_handling.py -q`; expect pass.
- [ ] Commit:
  - `git add oci_documentation_mcp_server tests/test_oci_search.py tests/test_metadata_handling.py`
  - `git commit -m "Implement OCI documentation search"`

## Task 6: Remove AWS-Only Modules and Tests

- Delete after replacement tests pass:
  - `awslabs/aws_documentation_mcp_server/`
  - `awslabs/__init__.py`
  - `tests/test_server_aws.py`
  - `tests/test_server_aws_cn.py`
  - `tests/test_aws_search_live.py`
  - `tests/test_aws_read_documentation_live.py`
  - `tests/test_aws_read_sections_live.py`
  - `tests/test_aws_recommend_live.py`
  - `tests/test_aws_cn_read_documentation_live.py`
  - `tests/test_aws_cn_get_available_services_live.py`
- Create/rename:
  - `tests/test_oci_read_documentation_live.py`
  - `tests/test_oci_read_sections_live.py`
  - `tests/test_oci_search_live.py`

- [ ] Rename or recreate live tests for OCI docs using the verified contract.
- [ ] Remove `recommend` tests unless an OCI equivalent was verified.
- [ ] Run: `uv run pytest -m "not live" -q`; expect no AWS import or AWS URL failures.
- [ ] Run live tests only if network access and `--run-live` are intentionally available:
  - `uv run pytest --run-live tests/test_oci_*_live.py -q`
- [ ] Commit:
  - `git add -A`
  - `git commit -m "Remove AWS-specific implementation and tests"`

## Task 7: Update Docs, Docker, and Healthcheck

- Modify: `README.md`
- Modify: `Dockerfile`
- Modify: `docker-healthcheck.sh`
- Modify: `CHANGELOG.md`
- Review: `LICENSE`, `NOTICE`

- [ ] Replace AWS usage examples with OCI examples.
- [ ] Remove `AWS_DOCUMENTATION_PARTITION`.
- [ ] Keep `FASTMCP_LOG_LEVEL` and `MCP_USER_AGENT`.
- [ ] Update install examples to use `oci-documentation-mcp-server`.
- [ ] Update Docker image examples from `mcp/aws-documentation` to `mcp/oci-documentation`.
- [ ] Update healthcheck command to use the new console script/package import.
- [ ] Review `LICENSE` and `NOTICE`; update only if ownership/project attribution is incorrect for this fork.
- [ ] Run: `uv run pytest -m "not live" -q`.
- [ ] Commit:
  - `git add README.md Dockerfile docker-healthcheck.sh CHANGELOG.md LICENSE NOTICE`
  - `git commit -m "Update documentation for OCI MCP server"`

## Task 8: Final Verification and Cleanup

- Modify: any remaining files found by search
- Test: full non-live suite

- [ ] Run: `rg -n "AWS|aws|awslabs|amazonaws|docs\\.aws|docs\\.amazonaws" . -g '!uv.lock'`.
- [ ] For each remaining match, either remove it or confirm it belongs in historical/changelog/license context.
- [ ] Run: `uv run ruff check .`.
- [ ] Run: `uv run pyright`.
- [ ] Run: `uv run pytest -m "not live" -q`.
- [ ] Optional live verification:
  - `uv run pytest --run-live tests/test_oci_*_live.py -q`
- [ ] Update Basic Memory with implementation decisions, blockers, and final state.
- [ ] Commit:
  - `git add -A`
  - `git commit -m "Verify OCI documentation MCP migration"`

## Implementation Notes

- Keep the old AWS files until OCI tests pass; delete them only in Task 6.
- Avoid inventing OCI recommendations support. Search/read/section-read are enough for the first working conversion.
- Preserve MCP tool parameter names where possible so existing client prompts remain intuitive.
- Prefer a small, well-tested HTML parser for Oracle docs search results over adding a heavy dependency.
- If the OCI docs site requires JavaScript for search, add a documented fallback strategy before implementing: a static Oracle docs sitemap source, a constrained docs index, or a search-provider integration chosen by the project owner.
