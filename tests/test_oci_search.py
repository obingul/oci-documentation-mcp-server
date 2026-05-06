"""Tests for OCI documentation search support."""

import json
from oci_documentation_mcp_server.util import (
    build_oci_search_url,
    parse_oci_search_response,
    parse_oci_search_results,
)
from pathlib import Path


HTML_FIXTURE = Path(__file__).parent / 'resources' / 'oci_search_compute_results.html'
JSON_FIXTURE = Path(__file__).parent / 'resources' / 'oci_search_compute_results.json'


def test_build_oci_search_url_uses_oracle_search_api_parameters():
    """Build an OCI docs backend search URL with normalized query parameters."""
    result = build_oci_search_url(
        '  compute   instance  ',
        limit=10,
        base_url='https://docs.oracle.com/apps/ohcsearchclient/api/v2/search/pages',
    )

    assert result == (
        'https://docs.oracle.com/apps/ohcsearchclient/api/v2/search/pages'
        '?q=compute+instance&pg=1&size=10&lang=en'
    )


def test_parse_oci_search_response_from_json_fixture():
    """Parse OCI documentation results from Oracle search JSON."""
    results = parse_oci_search_response(json.loads(JSON_FIXTURE.read_text()), limit=10)

    assert len(results) == 2
    assert results[0].rank_order == 1
    assert results[0].title == 'Compute Instances'
    assert results[0].url == (
        'https://docs.oracle.com/en-us/iaas/compute-cloud-at-customer/cmn/compute/compute-instances.htm'
    )
    assert results[0].context == (
        'You can provision and manage compute instances on Compute Cloud@Customer.'
    )
    assert results[1].rank_order == 2
    assert results[1].title == 'Compute Instance Agent'


def test_parse_oci_search_response_honors_limit():
    """Limit parsed OCI JSON documentation results."""
    results = parse_oci_search_response(json.loads(JSON_FIXTURE.read_text()), limit=1)

    assert len(results) == 1
    assert results[0].title == 'Compute Instances'


def test_parse_oci_search_results_from_html_fixture():
    """Parse OCI documentation results from Oracle search HTML fallback."""
    results = parse_oci_search_results(HTML_FIXTURE.read_text(), limit=10)

    assert len(results) == 2
    assert results[0].rank_order == 1
    assert results[0].title == 'Creating an Instance'
    assert results[0].url == (
        'https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm'
    )
    assert results[0].context is not None
    assert 'compute instance' in results[0].context
    assert results[1].rank_order == 2
    assert results[1].title == 'Overview of Compute'


def test_parse_oci_search_results_honors_limit():
    """Limit parsed OCI documentation results."""
    results = parse_oci_search_results(HTML_FIXTURE.read_text(), limit=1)

    assert len(results) == 1
    assert results[0].title == 'Creating an Instance'
