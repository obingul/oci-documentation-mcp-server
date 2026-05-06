"""Data models for OCI documentation search and answer evidence."""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class SourceType(str, Enum):
    """Content source roles used when building answers."""

    OFFICIAL_DOCS = 'official_docs'
    ARCHITECTURE_CENTER = 'architecture_center'
    ORACLE_BLOG = 'oracle_blog'


class IntentType(str, Enum):
    """High-level user intent categories for source ranking."""

    REFERENCE = 'reference'
    HOW_TO = 'how_to'
    ARCHITECTURE = 'architecture'
    COMPARISON = 'comparison'
    LATEST = 'latest'
    EXAMPLE = 'example'


class SearchResult(BaseModel):
    """Search result from OCI documentation search."""

    rank_order: int
    url: str
    title: str
    context: Optional[str] = None
    sections: Optional[List[str]] = None
    source_type: SourceType = SourceType.OFFICIAL_DOCS
    content_type: Optional[str] = None
    published_at: Optional[str] = None
    service_tags: List[str] = Field(default_factory=list)
    product_tags: List[str] = Field(default_factory=list)
    technology_tags: List[str] = Field(default_factory=list)
    matched_sections: List[str] = Field(default_factory=list)
    highlights: List[str] = Field(default_factory=list)
    authority_score: float = 0.0
    freshness_score: float = 0.0
    query_relevance_score: float = 0.0
    recommended_use: Optional[str] = None


class SearchResponse(BaseModel):
    """Complete search response including results and optional facets."""

    search_results: List[SearchResult]
    facets: Optional[Dict[str, List[str]]] = None
    query_id: str


class SourceDocument(BaseModel):
    """Readable documentation content associated with a search result."""

    result: SearchResult
    content: str


class Citation(BaseModel):
    """Citation for a material claim in a synthesized answer."""

    citation_id: int
    url: str
    title: str
    source_type: SourceType = SourceType.OFFICIAL_DOCS
    excerpt: str


class AnswerResponse(BaseModel):
    """Synthesized answer with structured citations and consulted sources."""

    question: str
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    sources_consulted: List[SearchResult] = Field(default_factory=list)
    query_id: str
    confidence: str = 'medium'
    missing_information: List[str] = Field(default_factory=list)


class EvidenceCandidate(BaseModel):
    """A normalized result plus the claim it can support."""

    result: SearchResult
    intent: IntentType
    claim: str

    @property
    def citation_url(self) -> str:
        """Return the URL to cite when using this candidate."""
        return self.result.url

    @property
    def combined_score(self) -> float:
        """Combine simple source scores for deterministic ranking."""
        return round(
            self.result.authority_score
            + self.result.freshness_score
            + self.result.query_relevance_score,
            6,
        )


class EvidenceBundle(BaseModel):
    """Grouped evidence for client-side or server-side answer synthesis."""

    user_intent: IntentType
    answer_outline: List[str] = Field(default_factory=list)
    claims: List[str] = Field(default_factory=list)
    supporting_sources: List[EvidenceCandidate] = Field(default_factory=list)
    source_conflicts: List[str] = Field(default_factory=list)
    confidence: str = 'medium'
    missing_information: List[str] = Field(default_factory=list)
