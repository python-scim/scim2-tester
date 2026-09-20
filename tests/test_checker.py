"""Test the main checker functionality."""

import pytest
from scim2_client.engines.httpx2 import SyncSCIMClient
from scim2_client.engines.werkzeug import TestSCIMClient
from werkzeug.test import Client as WerkzeugClient

from scim2_tester.checker import check_server
from scim2_tester.utils import SCIMTesterError
from scim2_tester.utils import Status
from tests.utils import Client


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


def test_check_server_ignores_data_of_failed_discovery_checks(httpserver):
    """Ensures the debugging data of failed discovery checks is not registered on the client."""
    client = SyncSCIMClient(Client(base_url=httpserver.url_for("/")))

    results = check_server(client)

    assert client.service_provider_config is None
    assert client.resource_types is None
    assert client.resource_models == ()
    assert all(result.status == Status.ERROR for result in results)


def test_check_server_exception_handling(httpserver):
    """Ensures proper exception handling based on raise_exceptions parameter."""
    client = SyncSCIMClient(Client(base_url=httpserver.url_for("/")))

    results = check_server(client, raise_exceptions=False)
    assert isinstance(results, list)
    error_results = [r for r in results if r.status == Status.ERROR]
    assert len(error_results) > 0

    with pytest.raises((SCIMTesterError, Exception)):
        check_server(client, raise_exceptions=True)
