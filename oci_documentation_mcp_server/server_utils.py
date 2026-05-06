"""Shared implementation helpers for OCI documentation MCP tools."""

import httpx
import os
from collections import deque
from importlib.metadata import version
from loguru import logger
from mcp.server.fastmcp import Context
from oci_documentation_mcp_server.models import SearchResponse
from oci_documentation_mcp_server.util import (
    extract_content_from_html,
    extract_sections_from_html,
    format_documentation_result,
    is_html_content,
)
from typing import Optional
from urllib.parse import quote


try:
    __version__ = version('oci-documentation-mcp-server')
except Exception:
    from . import __version__


BASE_USER_AGENT = os.getenv(
    'MCP_USER_AGENT',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
)
DEFAULT_USER_AGENT = (
    f'{BASE_USER_AGENT} ModelContextProtocol/{__version__} (OCI Documentation Server)'
)

SEARCH_RESULT_CACHE = deque(maxlen=3)


async def read_documentation_impl(
    ctx: Context,
    url_str: str,
    max_length: int,
    start_index: int,
    session_uuid: str,
) -> str:
    """Implementation of the read_documentation tool."""
    logger.debug(f'Fetching documentation from {url_str}')
    url_with_session = f'{url_str}?session={session_uuid}'

    query_id = get_query_id_from_cache(url_str)
    if query_id:
        url_with_session += f'&query_id={query_id}'

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url_with_session,
                follow_redirects=True,
                headers={
                    'User-Agent': DEFAULT_USER_AGENT,
                    'X-MCP-Session-Id': session_uuid,
                },
                timeout=30,
            )
        except httpx.HTTPError as e:
            error_msg = f'Failed to fetch {url_str}: {str(e)}'
            await ctx.error(error_msg)
            return error_msg

    if response.status_code >= 400:
        error_msg = f'Failed to fetch {url_str} - status code {response.status_code}'
        await ctx.error(error_msg)
        return error_msg

    page_raw = response.text
    content_type = response.headers.get('content-type', '')
    content = extract_content_from_html(page_raw) if is_html_content(page_raw, content_type) else page_raw
    return format_documentation_result(url_str, content, start_index, max_length)


async def read_sections_impl(
    ctx: Context,
    url_str: str,
    section_titles: list[str],
    session_uuid: str,
) -> str:
    """Implementation of the read_sections tool."""
    logger.debug(f'Fetching sections {section_titles} from {url_str}')
    sections_param = ','.join(quote(title.strip(), safe='') for title in section_titles)
    url_with_session = f'{url_str}?session={session_uuid}&sections={sections_param}'

    query_id = get_query_id_from_cache(url_str)
    if query_id:
        url_with_session += f'&query_id={query_id}'

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url_with_session,
                follow_redirects=True,
                headers={
                    'User-Agent': DEFAULT_USER_AGENT,
                    'X-MCP-Session-Id': session_uuid,
                },
                timeout=30,
            )
        except httpx.HTTPError as e:
            error_msg = f'Failed to fetch {url_str}: {str(e)}'
            await ctx.error(error_msg)
            return error_msg

    if response.status_code >= 400:
        error_msg = f'Failed to fetch {url_str} - status code {response.status_code}'
        await ctx.error(error_msg)
        return error_msg

    try:
        filtered_content = extract_sections_from_html(response.text, section_titles)
    except ValueError as e:
        error_msg = str(e)
        await ctx.error(error_msg)
        return error_msg

    return extract_content_from_html(filtered_content)


def add_search_result_cache_item(search_response: SearchResponse) -> None:
    """Add search results to the front of the query-id cache."""
    SEARCH_RESULT_CACHE.appendleft(search_response)


def get_query_id_from_cache(url: str) -> Optional[str]:
    """Return the query ID for a URL in the recent search-result cache."""
    for search_response in SEARCH_RESULT_CACHE:
        for search_result in search_response.search_results:
            if search_result.url == url:
                return quote(search_response.query_id)
    return None
