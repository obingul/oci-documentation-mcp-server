"""Tests for Oracle Architecture Center search helpers."""

import json
from oci_documentation_mcp_server.architecture_center import (
    build_architecture_center_search_url,
    parse_architecture_center_response,
)
from oci_documentation_mcp_server.models import SourceType
from pathlib import Path


FIXTURE = Path(__file__).parent / 'resources' / 'oracle_solutions_assets.json'


def test_build_architecture_center_search_url_uses_assets_parameters():
    """Build an Architecture Center assets API URL with filters."""
    result = build_architecture_center_search_url(
        '  multicloud   rag  ',
        limit=5,
        page=2,
        content_types=['reference-architectures', 'solution-playbook'],
        technologies=['AI and Machine Learning'],
        sort='relevance',
    )

    assert result == (
        'https://docs.oracle.com/apps/ohcsearchclient/api/v1/search/assets'
        '?pg=2&size=5&lang=en'
        '&cType=reference-architectures%2Csolution-playbook'
        '&services=&product=&technologies=AI+and+Machine+Learning'
        '&q=multicloud+rag&sort=relevance'
    )


def test_parse_architecture_center_response_normalizes_hits():
    """Parse Architecture Center hits into source-labeled SearchResult values."""
    results = parse_architecture_center_response(json.loads(FIXTURE.read_text()), limit=10)

    assert len(results) == 2
    assert results[0].rank_order == 1
    assert results[0].source_type == SourceType.ARCHITECTURE_CENTER
    assert results[0].content_type == 'reference-architectures'
    assert results[0].title == 'Deploy multicloud generative AI retrieval augmented generation (RAG)'
    assert results[0].url == 'https://docs.oracle.com/en/solutions/oci-multicloud-genai-rag/index.html'
    assert results[0].published_at == '2026-04-24T06:00'
    assert results[0].technology_tags == ['AI and Machine Learning', 'Data Warehouse']
    assert results[0].highlights == ['Deploy OCI Generative AI services across clouds.']
    assert results[0].recommended_use == 'Use for architecture and solution design guidance.'
    assert results[0].authority_score > results[0].freshness_score


def test_parse_architecture_center_response_honors_limit():
    """Limit parsed Architecture Center results."""
    results = parse_architecture_center_response(json.loads(FIXTURE.read_text()), limit=1)

    assert len(results) == 1
    assert results[0].title == 'Deploy multicloud generative AI retrieval augmented generation (RAG)'
