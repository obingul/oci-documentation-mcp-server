"""Tests for normalized search and evidence models."""

from oci_documentation_mcp_server.models import (
    EvidenceBundle,
    EvidenceCandidate,
    IntentType,
    SearchResult,
    SourceType,
)


def test_search_result_accepts_official_source_metadata():
    """SearchResult preserves optional source metadata for existing search results."""
    result = SearchResult(
        rank_order=1,
        url='https://docs.oracle.com/en-us/iaas/Content/Compute/home.htm',
        title='Compute',
        context='Compute lets you provision and manage instances.',
        source_type=SourceType.OFFICIAL_DOCS,
        content_type='documentation',
        service_tags=['Compute'],
        recommended_use='Use for product behavior and procedural details.',
    )

    assert result.source_type == SourceType.OFFICIAL_DOCS
    assert result.content_type == 'documentation'
    assert result.service_tags == ['Compute']
    assert result.product_tags == []
    assert result.technology_tags == []
    assert result.recommended_use == 'Use for product behavior and procedural details.'


def test_evidence_candidate_wraps_architecture_center_result():
    """EvidenceCandidate keeps source role, scores, and citation URL together."""
    result = SearchResult(
        rank_order=1,
        url='https://docs.oracle.com/en/solutions/oci-multicloud-genai-rag/index.html',
        title='Deploy multicloud generative AI retrieval augmented generation (RAG)',
        source_type=SourceType.ARCHITECTURE_CENTER,
        content_type='reference-architecture',
        technology_tags=['AI and Machine Learning'],
        authority_score=0.9,
        query_relevance_score=0.8,
    )

    candidate = EvidenceCandidate(
        result=result,
        intent=IntentType.ARCHITECTURE,
        claim='Use this architecture for multicloud RAG design guidance.',
    )

    assert candidate.result.source_type == SourceType.ARCHITECTURE_CENTER
    assert candidate.intent == IntentType.ARCHITECTURE
    assert candidate.citation_url == result.url
    assert candidate.combined_score == 1.7


def test_evidence_bundle_groups_candidates_for_answer_building():
    """EvidenceBundle groups cited candidates under the detected user intent."""
    blog_result = SearchResult(
        rank_order=1,
        url='https://blogs.oracle.com/cloud-infrastructure/example',
        title='Example OCI announcement',
        source_type=SourceType.ORACLE_BLOG,
        published_at='2026-04-16 00:00:00',
        recommended_use='Use for recent announcement context.',
    )
    candidate = EvidenceCandidate(
        result=blog_result,
        intent=IntentType.LATEST,
        claim='Use this for recent context.',
    )

    bundle = EvidenceBundle(
        user_intent=IntentType.LATEST,
        answer_outline=['Summarize the recent announcement.'],
        claims=['Recent context comes from Oracle Blogs.'],
        supporting_sources=[candidate],
        confidence='medium',
    )

    assert bundle.user_intent == IntentType.LATEST
    assert bundle.supporting_sources[0].citation_url == blog_result.url
    assert bundle.missing_information == []
