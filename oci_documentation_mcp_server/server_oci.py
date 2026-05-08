"""OCI Documentation MCP Server."""

import httpx
import os
import uuid
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from oci_documentation_mcp_server.architecture_center import (
    ARCHITECTURE_CENTER_REFERER,
    build_architecture_center_search_url,
    parse_architecture_center_response,
)
from oci_documentation_mcp_server.evidence import (
    build_cited_answer,
    classify_intent,
    dedupe_search_results,
    rank_search_results,
)
from oci_documentation_mcp_server.models import (
    AnswerResponse,
    SearchResponse,
    SearchResult,
    SourceDocument,
)
from oci_documentation_mcp_server.oracle_blogs import (
    ORACLE_BLOG_REFERER,
    build_oracle_blog_search_url,
    parse_oracle_blog_search_response,
)
from oci_documentation_mcp_server.server_utils import (
    DEFAULT_USER_AGENT,
    add_search_result_cache_item,
    read_documentation_impl,
    read_sections_impl,
)
from oci_documentation_mcp_server.util import (
    DEFAULT_OCI_SEARCH_URL,
    build_oci_search_referer,
    build_oci_search_url,
    is_oci_documentation_url,
    parse_oci_search_response,
    parse_oci_search_results,
)
from pydantic import Field
from typing import List, Optional
from urllib.parse import urlparse


SESSION_UUID = str(uuid.uuid4())
OCI_SEARCH_URL = os.getenv('OCI_DOCUMENTATION_SEARCH_URL', DEFAULT_OCI_SEARCH_URL)

mcp = FastMCP(
    'oci-documentation-mcp-server',
    instructions=(
        'Use this server to search, read, and extract sections from Oracle Cloud '
        'Infrastructure documentation.'
    ),
    dependencies=[
        'httpx',
        'beautifulsoup4',
        'markdownify',
        'pydantic',
    ],
)


@mcp.prompt(
    name='ask_oci_docs',
    title='Ask OCI Docs',
    description='Answer an OCI documentation question by searching, reading, and citing sources.',
)
def ask_oci_docs(question: str) -> str:
    """Create a prompt for answering an OCI documentation question with citations."""
    return (
        'Use the `answer_question` tool to answer this OCI documentation question. '
        'Read relevant OCI documentation before answering, cite every material claim, '
        f'and include the source URLs.\n\nQuestion: {question}'
    )


@mcp.prompt(
    name='how_to_oci',
    title='OCI How-To',
    description='Answer an OCI how-to question from task-oriented OCI documentation.',
)
def how_to_oci(task: str) -> str:
    """Create a prompt for task-oriented OCI documentation answers."""
    return (
        'Use the `answer_question` tool for this OCI how-to task. Prefer task pages, '
        'CLI sections, API operation names, prerequisites, and cited step-level evidence.\n\n'
        f'Task: {task}'
    )


@mcp.prompt(
    name='compare_oci_services',
    title='Compare OCI Services',
    description='Compare OCI services or options using cited OCI documentation.',
)
def compare_oci_services(question: str) -> str:
    """Create a prompt for cited OCI comparison answers."""
    return (
        'Use OCI documentation tools to search and read relevant OCI documentation before '
        'answering. Compare only what the cited sources support, call out missing evidence, '
        f'and cite source URLs.\n\nQuestion: {question}'
    )


@mcp.tool()
async def read_documentation(
    ctx: Context,
    url: str = Field(description='URL of the OCI documentation page to read'),
    max_length: int = Field(
        default=5000,
        description='Maximum number of characters to return.',
        gt=0,
        le=20000,
    ),
    start_index: int = Field(
        default=0,
        description='Start index for pagination.',
        ge=0,
    ),
) -> str:
    """Fetch and convert an OCI documentation page to markdown."""
    if not is_oci_documentation_url(url):
        error_msg = f'Invalid URL: {url}. URL must be under a supported docs.oracle.com documentation path.'
        await ctx.error(error_msg)
        return error_msg

    return await read_documentation_impl(ctx, url, max_length, start_index, SESSION_UUID)


@mcp.tool()
async def read_sections(
    ctx: Context,
    url: str = Field(description='URL of the OCI documentation page to read'),
    section_titles: List[str] = Field(description='Section titles to extract'),
) -> str:
    """Fetch selected sections from an OCI documentation page."""
    if not is_oci_documentation_url(url):
        error_msg = f'Invalid URL: {url}. URL must be under a supported docs.oracle.com documentation path.'
        await ctx.error(error_msg)
        return error_msg

    return await read_sections_impl(ctx, url, section_titles, SESSION_UUID)


@mcp.tool()
async def search_documentation(
    ctx: Context,
    search_phrase: str = Field(description='Search phrase to use'),
    search_intent: str = Field(
        default='',
        description='Brief non-PII description of the user intent behind the OCI docs search.',
    ),
    limit: int = Field(default=10, description='Maximum number of results to return', ge=1, le=50),
) -> SearchResponse:
    """Search OCI documentation and return parsed documentation results."""
    logger.debug(f'Searching OCI documentation for: {search_phrase}')
    query_id = str(uuid.uuid4())
    search_url = build_oci_search_url(search_phrase, limit=limit, base_url=OCI_SEARCH_URL)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                search_url,
                follow_redirects=True,
                headers={
                    'User-Agent': DEFAULT_USER_AGENT,
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Referer': build_oci_search_referer(search_phrase),
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-MCP-Session-Id': SESSION_UUID,
                },
                timeout=30,
            )
        except httpx.HTTPError as e:
            error_msg = f'Error searching OCI docs: {str(e)}'
            await ctx.error(error_msg)
            return SearchResponse(
                search_results=[SearchResult(rank_order=1, url='', title=error_msg)],
                facets=None,
                query_id=query_id,
            )

        if response.status_code >= 400:
            results = await _search_public_search_page(client, search_phrase, limit)
            if results:
                search_response = SearchResponse(search_results=results, facets=None, query_id=query_id)
                add_search_result_cache_item(search_response)
                return search_response

            error_msg = (
                f'Error searching OCI docs - status code {response.status_code}; '
                'fallback search page returned no OCI documentation results'
            )
            await ctx.error(error_msg)
            return SearchResponse(
                search_results=[SearchResult(rank_order=1, url='', title=error_msg)],
                facets=None,
                query_id=query_id,
            )

        try:
            results = parse_oci_search_response(response.json(), limit)
        except ValueError:
            results = parse_oci_search_results(response.text, limit)

        results.extend(await _search_architecture_center(client, search_phrase, limit))
        results.extend(await _search_oracle_blogs(client, search_phrase, limit))
        results = _rank_combined_search_results(results, search_intent or search_phrase, limit)

        search_response = SearchResponse(search_results=results, facets=None, query_id=query_id)
        add_search_result_cache_item(search_response)
        return search_response


@mcp.tool()
async def answer_question(
    ctx: Context,
    question: str = Field(description='OCI documentation question to answer with citations'),
    search_phrase: Optional[str] = Field(
        default=None,
        description='Optional search phrase to use instead of the full question.',
    ),
    max_sources: int = Field(
        default=3,
        description='Maximum number of OCI documentation pages to read before answering.',
        ge=1,
        le=5,
    ),
) -> AnswerResponse:
    """Search, read relevant OCI docs, and return a synthesized answer with citations."""
    query = search_phrase or question
    search_response = await search_documentation(
        ctx,
        search_phrase=query,
        search_intent=question,
        limit=min(50, max(max_sources * 3, max_sources)),
    )
    ranked_results = rank_search_results(
        [
            result
            for result in search_response.search_results
            if result.url and _is_readable_evidence_url(result.url)
        ],
        classify_intent(question),
    )

    documents = []
    for result in ranked_results[:max_sources]:
        content = await read_documentation_impl(ctx, result.url, 12000, 0, SESSION_UUID)
        if _is_unreadable_documentation(content):
            continue
        documents.append(SourceDocument(result=result, content=content))

    return build_cited_answer(
        question=question,
        documents=documents,
        search_results=ranked_results,
        query_id=search_response.query_id,
    )


async def _search_public_search_page(
    client: httpx.AsyncClient,
    search_phrase: str,
    limit: int,
) -> list[SearchResult]:
    """Search the public Oracle search page when the JSON backend blocks a request."""
    fallback_url = build_oci_search_referer(search_phrase)
    try:
        response = await client.get(
            fallback_url,
            follow_redirects=True,
            headers={
                'User-Agent': DEFAULT_USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml',
                'X-MCP-Session-Id': SESSION_UUID,
            },
            timeout=30,
        )
    except httpx.HTTPError:
        return []

    if response.status_code >= 400:
        return []
    return parse_oci_search_results(response.text, limit)


async def _search_architecture_center(
    client: httpx.AsyncClient,
    search_phrase: str,
    limit: int,
) -> list[SearchResult]:
    """Search Architecture Center as a supplemental official Oracle source."""
    try:
        response = await client.get(
            build_architecture_center_search_url(search_phrase, limit=limit),
            follow_redirects=True,
            headers={
                'User-Agent': DEFAULT_USER_AGENT,
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Referer': ARCHITECTURE_CENTER_REFERER,
                'X-Requested-With': 'XMLHttpRequest',
                'X-MCP-Session-Id': SESSION_UUID,
            },
            timeout=30,
        )
    except httpx.HTTPError:
        return []

    if response.status_code >= 400:
        return []
    try:
        return parse_architecture_center_response(response.json(), limit)
    except ValueError:
        return []


async def _search_oracle_blogs(
    client: httpx.AsyncClient,
    search_phrase: str,
    limit: int,
) -> list[SearchResult]:
    """Search Oracle Blogs as supplemental recent-context evidence."""
    try:
        response = await client.get(
            build_oracle_blog_search_url(search_phrase, limit=limit),
            follow_redirects=True,
            headers={
                'User-Agent': DEFAULT_USER_AGENT,
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Referer': ORACLE_BLOG_REFERER,
                'X-Requested-With': 'XMLHttpRequest',
                'X-MCP-Session-Id': SESSION_UUID,
            },
            timeout=30,
        )
    except httpx.HTTPError:
        return []

    if response.status_code >= 400:
        return []
    try:
        return parse_oracle_blog_search_response(response.json(), limit)
    except ValueError:
        return []


def _rank_combined_search_results(
    results: list[SearchResult],
    search_intent: str,
    limit: int,
) -> list[SearchResult]:
    intent = classify_intent(search_intent)
    ranked = rank_search_results(dedupe_search_results(results), intent)
    return [
        result.model_copy(update={'rank_order': index})
        for index, result in enumerate(ranked[:limit], start=1)
    ]


def _is_readable_evidence_url(url: str) -> bool:
    if is_oci_documentation_url(url):
        return True
    parsed = urlparse(url)
    return parsed.netloc == 'blogs.oracle.com'


def _is_unreadable_documentation(content: str) -> bool:
    """Return whether a read result contains an error instead of documentation."""
    return content.startswith('Failed to fetch ') or '<e>No more content available.</e>' in content


def main():
    """Run the OCI Documentation MCP server."""
    mcp.run()
