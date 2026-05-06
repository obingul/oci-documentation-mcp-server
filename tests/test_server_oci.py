"""Tests for the OCI Documentation MCP server."""

import pytest
from oci_documentation_mcp_server.models import AnswerResponse, SearchResponse, SearchResult
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
    mock_client.get.assert_called_once()
    call_kwargs = mock_client.get.call_args.kwargs
    assert call_kwargs['headers']['X-Requested-With'] == 'XMLHttpRequest'
    assert call_kwargs['headers']['Referer'] == 'https://docs.oracle.com/search/?q=compute+instance'


@pytest.mark.asyncio
async def test_search_documentation_falls_back_to_public_search_page_after_403():
    """Return parsed HTML search results when the JSON backend blocks the request."""
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
    with patch('oci_documentation_mcp_server.server_oci.httpx.AsyncClient') as client_cls:
        client_cls.return_value = mock_client

        response = await search_documentation(
            ctx,
            search_phrase='compute instance launch',
            search_intent='create compute instance',
            limit=2,
        )

    assert [result.title for result in response.search_results] == [
        'Creating an Instance',
        'Overview of Compute',
    ]
    assert ctx.error.await_count == 0
    assert mock_client.get.await_count == 2
    fallback_call = mock_client.get.await_args_list[1]
    assert fallback_call.args[0] == 'https://docs.oracle.com/search/?q=compute+instance+launch'
    assert fallback_call.kwargs['headers']['Accept'] == 'text/html,application/xhtml+xml'


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
