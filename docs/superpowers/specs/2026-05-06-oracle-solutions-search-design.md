# Oracle Solutions Search Integration Design

Date: 2026-05-06
Status: approved direction, written spec
Scope: Oracle Architecture Center and Solutions search for MCP clients

## Goal

Integrate Oracle Architecture Center content from `https://docs.oracle.com/solutions/` into the OCI documentation MCP experience as official Oracle solution content.

This source should help users find reference architectures, solution playbooks, and built/deployed examples without mixing them up with blog posts.

## Recommendation

Treat Architecture Center content as an official documentation-adjacent source. It should be closer to OCI documentation search than Oracle Blogs.

Use it when users ask for:

- reference architectures
- implementation patterns
- deployment examples
- solution playbooks
- multicloud or workload architecture guidance
- built and deployed customer-style examples

## Confirmed Endpoint

Main asset endpoint:

```text
https://docs.oracle.com/apps/ohcsearchclient/api/v1/search/assets
```

Confirmed parameters:

- `pg`
- `size`
- `lang`
- `cType`
- `services`
- `product`
- `technologies`
- `q`
- `sort`

Useful content type values:

- `reference-architectures`
- `solution-playbook`
- `built-deployed`

Confirmed sort examples:

- `date-desc`
- `relevance`

## Response Shape

The asset response includes:

- `pagination`
- `hits`

Each hit includes:

- `_id`
- `_score`
- `_source`
- `highlight`

Useful `_source` fields include:

- `title`
- `description`
- `url`
- `content_type`
- `publish_date`
- `breadcrumbs`
- `technologies`
- `formats`
- `lang`

## Supporting Endpoints

Aggregation endpoint:

```text
https://docs.oracle.com/apps/ohcsearchclient/api/v1/search/assetsAggs
```

Taxonomy endpoint:

```text
https://docs.oracle.com/apps/ohcsearchclient/api/v1/search/taxonomies?name=technologies,services&combined=true
```

Use these for filters, facets, and client-facing labels.

## Client UX Behavior

Solutions results should be clearly labeled separately from normal OCI docs and blogs.

Recommended source labels:

- `official_docs`
- `architecture_center`
- `oracle_blog`

Architecture Center result fields should include:

- title
- URL
- description
- source type
- content type
- publish date
- technologies
- highlights when available

Clients should prefer Architecture Center results when the user asks for architecture, design, deployment, or implementation patterns.

## Suggested Tool Flow

For ordinary documentation questions:

1. Search OCI documentation first.
2. Include Architecture Center results when the query suggests architecture, deployment, examples, or solutions.
3. Prefer exact official docs for command/API/reference answers.

For architecture questions:

1. Search Architecture Center assets directly.
2. Filter by relevant `cType` values.
3. Return source-labeled results with publish dates and technologies.
4. Read the selected solution URL for answer details.

## Implementation Order

1. Add Architecture Center result model fields.
2. Implement an assets API client.
3. Implement response parsing for `pagination`, `hits`, `_source`, and `highlight`.
4. Add content-type normalization for reference architectures, solution playbooks, and built/deployed examples.
5. Add source labels and merge/dedupe behavior with OCI docs results.
6. Add fixture-backed tests for search results, empty results, and API failures.
7. Update README/tool descriptions with source behavior.

## Acceptance Criteria

- Architecture Center API fixtures parse into stable result models.
- Results include URL, title, description, content type, publish date, technologies, and source label.
- Search can filter by the confirmed `cType` values.
- Architecture Center results are not mislabeled as blogs.
- Official docs remain preferred for normative reference answers.
- API failures return recoverable, client-friendly messages.

## Open Questions

- Should Architecture Center be exposed through a dedicated tool or a unified search source option?
- Should default search include Architecture Center automatically for all queries or only intent-matched queries?
- Should filters use raw Oracle `cType` values or friendlier MCP enum names?
