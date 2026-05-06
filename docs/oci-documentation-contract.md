# OCI Documentation Contract

## Status

Provisional implementation contract. Live verification showed that the public Oracle search page is HTML, but its browser app fetches results from a JSON backend endpoint.

## Documentation URLs

- Canonical OCI documentation base: `https://docs.oracle.com/en-us/iaas/`
- Accepted read URLs: `https://docs.oracle.com/en-us/iaas/...`
- Non-OCI Oracle pages, such as `https://www.oracle.com/...`, are filtered out of search results.

## Search

- Public search page: `https://docs.oracle.com/search/`
- Backend search URL: `https://docs.oracle.com/apps/ohcsearchclient/api/v2/search/pages`
- Query parameter: `q`
- Paging parameters: `pg`, `size`
- Language parameter: `lang`
- Required request headers observed during live verification:
  - `Accept: application/json, text/javascript, */*; q=0.01`
  - `Referer: https://docs.oracle.com/search/?q=<query>`
  - `X-Requested-With: XMLHttpRequest`
- Backend response format: JSON with `hits`, `links`, and `pagination`.
- Public page response format: HTML shell that loads results with JavaScript.

## Parser Expectations

The JSON parser extracts:
- result hits from `hits`
- title from `_source.title`
- URL from `_source.url`
- context from `highlight.description`, then `highlight.body`, then source description/snippet fields
- 1-based result rank order

The HTML fallback parser extracts:
- result containers using common result selectors such as `.search-result`, `.result`, `.result-item`, and article-like blocks
- the first OCI documentation anchor inside each result container
- title from the anchor text
- context from snippet-like elements such as `.result-snippet`, `.search-result-snippet`, `.snippet`, `.description`, `p`, or `dd`
- 1-based result rank order

## Current Limitations

- Facets are not implemented; `SearchResponse.facets` is `None`.
- Pagination is not exposed through the MCP tool yet.
- Production result ranking/filtering should be rechecked periodically because the endpoint is used by Oracle's browser search app rather than a separately documented public API.
