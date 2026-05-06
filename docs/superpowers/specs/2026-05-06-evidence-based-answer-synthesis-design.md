# Evidence-Based Answer Synthesis Design

Date: 2026-05-06
Status: approved direction, written spec
Scope: turning OCI documentation, Architecture Center, and Oracle Blogs results into client-ready answers

## Goal

Create a consistent internal flow that turns heterogeneous returned content into reliable, cited answers.

Search results should not become final answers directly. They should become candidates, candidates should become evidence, and evidence should become a cited answer.

## Source Roles

Use source roles to decide how each result should contribute.

- `official_docs`: best for normative product behavior, configuration, APIs, limits, and procedural steps.
- `architecture_center`: best for design patterns, reference architectures, solution playbooks, and deployment examples.
- `oracle_blog`: best for announcements, recent context, examples, launch notes, and product direction.

## Normalized Evidence Candidate

All retrieved items should be normalized into one shape before ranking or synthesis.

```text
source_type
url
title
description_or_excerpt
published_at
content_type
service_tags
product_tags
technology_tags
matched_sections
highlights
authority_score
freshness_score
query_relevance_score
recommended_use
```

Optional fields should be allowed because sources expose different metadata.

## Intent Classification

Before ranking, classify the user request.

Suggested intent labels:

- `reference`: factual product behavior, API, configuration, limits
- `how_to`: step-by-step implementation
- `architecture`: design or deployment pattern
- `comparison`: compare services, clouds, products, or approaches
- `latest`: recent changes, announcements, roadmap-like context
- `example`: practical examples or customer-style deployments

Intent should guide source priority.

## Ranking Strategy

Rank by source role plus relevance, not text match alone.

Default source priority:

- `reference` and `how_to`: official docs first
- `architecture`: Architecture Center first, official docs second
- `comparison`: Architecture Center and official docs together
- `latest`: blogs first for recency, official docs for validation
- `example`: Architecture Center and blogs first, official docs for details

Ranking score can combine:

- query relevance
- source authority for the detected intent
- freshness when recency matters
- content type fit
- section/highlight match quality

## Reading Strategy

Do not synthesize substantial answers from snippets alone.

For substantive answers:

1. Search one or more sources.
2. Normalize candidates.
3. Rank candidates.
4. Read top URLs or sections.
5. Extract evidence chunks.
6. Build an evidence bundle.
7. Synthesize the answer with citations.

For simple list/discovery requests, search result metadata may be enough.

## Evidence Bundle

An evidence bundle should group extracted content by claim or answer part.

Suggested bundle fields:

```text
user_intent
answer_outline
claims
supporting_sources
source_conflicts
confidence
missing_information
```

Each claim should retain citation URLs and source type.

## Conflict Handling

When sources disagree:

- prefer official docs for current normative behavior
- use Architecture Center for design context
- use blogs only as time-sensitive context unless no better source exists
- mention uncertainty when content is stale, ambiguous, or unsupported

## Client-Facing Output

Answers should:

- state the recommendation or answer first
- cite URLs for material claims
- distinguish official docs, Architecture Center, and blog context
- call out freshness when blogs or dated solution assets matter
- avoid presenting blog content as official product reference

## Implementation Order

1. Add normalized source/result models.
2. Add intent classification helper.
3. Add source-role ranking helper.
4. Add evidence bundle builder.
5. Update search/read orchestration to read top ranked URLs before synthesis.
6. Add tests for intent routing, source priority, dedupe, and conflict handling.
7. Update README/tool descriptions with source behavior.

## Acceptance Criteria

- Results from OCI docs, Architecture Center, and blogs normalize into a common shape.
- Source type is preserved through ranking, reading, and final answer construction.
- Architecture questions prioritize Architecture Center.
- Reference and how-to questions prioritize official docs.
- Latest/example questions can use blogs while clearly labeling them.
- Final answers can cite the source URLs used for each material claim.

## Open Questions

- Should answer synthesis live inside this MCP server, or should the server return evidence bundles for the client model to synthesize?
- Should intent classification be rule-based first, or delegated to the client model?
- Should evidence bundles be exposed as a separate tool response type?
