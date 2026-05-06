"""Tests for Oracle Blogs search and RSS helpers."""

import json
from oci_documentation_mcp_server.models import SourceType
from oci_documentation_mcp_server.oracle_blogs import (
    build_oracle_blog_search_url,
    parse_oracle_blog_feed,
    parse_oracle_blog_search_response,
)
from pathlib import Path


SEARCH_FIXTURE = Path(__file__).parent / 'resources' / 'oracle_blog_search_results.json'
FEED_FIXTURE = Path(__file__).parent / 'resources' / 'oracle_blog_feed.xml'


def test_build_oracle_blog_search_url_uses_confirmed_parameters():
    """Build the confirmed Oracle Blogs search API URL."""
    result = build_oracle_blog_search_url('  oci   compute ', limit=5, offset=10)

    assert result == (
        'https://search-api.oracle.com/api/v1/search/blogs'
        '?app=blogsui&offset=10&q=oci+compute&size=5'
    )


def test_parse_oracle_blog_search_response_normalizes_results():
    """Parse Oracle Blogs API results into source-labeled SearchResult values."""
    results = parse_oracle_blog_search_response(json.loads(SEARCH_FIXTURE.read_text()), limit=10)

    assert len(results) == 2
    assert results[0].rank_order == 1
    assert results[0].source_type == SourceType.ORACLE_BLOG
    assert results[0].content_type == 'blog'
    assert results[0].title == 'Introducing the Next Generation of OCI Compute Shapes'
    assert results[0].url == 'https://blogs.oracle.com/cloud-infrastructure/oci-acceleron-computeshapes'
    assert results[0].context == 'OCI announcing new Acceleron based compute shapes.'
    assert results[0].published_at == '2026-04-16 00:00:00'
    assert results[0].service_tags == ['cloud-infrastructure']
    assert results[0].technology_tags == ['OCI', 'Compute', 'Acceleron']
    assert results[0].freshness_score > results[0].authority_score


def test_parse_oracle_blog_feed_normalizes_items():
    """Parse RSS feed items into source-labeled SearchResult values."""
    results = parse_oracle_blog_feed(FEED_FIXTURE.read_text(), blog_name='cloud-infrastructure', limit=1)

    assert len(results) == 1
    assert results[0].rank_order == 1
    assert results[0].source_type == SourceType.ORACLE_BLOG
    assert results[0].title == 'Raising the bar for trustworthy AI at Oracle'
    assert results[0].url == (
        'https://blogs.oracle.com/cloud-infrastructure/raising-the-bar-for-trustworthy-ai-at-oracle'
    )
    assert results[0].published_at == 'Tue, 05 May 2026 17:00:00 +0000'
    assert results[0].context == (
        'Oracle announces ISO/IEC 42001 certification for OCI and related services.'
    )
    assert results[0].service_tags == ['cloud-infrastructure']
    assert results[0].technology_tags == [
        'Oracle Cloud Infrastructure',
        'AI governance',
        'responsible AI',
    ]
