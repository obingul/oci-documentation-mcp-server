"""Tests for the OCI documentation command-line wrapper."""

from oci_documentation_mcp_server.cli import main
from oci_documentation_mcp_server.models import (
    AnswerResponse,
    Citation,
    SearchResponse,
    SearchResult,
)
from unittest.mock import AsyncMock, patch


def test_cli_answer_prints_answer_and_citations(capsys):
    """Render an answer response as readable terminal output."""
    response = AnswerResponse(
        question='How do I launch a compute instance?',
        answer='Based on the OCI documentation:\n- Use the instance launch command. [1]',
        citations=[
            Citation(
                citation_id=1,
                url='https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm',
                title='Creating an Instance',
                excerpt='Use the instance launch command.',
            )
        ],
        sources_consulted=[],
        query_id='query-1',
    )

    with patch('oci_documentation_mcp_server.cli.answer_question', new=AsyncMock(return_value=response)):
        exit_code = main(['answer', 'How do I launch a compute instance?'])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert 'Use the instance launch command. [1]' in output
    assert '[1] Creating an Instance' in output
    assert 'https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm' in output


def test_cli_search_prints_ranked_results(capsys):
    """Render search results for quick local use."""
    response = SearchResponse(
        search_results=[
            SearchResult(
                rank_order=1,
                url='https://docs.oracle.com/en-us/iaas/Content/Compute/home.htm',
                title='Compute',
                context='Use Compute to create instances.',
            )
        ],
        facets=None,
        query_id='query-1',
    )

    with patch(
        'oci_documentation_mcp_server.cli.search_documentation',
        new=AsyncMock(return_value=response),
    ):
        exit_code = main(['search', 'compute instance'])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert '1. Compute' in output
    assert 'Use Compute to create instances.' in output
