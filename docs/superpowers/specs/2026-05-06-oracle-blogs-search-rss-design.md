# Oracle Blogs Search And RSS Integration Design

Date: 2026-05-06
Status: approved direction, written spec
Scope: Oracle Blogs discovery for client-facing MCP search experiences

## Goal

Add Oracle Blogs as a useful companion source for OCI-related discovery without confusing it with official OCI documentation. Blog content should help with announcements, examples, architecture posts, release context, and recent changes.

## Recommendation

Use a hybrid source strategy:

1. Use Oracle Blogs Search API for broad live keyword search.
2. Use RSS feeds for category-scoped freshness, incremental indexing, and seed URL discovery.
3. Merge and dedupe results by canonical URL.
4. Label blog results clearly so clients can distinguish blog content from official documentation.

## Confirmed Search API

Endpoint:

```text
https://search-api.oracle.com/api/v1/search/blogs
```

Confirmed query parameters:

- `app=blogsui`
- `q=<query>`
- `offset=<number>`
- `size=<number>`

Confirmed response shape:

- top-level `total`
- top-level `results`
- result fields include `title`, `display_url`, `description`, `blog_name`, `display_date`, `author`, `keywords`, `document_id`, and ranking scores

Notes:

- Pagination works with `offset` and `size`.
- `category=cloud-infrastructure` returned `400` during probing, so category filtering is not confirmed.
- API responses set `access-control-allow-origin: https://blogs.oracle.com`.

## Confirmed RSS Feeds

The following feeds returned `200` in browser checks:

- `https://blogs.oracle.com/cloud-infrastructure/feed`
- `https://blogs.oracle.com/ai-and-datascience/feed`
- `https://blogs.oracle.com/analytics/feed`
- `https://blogs.oracle.com/security/feed`
- `https://blogs.oracle.com/developers/feed`
- `https://blogs.oracle.com/database/feed`
- `https://blogs.oracle.com/maa/feed`

The `/rss` variants for security, developers, database, and maa normalize to `/feed`.

RSS item fields include:

- `title`
- `link`
- `pubDate`
- `description`
- `category`

## Fetching Constraints

Oracle Blogs may return `403` to direct non-browser fetches, including RSS and WordPress REST endpoints. The browser can load the feeds successfully.

Implementation should account for this by:

- sending browser-like request headers where appropriate
- keeping fetch failures recoverable
- falling back to the search API for live user queries
- avoiding hard dependency on WordPress REST endpoints

## Client UX Behavior

Search tools should label result source type:

- `official_docs`
- `oracle_blog`

Blog results should include:

- title
- URL
- blog name
- author when available
- publish date
- description or excerpt
- categories or keywords
- source type

Client-facing guidance should prefer official documentation for normative answers and use blog results for recent context, examples, launch posts, and product announcements.

## Suggested Tool Flow

For broad queries:

1. Search official OCI documentation.
2. Search Oracle Blogs when user intent suggests recency, examples, announcements, architecture, or product updates.
3. Merge results with source labels.
4. Prefer official docs in final answers unless blog freshness matters.

For latest/category queries:

1. Read the relevant RSS feed or local feed cache.
2. Return recent posts from the requested category.
3. Optionally enrich with live search API results.

## Implementation Order

1. Add Oracle Blogs source models with optional fields for author, date, blog name, keywords, and source type.
2. Add a search API client for `search-api.oracle.com/api/v1/search/blogs`.
3. Add RSS feed parsing for configured feeds.
4. Add dedupe and source labeling.
5. Add fallback behavior for `403`, malformed RSS, and empty results.
6. Add tests with saved search API and RSS fixtures.
7. Update README/tool descriptions to explain when blog results are used.

## Acceptance Criteria

- Search API fixture parses into stable blog result models.
- RSS fixture parses titles, URLs, dates, descriptions, and categories.
- Duplicate URLs are merged or removed.
- Blog results are clearly labeled as blogs.
- Fetch failures return actionable messages and do not break official documentation search.
- README documents blog search as companion context, not official docs replacement.

## Open Questions

- Should blog search be a separate MCP tool or folded into a unified search tool?
- Should RSS content be cached locally, or fetched on demand only?
- What freshness window should client-facing queries use by default?
