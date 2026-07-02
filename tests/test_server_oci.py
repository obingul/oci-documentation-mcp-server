"""Tests for the OCI Documentation MCP server."""

import httpx
import json
import pytest
from oci_documentation_mcp_server.models import (
    AnswerResponse,
    SearchResponse,
    SearchResult,
    SourceType,
)
from oci_documentation_mcp_server.server_oci import (
    answer_question,
    ask_oci_docs,
    compare_oci_services,
    how_to_oci,
    search_documentation,
)
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch


JSON_FIXTURE = Path(__file__).parent / 'resources' / 'oci_search_compute_results.json'
HTML_FIXTURE = Path(__file__).parent / 'resources' / 'oci_search_compute_results.html'
ARCHITECTURE_FIXTURE = Path(__file__).parent / 'resources' / 'oracle_solutions_assets.json'
BLOG_FIXTURE = Path(__file__).parent / 'resources' / 'oracle_blog_search_results.json'


class MockContext:
    """Minimal MCP context test double."""

    def __init__(self):
        """Create async context method mocks."""
        self.error = AsyncMock()
        self.info = AsyncMock()


@pytest.mark.asyncio
async def test_search_documentation_parses_html_results():
    """Return SearchResponse results from OCI search JSON."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = JSON_FIXTURE.read_text()
    mock_response.headers = {'content-type': 'application/json'}
    mock_response.json.return_value = __import__('json').loads(JSON_FIXTURE.read_text())

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client

    with patch('oci_documentation_mcp_server.server_oci.httpx.AsyncClient') as client_cls:
        client_cls.return_value = mock_client

        response = await search_documentation(
            MockContext(),
            search_phrase='compute instance',
            search_intent='create compute instance',
            limit=2,
        )

    assert isinstance(response, SearchResponse)
    assert response.query_id
    assert response.facets is None
    assert [result.title for result in response.search_results] == [
        'Compute Instances',
        'Compute Instance Agent',
    ]
    assert mock_client.get.await_count == 3
    docs_call = mock_client.get.await_args_list[0]
    call_kwargs = docs_call.kwargs
    assert call_kwargs['headers']['X-Requested-With'] == 'XMLHttpRequest'
    assert (
        call_kwargs['headers']['Referer'] == 'https://docs.oracle.com/search/?q=compute+instance'
    )


@pytest.mark.asyncio
async def test_search_documentation_merges_supplemental_sources_after_public_fallback():
    """Merge supplemental results after the JSON backend falls back to public HTML."""
    blocked_response = Mock()
    blocked_response.status_code = 403
    blocked_response.text = 'Forbidden'

    html_response = Mock()
    html_response.status_code = 200
    html_response.text = HTML_FIXTURE.read_text()
    html_response.json.side_effect = ValueError('not json')

    mock_client = AsyncMock()
    mock_client.get.side_effect = [blocked_response, html_response]
    mock_client.__aenter__.return_value = mock_client

    ctx = MockContext()
    architecture_result = SearchResult(
        rank_order=1,
        url='https://docs.oracle.com/solutions/example/index.html',
        title='Architecture Center Result',
        source_type=SourceType.ARCHITECTURE_CENTER,
    )
    blog_result = SearchResult(
        rank_order=1,
        url='https://blogs.oracle.com/cloud-infrastructure/post/example',
        title='Oracle Blog Result',
        source_type=SourceType.ORACLE_BLOG,
    )
    with (
        patch('oci_documentation_mcp_server.server_oci.httpx.AsyncClient') as client_cls,
        patch(
            'oci_documentation_mcp_server.server_oci._search_architecture_center',
            new=AsyncMock(return_value=[architecture_result]),
        ) as architecture_search,
        patch(
            'oci_documentation_mcp_server.server_oci._search_oracle_blogs',
            new=AsyncMock(return_value=[blog_result]),
        ) as blog_search,
    ):
        client_cls.return_value = mock_client

        response = await search_documentation(
            ctx,
            search_phrase='compute instance launch',
            search_intent='create compute instance',
            limit=10,
        )

    result_titles = {result.title for result in response.search_results}
    assert 'Creating an Instance' in result_titles
    assert 'Architecture Center Result' in result_titles
    assert 'Oracle Blog Result' in result_titles
    assert ctx.error.await_count == 0
    assert mock_client.get.await_count == 2
    architecture_search.assert_awaited_once_with(mock_client, 'compute instance launch', 10)
    blog_search.assert_awaited_once_with(mock_client, 'compute instance launch', 10)
    fallback_call = mock_client.get.await_args_list[1]
    assert fallback_call.args[0] == 'https://docs.oracle.com/search/?q=compute+instance+launch'
    assert fallback_call.kwargs['headers']['Accept'] == 'text/html,application/xhtml+xml'


@pytest.mark.asyncio
async def test_search_documentation_returns_architecture_result_when_official_paths_fail():
    """Return Architecture Center evidence without reporting a tool-level error."""
    blocked_response = Mock(status_code=403, text='Forbidden')
    fallback_response = Mock(status_code=503, text='Unavailable')
    mock_client = AsyncMock()
    mock_client.get.side_effect = [blocked_response, fallback_response]
    mock_client.__aenter__.return_value = mock_client
    architecture_result = SearchResult(
        rank_order=1,
        url='https://docs.oracle.com/solutions/example/index.html',
        title='Architecture Center Result',
        source_type=SourceType.ARCHITECTURE_CENTER,
    )
    ctx = MockContext()

    with (
        patch('oci_documentation_mcp_server.server_oci.httpx.AsyncClient') as client_cls,
        patch(
            'oci_documentation_mcp_server.server_oci._search_architecture_center',
            new=AsyncMock(return_value=[architecture_result]),
        ) as architecture_search,
        patch(
            'oci_documentation_mcp_server.server_oci._search_oracle_blogs',
            new=AsyncMock(return_value=[]),
        ) as blog_search,
    ):
        client_cls.return_value = mock_client
        response = await search_documentation(
            ctx, search_phrase='compute', search_intent='compute', limit=5
        )

    assert [result.title for result in response.search_results] == ['Architecture Center Result']
    assert ctx.error.await_count == 0
    architecture_search.assert_awaited_once_with(mock_client, 'compute', 5)
    blog_search.assert_awaited_once_with(mock_client, 'compute', 5)


@pytest.mark.asyncio
async def test_search_documentation_returns_blog_result_after_official_transport_error():
    """Return Oracle Blog evidence after JSON transport and public HTML failures."""
    request = httpx.Request('GET', 'https://docs.oracle.com/search/api/v2/search/pages')
    fallback_response = Mock(status_code=503, text='Unavailable')
    mock_client = AsyncMock()
    mock_client.get.side_effect = [
        httpx.ConnectError('blocked', request=request),
        fallback_response,
    ]
    mock_client.__aenter__.return_value = mock_client
    blog_result = SearchResult(
        rank_order=1,
        url='https://blogs.oracle.com/cloud-infrastructure/post/example',
        title='Oracle Blog Result',
        source_type=SourceType.ORACLE_BLOG,
    )
    ctx = MockContext()

    with (
        patch('oci_documentation_mcp_server.server_oci.httpx.AsyncClient') as client_cls,
        patch(
            'oci_documentation_mcp_server.server_oci._search_architecture_center',
            new=AsyncMock(return_value=[]),
        ) as architecture_search,
        patch(
            'oci_documentation_mcp_server.server_oci._search_oracle_blogs',
            new=AsyncMock(return_value=[blog_result]),
        ) as blog_search,
    ):
        client_cls.return_value = mock_client
        response = await search_documentation(
            ctx, search_phrase='compute', search_intent='compute', limit=5
        )

    assert [result.title for result in response.search_results] == ['Oracle Blog Result']
    assert ctx.error.await_count == 0
    architecture_search.assert_awaited_once_with(mock_client, 'compute', 5)
    blog_search.assert_awaited_once_with(mock_client, 'compute', 5)


@pytest.mark.asyncio
async def test_search_documentation_reports_error_only_when_every_source_is_empty():
    """Return one synthetic error only when all configured sources yield no results."""
    empty_json_response = Mock(status_code=200, text='{}')
    empty_json_response.json.return_value = {}
    empty_html_response = Mock(status_code=200, text='<html></html>')
    mock_client = AsyncMock()
    mock_client.get.side_effect = [empty_json_response, empty_html_response]
    mock_client.__aenter__.return_value = mock_client
    ctx = MockContext()

    with (
        patch('oci_documentation_mcp_server.server_oci.httpx.AsyncClient') as client_cls,
        patch(
            'oci_documentation_mcp_server.server_oci._search_architecture_center',
            new=AsyncMock(return_value=[]),
        ) as architecture_search,
        patch(
            'oci_documentation_mcp_server.server_oci._search_oracle_blogs',
            new=AsyncMock(return_value=[]),
        ) as blog_search,
    ):
        client_cls.return_value = mock_client
        response = await search_documentation(
            ctx, search_phrase='compute', search_intent='compute', limit=5
        )

    assert len(response.search_results) == 1
    assert response.search_results[0].url == ''
    assert 'all configured search sources returned no results' in response.search_results[0].title
    assert ctx.error.await_count == 1
    architecture_search.assert_awaited_once_with(mock_client, 'compute', 5)
    blog_search.assert_awaited_once_with(mock_client, 'compute', 5)


@pytest.mark.asyncio
async def test_search_documentation_keeps_client_open_for_supplemental_sources():
    """Keep one live HTTP client through all federated search requests."""
    real_async_client = httpx.AsyncClient
    requested_urls = []
    docs_payload = json.loads(JSON_FIXTURE.read_text())
    architecture_payload = json.loads(ARCHITECTURE_FIXTURE.read_text())
    blog_payload = json.loads(BLOG_FIXTURE.read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if '/api/v2/search/pages' in str(request.url):
            return httpx.Response(200, json=docs_payload)
        if '/api/v1/search/assets' in str(request.url):
            return httpx.Response(200, json=architecture_payload)
        if 'search-api.oracle.com/api/v1/search/blogs' in str(request.url):
            return httpx.Response(200, json=blog_payload)
        return httpx.Response(404, text=str(request.url))

    def client_factory() -> httpx.AsyncClient:
        return real_async_client(transport=httpx.MockTransport(handler))

    with patch(
        'oci_documentation_mcp_server.server_oci.httpx.AsyncClient', side_effect=client_factory
    ):
        response = await search_documentation(
            MockContext(),
            search_phrase='compute instance',
            search_intent='create compute instance',
            limit=3,
        )

    assert response.search_results
    assert any('/api/v2/search/pages' in url for url in requested_urls)
    assert any('/api/v1/search/assets' in url for url in requested_urls)
    assert any('search-api.oracle.com/api/v1/search/blogs' in url for url in requested_urls)


@pytest.mark.asyncio
async def test_search_documentation_combines_source_specific_results():
    """Return one intent-ranked response across docs, Learn, PaaS, Architecture Center, and Blogs."""
    docs_response = Mock()
    docs_response.status_code = 200
    docs_response.text = ''
    docs_response.json.return_value = {
        'hits': [
            {
                '_source': {
                    'url': 'https://docs.oracle.com/en/learn/oci-foundations/index.html',
                    'title': 'Learn OCI Foundations',
                }
            },
            {
                '_source': {
                    'url': 'https://docs.oracle.com/en/paas/application-integration/index.html',
                    'title': 'Oracle Integration',
                }
            },
        ]
    }

    architecture_response = Mock()
    architecture_response.status_code = 200
    architecture_response.json.return_value = json.loads(ARCHITECTURE_FIXTURE.read_text())

    blog_response = Mock()
    blog_response.status_code = 200
    blog_response.json.return_value = json.loads(BLOG_FIXTURE.read_text())

    mock_client = AsyncMock()
    mock_client.get.side_effect = [docs_response, architecture_response, blog_response]
    mock_client.__aenter__.return_value = mock_client

    with patch('oci_documentation_mcp_server.server_oci.httpx.AsyncClient') as client_cls:
        client_cls.return_value = mock_client

        response = await search_documentation(
            MockContext(),
            search_phrase='latest oci integration examples',
            search_intent='latest oci integration examples',
            limit=6,
        )

    source_types = [result.source_type for result in response.search_results]
    assert source_types[0] == SourceType.ORACLE_BLOG
    assert SourceType.LEARN in source_types
    assert SourceType.PAAS_DOCS in source_types
    assert SourceType.ARCHITECTURE_CENTER in source_types
    assert mock_client.get.await_count == 3


@pytest.mark.asyncio
async def test_answer_question_searches_reads_and_returns_cited_answer():
    """Answer questions by reading relevant OCI docs and citing sources."""
    search_result = SearchResult(
        rank_order=1,
        url='https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm',
        title='Creating an Instance',
        context='Create a compute instance in Oracle Cloud Infrastructure.',
    )
    search_response = SearchResponse(
        search_results=[search_result],
        facets=None,
        query_id='query-1',
    )

    with (
        patch(
            'oci_documentation_mcp_server.server_oci.search_documentation',
            new=AsyncMock(return_value=search_response),
        ) as search_mock,
        patch(
            'oci_documentation_mcp_server.server_oci.read_documentation_impl',
            new=AsyncMock(
                return_value=(
                    'OCI Documentation from https://docs.oracle.com/en-us/iaas/example:\n\n'
                    'Use the instance launch command and required parameters to create an '
                    'instance. The LaunchInstance operation creates instances through the API.'
                )
            ),
        ) as read_mock,
    ):
        response = await answer_question(
            MockContext(),
            question='How do I launch a compute instance?',
            max_sources=1,
        )

    assert isinstance(response, AnswerResponse)
    assert 'Use the instance launch command' in response.answer
    assert '[1]' in response.answer
    assert response.citations[0].url == search_result.url
    assert response.sources_consulted == [search_result]
    search_mock.assert_awaited_once()
    read_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_answer_question_reads_blog_results_for_latest_context():
    """Use Oracle Blogs as readable evidence when answering latest/news questions."""
    blog_result = SearchResult(
        rank_order=1,
        url='https://blogs.oracle.com/cloud-infrastructure/oci-compute-announcement',
        title='OCI Compute Announcement',
        context='New OCI compute capabilities were announced.',
        source_type=SourceType.ORACLE_BLOG,
    )
    search_response = SearchResponse(
        search_results=[blog_result],
        facets=None,
        query_id='query-1',
    )

    with (
        patch(
            'oci_documentation_mcp_server.server_oci.search_documentation',
            new=AsyncMock(return_value=search_response),
        ),
        patch(
            'oci_documentation_mcp_server.server_oci.read_documentation_impl',
            new=AsyncMock(
                return_value=(
                    'OCI Documentation from https://blogs.oracle.com/cloud-infrastructure/'
                    'oci-compute-announcement:\n\n'
                    'Oracle announced new OCI compute capabilities for recent workloads.'
                )
            ),
        ) as read_mock,
    ):
        response = await answer_question(
            MockContext(),
            question='What is the latest OCI compute announcement?',
            max_sources=1,
        )

    assert response.citations[0].source_type == SourceType.ORACLE_BLOG
    assert response.citations[0].url == blog_result.url
    read_mock.assert_awaited_once()


def test_prompt_templates_guide_clients_to_answer_question_tool():
    """Expose discoverable prompt templates for common MCP calling paths."""
    ask_prompt = ask_oci_docs('How do I launch a compute instance?')
    how_to_prompt = how_to_oci('launch a compute instance')
    compare_prompt = compare_oci_services('Compare compute instance launch options')

    assert 'answer_question' in ask_prompt
    assert 'How do I launch a compute instance?' in ask_prompt
    assert 'answer_question' in how_to_prompt
    assert 'launch a compute instance' in how_to_prompt
    assert 'read relevant OCI documentation' in compare_prompt
