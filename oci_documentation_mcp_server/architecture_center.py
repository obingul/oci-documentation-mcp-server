"""Oracle Architecture Center search helpers."""

from bs4 import BeautifulSoup
from oci_documentation_mcp_server.models import SearchResult, SourceType
from oci_documentation_mcp_server.util import normalize_whitespace
from typing import Any, Dict, List
from urllib.parse import urlencode, urlparse


ARCHITECTURE_CENTER_ASSETS_URL = (
    'https://docs.oracle.com/apps/ohcsearchclient/api/v1/search/assets'
)
DEFAULT_ARCHITECTURE_CENTER_CONTENT_TYPES = [
    'reference-architectures',
    'solution-playbook',
    'built-deployed',
]
ARCHITECTURE_CENTER_REFERER = 'https://docs.oracle.com/solutions/'


def build_architecture_center_search_url(
    search_phrase: str,
    limit: int,
    page: int = 1,
    lang: str = 'en',
    content_types: List[str] | None = None,
    services: List[str] | None = None,
    product: str = '',
    technologies: List[str] | None = None,
    sort: str = 'date-desc',
    base_url: str = ARCHITECTURE_CENTER_ASSETS_URL,
) -> str:
    """Build the Oracle Architecture Center assets search URL."""
    params = [
        ('pg', str(page)),
        ('size', str(limit)),
        ('lang', lang),
        ('cType', ','.join(content_types or DEFAULT_ARCHITECTURE_CENTER_CONTENT_TYPES)),
        ('services', ','.join(services or [])),
        ('product', product),
        ('technologies', ','.join(technologies or [])),
        ('q', normalize_whitespace(search_phrase)),
        ('sort', sort),
    ]
    return f'{base_url}?{urlencode(params)}'


def parse_architecture_center_response(data: Dict[str, Any], limit: int) -> List[SearchResult]:
    """Parse Architecture Center assets API results."""
    if limit <= 0:
        return []

    hits = data.get('hits', [])
    if not isinstance(hits, list):
        return []

    results: List[SearchResult] = []
    seen_urls = set()
    for hit in hits:
        if len(results) >= limit or not isinstance(hit, dict):
            break

        source = hit.get('_source', {})
        if not isinstance(source, dict):
            continue

        url = _first_string(source.get('url'), hit.get('_id'))
        title = _first_string(source.get('title'))
        if not url or not title or not _is_architecture_center_url(url) or url in seen_urls:
            continue

        seen_urls.add(url)
        results.append(
            SearchResult(
                rank_order=len(results) + 1,
                url=url,
                title=normalize_whitespace(title),
                context=_first_string(source.get('description')) or None,
                source_type=SourceType.ARCHITECTURE_CENTER,
                content_type=_normalize_content_type(source.get('content_type')),
                published_at=_first_string(source.get('publish_date')) or None,
                service_tags=_string_list(source.get('services')),
                product_tags=_string_list(source.get('products')) or _string_list(source.get('product')),
                technology_tags=_string_list(source.get('technologies')),
                highlights=_extract_highlights(hit.get('highlight')),
                authority_score=0.9,
                freshness_score=0.2,
                query_relevance_score=_normalize_score(hit.get('_score')),
                recommended_use='Use for architecture and solution design guidance.',
            )
        )

    return results


def _is_architecture_center_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc == 'docs.oracle.com' and parsed.path.startswith(
        ('/en/solutions/', '/solutions/')
    )


def _normalize_content_type(value: Any) -> str | None:
    """Return the useful Architecture Center content type from Oracle metadata."""
    values = _string_list(value)
    for item in values:
        if item in DEFAULT_ARCHITECTURE_CENTER_CONTENT_TYPES:
            return item
    return values[0] if values else None


def _extract_highlights(value: Any) -> List[str]:
    """Extract clean highlight snippets from an Oracle search hit."""
    if not isinstance(value, dict):
        return []

    snippets: List[str] = []
    for key in ('description', 'body', 'title'):
        for item in _string_list(value.get(key)):
            text = _html_to_text(item)
            if text and text not in snippets:
                snippets.append(text)
    return snippets


def _normalize_score(value: Any) -> float:
    """Map backend relevance scores to a small deterministic range."""
    if isinstance(value, (int, float)) and value > 0:
        return min(float(value) / 10.0, 1.0)
    return 0.0


def _string_list(value: Any) -> List[str]:
    """Normalize Oracle scalar/list metadata to a string list."""
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
