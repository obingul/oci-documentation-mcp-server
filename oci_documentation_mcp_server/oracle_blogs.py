"""Oracle Blogs search and RSS helpers."""

from bs4 import BeautifulSoup
from oci_documentation_mcp_server.models import SearchResult, SourceType
from oci_documentation_mcp_server.util import normalize_whitespace
from typing import Any, Dict, List
from urllib.parse import urlencode
from xml.etree import ElementTree


ORACLE_BLOG_SEARCH_URL = 'https://search-api.oracle.com/api/v1/search/blogs'
ORACLE_BLOG_REFERER = 'https://blogs.oracle.com/'


def build_oracle_blog_search_url(
    search_phrase: str,
    limit: int,
    offset: int = 0,
    base_url: str = ORACLE_BLOG_SEARCH_URL,
) -> str:
    """Build the confirmed Oracle Blogs search API URL."""
    params = [
        ('app', 'blogsui'),
        ('offset', str(offset)),
        ('q', normalize_whitespace(search_phrase)),
        ('size', str(limit)),
    ]
    return f'{base_url}?{urlencode(params)}'


def parse_oracle_blog_search_response(data: Dict[str, Any], limit: int) -> List[SearchResult]:
    """Parse Oracle Blogs search API results."""
    if limit <= 0:
        return []

    raw_results = data.get('results', [])
    if not isinstance(raw_results, list):
        return []

    results: List[SearchResult] = []
    seen_urls = set()
    for item in raw_results:
        if len(results) >= limit or not isinstance(item, dict):
            break

        url = _first_string(item.get('display_url'), item.get('document_id'))
        title = _clean_blog_title(_first_string(item.get('title')))
        if not url or not title or url in seen_urls:
            continue

        seen_urls.add(url)
        results.append(
            SearchResult(
                rank_order=len(results) + 1,
                url=url,
                title=title,
                context=_html_to_text(_first_string(item.get('description'))) or None,
                source_type=SourceType.ORACLE_BLOG,
                content_type='blog',
                published_at=_first_string(item.get('display_date')) or None,
                service_tags=_string_list(item.get('blog_name')),
                technology_tags=_string_list(item.get('keywords')),
                authority_score=0.45,
                freshness_score=0.8,
                query_relevance_score=_normalize_score(item.get('score')),
                recommended_use='Use for announcements, recent examples, and product context.',
            )
        )

    return results


def parse_oracle_blog_feed(xml: str, blog_name: str, limit: int) -> List[SearchResult]:
    """Parse Oracle Blogs RSS feed items."""
    if limit <= 0 or not xml:
        return []

    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return []

    results: List[SearchResult] = []
    seen_urls = set()
    for item in root.findall('./channel/item'):
        if len(results) >= limit:
            break

        url = _node_text(item, 'link')
        title = _node_text(item, 'title')
        if not url or not title or url in seen_urls:
            continue

        categories = [_clean_text(category.text or '') for category in item.findall('category')]
        seen_urls.add(url)
        results.append(
            SearchResult(
                rank_order=len(results) + 1,
                url=url,
                title=title,
                context=_html_to_text(_node_text(item, 'description')) or None,
                source_type=SourceType.ORACLE_BLOG,
                content_type='blog',
                published_at=_node_text(item, 'pubDate') or None,
                service_tags=[blog_name] if blog_name else [],
                technology_tags=[category for category in categories if category],
                authority_score=0.45,
                freshness_score=0.8,
                recommended_use='Use for announcements, recent examples, and product context.',
            )
        )

    return results


def _clean_blog_title(value: str) -> str:
    """Remove blog-name suffixes from Oracle search result titles."""
    title = normalize_whitespace(value)
    if ' | ' in title:
        return title.rsplit(' | ', 1)[0]
    return title


def _normalize_score(value: Any) -> float:
    """Map Oracle blog relevance scores to a small deterministic range."""
    if isinstance(value, (int, float)) and value > 0:
        return min(float(value) / 20.0, 1.0)
    return 0.0


def _node_text(item: ElementTree.Element, name: str) -> str:
    """Return stripped child text from an RSS item."""
    child = item.find(name)
    if child is None or child.text is None:
        return ''
    return _clean_text(child.text)


def _string_list(value: Any) -> List[str]:
    """Normalize scalar/list metadata to a string list."""
    if isinstance(value, str) and value:
        return [normalize_whitespace(value)]
    if isinstance(value, list):
        return [normalize_whitespace(item) for item in value if isinstance(item, str) and item]
    return []


def _first_string(*values: Any) -> str:
    """Return the first non-empty string from values."""
    for value in values:
        if isinstance(value, str) and value:
            return value
    return ''


def _html_to_text(value: str) -> str:
    """Convert a short HTML snippet to plain text."""
    return normalize_whitespace(BeautifulSoup(value, 'html.parser').get_text(' ', strip=True))


def _clean_text(value: str) -> str:
    """Normalize plain XML text."""
    return normalize_whitespace(value)
