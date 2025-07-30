"""Test the main checker functionality."""

import pytest
from httpx import Client
from scim2_client.engines.httpx import SyncSCIMClient
from scim2_client.engines.werkzeug import TestSCIMClient
from werkzeug.test import Client as WerkzeugClient

from scim2_tester.checker import check_server
from scim2_tester.utils import SCIMTesterError
from scim2_tester.utils import Status


def test_check_server_with_tag_filtering(httpserver):
    """Validates tag filtering includes specified tags and excludes others."""
    client = SyncSCIMClient(Client(base_url=httpserver.url_for("/")))

    results = check_server(client, include_tags={"discovery"})
    for result in results:
        assert any("discovery" in tag for tag in result.tags)

    results = check_server(client, exclude_tags={"crud"})
    for result in results:
        assert not any("crud" in tag for tag in result.tags)


def test_check_server_with_resource_type_filtering(scim2_server_app):
    """Validates resource type filtering excludes unwanted resource types."""
    client = TestSCIMClient(WerkzeugClient(scim2_server_app))

    all_results = check_server(client, include_tags={"discovery", "crud:read"})
    user_results = [
        r for r in all_results if getattr(r, "resource_type", None) == "User"
    ]
    group_results = [
        r for r in all_results if getattr(r, "resource_type", None) == "Group"
    ]
    assert user_results
    assert group_results

    filtered_results = check_server(
        client, resource_types=["User"], include_tags={"discovery", "crud:read"}
    )
    user_filtered = [
        r for r in filtered_results if getattr(r, "resource_type", None) == "User"
    ]
    group_filtered = [
        r for r in filtered_results if getattr(r, "resource_type", None) == "Group"
    ]
    assert user_filtered
    assert not group_filtered


def test_check_server_exception_handling(httpserver):
    """Ensures proper exception handling based on raise_exceptions parameter."""
    client = SyncSCIMClient(Client(base_url=httpserver.url_for("/")))

    results = check_server(client, raise_exceptions=False)
    assert isinstance(results, list)
    error_results = [r for r in results if r.status == Status.ERROR]
    assert len(error_results) > 0

    with pytest.raises((SCIMTesterError, Exception)):
        check_server(client, raise_exceptions=True)
