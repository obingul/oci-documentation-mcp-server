"""Utilities for OCI documentation retrieval and search."""

import markdownify
from bs4 import BeautifulSoup, Tag
from oci_documentation_mcp_server.models import SearchResult, SourceType
from typing import Any, Dict, List
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse


OCI_DOCS_BASE_URL = 'https://docs.oracle.com'
OCI_DOCS_PATH_PREFIXES = (
    '/en-us/iaas/',
    '/en/learn/',
    '/en/paas/',
    '/en/solutions/',
    '/solutions/',
)
DEFAULT_OCI_SEARCH_URL = 'https://docs.oracle.com/apps/ohcsearchclient/api/v2/search/pages'
DEFAULT_OCI_SEARCH_PAGE_URL = 'https://docs.oracle.com/search/'


def normalize_whitespace(value: str) -> str:
    """Collapse repeated whitespace in user or HTML text."""
    return ' '.join(value.split())


def is_oci_documentation_url(url: str) -> bool:
    """Return whether a URL points at OCI documentation."""
    parsed = urlparse(url)
    return parsed.netloc == 'docs.oracle.com' and any(
        parsed.path.startswith(prefix) for prefix in OCI_DOCS_PATH_PREFIXES
    )


def build_oci_search_url(
    search_phrase: str,
    limit: int,
    page: int = 1,
    lang: str = 'en',
    base_url: str = DEFAULT_OCI_SEARCH_URL,
) -> str:
    """Build the Oracle docs backend search URL for an OCI documentation query."""
    query = normalize_whitespace(search_phrase)
    params = [
        ('q', query),
        ('pg', str(page)),
        ('size', str(limit)),
        ('lang', lang),
    ]

    parsed = urlparse(base_url)
    existing = parse_qsl(parsed.query, keep_blank_values=True)
    final_query = urlencode(existing + params)
    return urlunparse(parsed._replace(query=final_query))


def build_oci_search_referer(search_phrase: str) -> str:
    """Build the public Oracle search page referer expected by the backend."""
    query = urlencode({'q': normalize_whitespace(search_phrase)})
    return f'{DEFAULT_OCI_SEARCH_PAGE_URL}?{query}'


def extract_content_from_html(html: str) -> str:
    """Convert documentation HTML to markdown."""
    if not html:
        return '<e>Empty HTML content</e>'

    soup = BeautifulSoup(html, 'html.parser')
    for selector in (
        'script',
        'style',
        'nav',
        'footer',
        '.breadcrumb',
        '.feedback',
        '.legal',
        '.copyright',
    ):
        for element in soup.select(selector):
            element.decompose()

    main = soup.find('main') or soup.find('article') or soup.body or soup
    content = markdownify.markdownify(
        str(main),
        heading_style=markdownify.ATX,
        bullets='-',
        strip=['script', 'style'],
    )
    return content.strip() or '<e>Page failed to be simplified from HTML</e>'


def is_html_content(page_raw: str, content_type: str) -> bool:
    """Return whether response content should be treated as HTML."""
    return '<html' in page_raw[:100].lower() or 'text/html' in content_type or not content_type


def format_documentation_result(url: str, content: str, start_index: int, max_length: int) -> str:
    """Format a paginated OCI documentation read result."""
    if start_index >= len(content):
        return f'OCI Documentation from {url}:\n\n<e>No more content available.</e>'

    end_index = min(start_index + max_length, len(content))
    page = content[start_index:end_index]
    result = f'OCI Documentation from {url}:\n\n{page}'

    if end_index < len(content):
        result += (
            f'\n\n<e>Content truncated. Call read_documentation with start_index={end_index} '
            'to continue.</e>'
        )

    return result


def extract_sections_from_html(html: str, section_titles: List[str]) -> str:
    """Extract requested heading sections from OCI documentation HTML."""
    if not html or not section_titles:
        return 'No content or section titles provided'

    soup = BeautifulSoup(html, 'html.parser')
    requested = {normalize_whitespace(title).lower(): title.strip() for title in section_titles}
    matched_html = []
    found = set()
    headings = soup.find_all(['h2', 'h3'])

    for heading in headings:
        heading_text = normalize_whitespace(heading.get_text(' ', strip=True))
        key = heading_text.lower()
        if key not in requested:
            continue

        section_content = [heading]
        for sibling in heading.find_next_siblings():
            if isinstance(sibling, Tag) and sibling.name in ['h2', 'h3']:
                break
            section_content.append(sibling)
        matched_html.append(''.join(str(element) for element in section_content))
        found.add(requested[key])

    if not found:
        available = ', '.join(
            f'"{normalize_whitespace(heading.get_text(" ", strip=True))}"' for heading in headings
        )
        if available:
            raise ValueError(
                'No matching sections were found. Available sections: '
                f'{available}. Please retry with one or more of these sections.'
            )
        raise ValueError(
            'This document does not contain subsections. Please use read_documentation instead.'
        )

    result_html = ''.join(matched_html)
    if len(found) < len(section_titles):
        missing = [title.strip() for title in section_titles if title.strip() not in found]
        result_html += (
            '\n\n<blockquote><strong>Note</strong>: The following requested sections were not '
            f'found: {", ".join(missing)}</blockquote>'
        )

    return result_html


def parse_oci_search_results(html: str, limit: int) -> List[SearchResult]:
    """Parse OCI documentation results from Oracle search HTML."""
    if limit <= 0 or not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    results = []
    seen_urls = set()

    containers = soup.select(
        '.search-result, .result, .result-item, li[class*="result"], div[class*="result"], article'
    )
    if not containers:
        containers = [anchor.parent for anchor in soup.find_all('a', href=True) if anchor.parent]

    for container in containers:
        if len(results) >= limit:
            break

        anchor = _find_result_anchor(container)
        if not anchor:
            continue

        href = anchor.get('href')
        if not isinstance(href, str):
            continue

        url = urljoin(OCI_DOCS_BASE_URL, href)
        if not is_oci_documentation_url(url) or url in seen_urls:
            continue

        title = normalize_whitespace(anchor.get_text(' ', strip=True))
        if not title:
            continue

        context = _extract_result_context(container, title)
        seen_urls.add(url)
        results.append(
            SearchResult(
                rank_order=len(results) + 1,
                url=url,
                title=title,
                context=context or None,
                source_type=_source_type_for_url(url),
            )
        )

    return results


def parse_oci_search_response(data: Dict[str, Any], limit: int) -> List[SearchResult]:
    """Parse OCI documentation results from Oracle search backend JSON."""
    if limit <= 0:
        return []

    results = []
    seen_urls = set()
    hits = data.get('hits', [])
    if not isinstance(hits, list):
        return []

    for hit in hits:
        if len(results) >= limit or not isinstance(hit, dict):
            break

        source = hit.get('_source', {})
        if not isinstance(source, dict):
            continue

        url = source.get('url')
        title = source.get('title')
        if not isinstance(url, str) or not isinstance(title, str):
            continue

        if not is_oci_documentation_url(url) or url in seen_urls:
            continue

        context = _extract_json_result_context(hit)
        seen_urls.add(url)
        results.append(
            SearchResult(
                rank_order=len(results) + 1,
                url=url,
                title=normalize_whitespace(title),
                context=context or None,
                source_type=_source_type_for_url(url),
            )
        )

    return results


def _find_result_anchor(container: Tag) -> Tag | None:
    """Find the first OCI documentation link inside a search result container."""
    for anchor in container.find_all('a', href=True):
        if not isinstance(anchor, Tag):
            continue

        href = anchor.get('href')
        if not isinstance(href, str):
            continue

        url = urljoin(OCI_DOCS_BASE_URL, href)
        if is_oci_documentation_url(url):
            return anchor
    return None


def _source_type_for_url(url: str) -> SourceType:
    parsed = urlparse(url)
    if parsed.netloc != 'docs.oracle.com':
        return SourceType.OFFICIAL_DOCS
    if parsed.path.startswith('/en/learn/'):
        return SourceType.LEARN
    if parsed.path.startswith('/en/paas/'):
        return SourceType.PAAS_DOCS
    if parsed.path.startswith(('/en/solutions/', '/solutions/')):
        return SourceType.ARCHITECTURE_CENTER
    return SourceType.OFFICIAL_DOCS


def _extract_result_context(container: Tag, title: str) -> str:
    """Extract a human useful snippet from a search result container."""
    for selector in (
        '.result-snippet',
        '.search-result-snippet',
        '.snippet',
        '.description',
        'p',
        'dd',
    ):
        snippet = container.select_one(selector)
        if snippet:
            return normalize_whitespace(snippet.get_text(' ', strip=True))

    text = normalize_whitespace(container.get_text(' ', strip=True))
    if text.startswith(title):
        text = normalize_whitespace(text[len(title) :])
    return text


def _extract_json_result_context(hit: Dict[str, Any]) -> str:
    """Extract and clean a context snippet from an Oracle search JSON hit."""
    highlight = hit.get('highlight', {})
    if isinstance(highlight, dict):
        for key in ('description', 'body'):
            value = highlight.get(key)
            text = _first_text_value(value)
            if text:
                return _html_to_plain_text(text)

    source = hit.get('_source', {})
    if isinstance(source, dict):
        for key in ('description', 'snippet'):
            value = source.get(key)
            if isinstance(value, str) and value:
                return _html_to_plain_text(value)

    return ''


def _first_text_value(value: Any) -> str:
    """Return the first useful string from a search response text value."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item:
                return item
    return ''


def _html_to_plain_text(value: str) -> str:
    """Convert a short highlighted HTML snippet to plain text."""
    soup = BeautifulSoup(value, 'html.parser')
    return normalize_whitespace(soup.get_text(' ', strip=True))
