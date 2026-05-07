"""Tests for evidence ranking and bundling helpers."""

from oci_documentation_mcp_server.evidence import (
    build_cited_answer,
    build_evidence_bundle,
    classify_intent,
    dedupe_search_results,
    rank_search_results,
)
from oci_documentation_mcp_server.models import (
    IntentType,
    SearchResult,
    SourceDocument,
    SourceType,
)


def _result(rank: int, source_type: SourceType, url: str, title: str) -> SearchResult:
    return SearchResult(
        rank_order=rank,
        url=url,
        title=title,
        source_type=source_type,
        authority_score=0.5,
        freshness_score=0.2,
        query_relevance_score=0.5,
    )


def test_classify_intent_routes_architecture_and_latest_queries():
    """Classify user queries into source-routing intents."""
    assert classify_intent('show me a reference architecture for multicloud RAG') == (
        IntentType.ARCHITECTURE
    )
    assert classify_intent('what is the latest announcement about OCI compute') == IntentType.LATEST
    assert classify_intent('how do I configure a compute instance') == IntentType.HOW_TO
    assert classify_intent('compare OCI compute with AWS EC2') == IntentType.COMPARISON


def test_rank_search_results_prefers_source_role_for_intent():
    """Rank by source role for the detected intent, not only backend order."""
    official = _result(1, SourceType.OFFICIAL_DOCS, 'https://docs.oracle.com/doc', 'Official docs')
    learn = _result(4, SourceType.LEARN, 'https://docs.oracle.com/en/learn/example', 'Learn')
    paas = _result(5, SourceType.PAAS_DOCS, 'https://docs.oracle.com/en/paas/example', 'PaaS')
    architecture = _result(
        6,
        SourceType.ARCHITECTURE_CENTER,
        'https://docs.oracle.com/en/solutions/example/index.html',
        'Architecture',
    )
    blog = _result(7, SourceType.ORACLE_BLOG, 'https://blogs.oracle.com/example', 'Blog')
    sources = [blog, architecture, learn, paas, official]

    reference_ranked = rank_search_results(sources, IntentType.REFERENCE)
    how_to_ranked = rank_search_results(sources, IntentType.HOW_TO)
    architecture_ranked = rank_search_results(sources, IntentType.ARCHITECTURE)
    comparison_ranked = rank_search_results(sources, IntentType.COMPARISON)
    latest_ranked = rank_search_results(sources, IntentType.LATEST)
    example_ranked = rank_search_results(sources, IntentType.EXAMPLE)

    assert reference_ranked[0].source_type == SourceType.PAAS_DOCS
    assert how_to_ranked[0].source_type == SourceType.LEARN
    assert architecture_ranked[0].source_type == SourceType.ARCHITECTURE_CENTER
    assert comparison_ranked[0].source_type == SourceType.ARCHITECTURE_CENTER
    assert latest_ranked[0].source_type == SourceType.ORACLE_BLOG
    assert example_ranked[0].source_type == SourceType.LEARN


def test_dedupe_search_results_keeps_first_url():
    """Deduplicate merged search sources by URL while preserving order."""
    first = _result(1, SourceType.OFFICIAL_DOCS, 'https://docs.oracle.com/doc', 'First')
    duplicate = _result(2, SourceType.ARCHITECTURE_CENTER, 'https://docs.oracle.com/doc', 'Duplicate')
    second = _result(3, SourceType.ORACLE_BLOG, 'https://blogs.oracle.com/post', 'Second')

    results = dedupe_search_results([first, duplicate, second])

    assert [result.title for result in results] == ['First', 'Second']
    assert [result.rank_order for result in results] == [1, 2]


def test_build_evidence_bundle_creates_cited_candidates():
    """Build an evidence bundle from ranked search results."""
    architecture = _result(
        1,
        SourceType.ARCHITECTURE_CENTER,
        'https://docs.oracle.com/en/solutions/example/index.html',
        'Architecture',
    )

    bundle = build_evidence_bundle(
        query='design a multicloud RAG architecture',
        results=[architecture],
    )

    assert bundle.user_intent == IntentType.ARCHITECTURE
    assert bundle.supporting_sources[0].citation_url == architecture.url
    assert bundle.claims == ['Architecture can support architecture evidence.']
    assert bundle.confidence == 'medium'


def test_build_cited_answer_extracts_relevant_sentences_with_citations():
    """Build a concise cited answer from read documentation content."""
    result = _result(
        1,
        SourceType.OFFICIAL_DOCS,
        'https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm',
        'Creating an Instance',
    )
    document = SourceDocument(
        result=result,
        content=(
            'OCI Documentation from https://docs.oracle.com/en-us/iaas/example:\n\n'
            '# Creating an Instance\n'
            'Create a compute instance by choosing an image, shape, and networking options. '
            'Use the instance launch command and required parameters to create an instance. '
            'The LaunchInstance operation creates instances through the API.'
        ),
    )

    answer = build_cited_answer(
        question='How do I launch a compute instance?',
        documents=[document],
        search_results=[result],
        query_id='query-1',
    )

    assert 'Use the instance launch command' in answer.answer
    assert '[1]' in answer.answer
    assert answer.citations[0].citation_id == 1
    assert answer.citations[0].url == result.url
    assert answer.citations[0].excerpt.startswith('Use the instance launch command')
    assert answer.confidence == 'medium'


def test_build_cited_answer_reports_missing_evidence_without_documents():
    """Avoid fabricating an answer when no readable source content is available."""
    answer = build_cited_answer(
        question='How do I launch a compute instance?',
        documents=[],
        search_results=[],
        query_id='query-1',
    )

    assert 'could not find enough readable OCI documentation' in answer.answer
    assert answer.citations == []
    assert answer.confidence == 'low'
    assert answer.missing_information == ['No readable source content was available.']
