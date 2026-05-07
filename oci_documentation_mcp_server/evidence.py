"""Helpers for relating search results to answer evidence."""

import re
from oci_documentation_mcp_server.models import (
    AnswerResponse,
    Citation,
    EvidenceBundle,
    EvidenceCandidate,
    IntentType,
    SearchResult,
    SourceDocument,
    SourceType,
)
from typing import Iterable, List


MAX_ANSWER_CITATIONS = 5
STOP_WORDS = {
    'a',
    'an',
    'and',
    'are',
    'by',
    'do',
    'for',
    'from',
    'how',
    'i',
    'in',
    'is',
    'it',
    'of',
    'on',
    'or',
    'the',
    'to',
    'what',
    'when',
    'where',
    'with',
}
ACTION_TERMS = {'configure', 'create', 'deploy', 'launch', 'start', 'use'}


def classify_intent(query: str) -> IntentType:
    """Classify a user query into a source-routing intent."""
    value = query.lower()
    if any(term in value for term in ('architecture', 'design', 'pattern', 'solution')):
        return IntentType.ARCHITECTURE
    if any(term in value for term in ('latest', 'new', 'announcement', 'recent', 'released')):
        return IntentType.LATEST
    if any(term in value for term in ('compare', 'comparison', 'versus', ' vs ', 'migration')):
        return IntentType.COMPARISON
    if any(term in value for term in ('example', 'sample', 'demo')):
        return IntentType.EXAMPLE
    if any(term in value for term in ('how do i', 'how to', 'configure', 'create', 'deploy')):
        return IntentType.HOW_TO
    return IntentType.REFERENCE


def dedupe_search_results(results: Iterable[SearchResult]) -> List[SearchResult]:
    """Deduplicate results by URL and normalize rank order."""
    deduped = []
    seen = set()
    for result in results:
        key = result.url.rstrip('/')
        if key in seen:
            continue
        seen.add(key)
        deduped.append(result.model_copy(update={'rank_order': len(deduped) + 1}))
    return deduped


def rank_search_results(results: Iterable[SearchResult], intent: IntentType) -> List[SearchResult]:
    """Rank results using source role and result scores."""
    return sorted(
        results,
        key=lambda result: (
            _source_priority(result.source_type, intent),
            result.authority_score + result.freshness_score + result.query_relevance_score,
            -result.rank_order,
        ),
        reverse=True,
    )


def build_evidence_bundle(query: str, results: Iterable[SearchResult]) -> EvidenceBundle:
    """Build a normalized evidence bundle from search results."""
    intent = classify_intent(query)
    ranked_results = rank_search_results(dedupe_search_results(results), intent)
    candidates = [
        EvidenceCandidate(
            result=result,
            intent=intent,
            claim=f'{result.title} can support {intent.value.replace("_", " ")} evidence.',
        )
        for result in ranked_results
    ]

    return EvidenceBundle(
        user_intent=intent,
        answer_outline=[f'Use {intent.value.replace("_", " ")} evidence to answer the query.'],
        claims=[candidate.claim for candidate in candidates],
        supporting_sources=candidates,
        confidence='medium' if candidates else 'low',
        missing_information=[] if candidates else ['No supporting sources were provided.'],
    )


def build_cited_answer(
    question: str,
    documents: Iterable[SourceDocument],
    search_results: Iterable[SearchResult],
    query_id: str,
) -> AnswerResponse:
    """Build an extractive answer with citations from read documentation."""
    consulted = list(search_results)
    ranked_sentences = _rank_evidence_sentences(question, documents)
    if not ranked_sentences:
        return AnswerResponse(
            question=question,
            answer=(
                'I could not find enough readable OCI documentation content to answer this '
                'with citations.'
            ),
            citations=[],
            sources_consulted=consulted,
            query_id=query_id,
            confidence='low',
            missing_information=['No readable source content was available.'],
        )

    citations = []
    citation_by_url = {}
    answer_lines = []
    for sentence, document in ranked_sentences:
        citation_id = citation_by_url.get(document.result.url)
        if citation_id is None:
            if len(citations) >= MAX_ANSWER_CITATIONS:
                continue
            citation_id = len(citations) + 1
            citation_by_url[document.result.url] = citation_id
            citations.append(
                Citation(
                    citation_id=citation_id,
                    url=document.result.url,
                    title=document.result.title,
                    source_type=document.result.source_type,
                    excerpt=sentence,
                )
            )
        answer_lines.append(f'- {sentence} [{citation_id}]')
        if len(answer_lines) >= MAX_ANSWER_CITATIONS:
            break

    return AnswerResponse(
        question=question,
        answer='Based on the OCI documentation:\n' + '\n'.join(answer_lines),
        citations=citations,
        sources_consulted=consulted,
        query_id=query_id,
        confidence='medium',
        missing_information=[],
    )


def _source_priority(source_type: SourceType, intent: IntentType) -> float:
    """Return source priority for a specific user intent."""
    priorities = {
        IntentType.REFERENCE: {
            SourceType.PAAS_DOCS: 3.5,
            SourceType.OFFICIAL_DOCS: 3.0,
            SourceType.LEARN: 2.5,
            SourceType.ARCHITECTURE_CENTER: 2.0,
            SourceType.ORACLE_BLOG: 1.0,
        },
        IntentType.HOW_TO: {
            SourceType.LEARN: 3.5,
            SourceType.PAAS_DOCS: 3.0,
            SourceType.OFFICIAL_DOCS: 2.5,
            SourceType.ARCHITECTURE_CENTER: 2.0,
            SourceType.ORACLE_BLOG: 1.0,
        },
        IntentType.ARCHITECTURE: {
            SourceType.ARCHITECTURE_CENTER: 3.0,
            SourceType.PAAS_DOCS: 2.5,
            SourceType.OFFICIAL_DOCS: 2.0,
            SourceType.LEARN: 1.5,
            SourceType.ORACLE_BLOG: 1.0,
        },
        IntentType.COMPARISON: {
            SourceType.ARCHITECTURE_CENTER: 3.0,
            SourceType.PAAS_DOCS: 2.5,
            SourceType.OFFICIAL_DOCS: 2.5,
            SourceType.LEARN: 2.0,
            SourceType.ORACLE_BLOG: 1.0,
        },
        IntentType.LATEST: {
            SourceType.ORACLE_BLOG: 3.0,
            SourceType.PAAS_DOCS: 2.5,
            SourceType.OFFICIAL_DOCS: 2.0,
            SourceType.ARCHITECTURE_CENTER: 1.5,
            SourceType.LEARN: 1.0,
        },
        IntentType.EXAMPLE: {
            SourceType.LEARN: 3.5,
            SourceType.ARCHITECTURE_CENTER: 3.0,
            SourceType.ORACLE_BLOG: 2.5,
            SourceType.PAAS_DOCS: 2.0,
            SourceType.OFFICIAL_DOCS: 2.0,
        },
    }
    return priorities[intent].get(source_type, 0.0)


def _rank_evidence_sentences(
    question: str,
    documents: Iterable[SourceDocument],
) -> List[tuple[str, SourceDocument]]:
    """Return relevant documentation sentences ordered for answer synthesis."""
    terms = _query_terms(question)
    ranked = []
    seen = set()
    for document_index, document in enumerate(documents):
        for sentence_index, sentence in enumerate(_sentences_from_content(document.content)):
            key = sentence.lower()
            if key in seen:
                continue
            seen.add(key)
            score = _sentence_score(sentence, document.result, terms)
            if score <= 0:
                continue
            ranked.append((score, -document_index, -sentence_index, sentence, document))

    ranked.sort(reverse=True)
    return [(sentence, document) for _, _, _, sentence, document in ranked]


def _query_terms(question: str) -> List[str]:
    """Extract meaningful lowercase terms from a user question."""
    terms = []
    for term in re.findall(r'[a-z0-9]+', question.lower()):
        if len(term) < 3 or term in STOP_WORDS:
            continue
        terms.append(term)
    return terms


def _sentences_from_content(content: str) -> List[str]:
    """Extract candidate answer sentences from a markdown read result."""
    cleaned = re.sub(r'^OCI Documentation from [^\n]+:\s*', '', content.strip())
    cleaned = re.sub(r'<e>.*?</e>', ' ', cleaned, flags=re.DOTALL)
    sentences = []
    for line in cleaned.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        line = re.sub(r'^[*-]\s+', '', line)
        for sentence in re.split(r'(?<=[.!?])\s+', line):
            sentence = re.sub(r'\s+', ' ', sentence).strip()
            if len(sentence) >= 30:
                sentences.append(sentence)
    return sentences


def _sentence_score(sentence: str, result: SearchResult, terms: List[str]) -> int:
    """Score a sentence by query overlap, action terms, and source rank."""
    lower_sentence = sentence.lower()
    lower_title = result.title.lower()
    score = sum(2 for term in terms if term in lower_sentence)
    score += sum(1 for term in terms if term in lower_title)
    score += sum(2 for term in ACTION_TERMS if term in terms and term in lower_sentence)
    score += max(0, 3 - result.rank_order)
    return score
