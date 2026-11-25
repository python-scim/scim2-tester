from collections import Counter

import pytest
from scim2_client.engines.wsgi import WSGISCIMClient

from scim2_tester import Status
from scim2_tester import check_server
from scim2_tester.discovery import get_all_available_tags
from scim2_tester.discovery import get_standard_resource_types

PATCH_TAGS = {"patch:add", "patch:replace", "patch:remove"}


@pytest.fixture
def scim_client(scim2_server_app):
    client = WSGISCIMClient(scim2_server_app)
    client.discover()
    return client


def test_discovered_scim2_server(scim_client):
    """Test the complete SCIM server with discovery."""
    results = check_server(scim_client, raise_exceptions=False)

    executed_results = [r for r in results if r.status != Status.SKIPPED]
    assert len(executed_results) > 0
    assert all(
        r.status not in (Status.ERROR, Status.CRITICAL) for r in executed_results
    )


def test_undiscovered_scim2_server(scim2_server_app):
    """Test the SCIM server without initial discovery."""
    client = WSGISCIMClient(scim2_server_app)
    results = check_server(client, raise_exceptions=False)

    executed_results = [r for r in results if r.status != Status.SKIPPED]
    assert len(executed_results) > 0
    assert all(
        r.status not in (Status.ERROR, Status.CRITICAL) for r in executed_results
    )


def test_unsupported_methods_on_discovery_endpoints(scim_client):
    """The server is checked to refuse the methods its discovery endpoints do not support."""
    results = check_server(scim_client, raise_exceptions=False)

    method_checks = {
        "service_provider_config_endpoint_methods",
        "resource_types_endpoint_methods",
        "schemas_endpoint_methods",
        "resource_type_by_id_methods",
        "schema_by_id_methods",
    }
    method_results = [r for r in results if r.title in method_checks]
    assert {r.title for r in method_results} == method_checks
    assert all(r.status == Status.SUCCESS for r in method_results)


def test_patch_results_identify_their_attribute(scim_client):
    """Each PATCH result tells its attribute, so a result can be followed from a run to another."""
    results = check_server(scim_client, include_tags=PATCH_TAGS)

    executed = [
        r for r in results if r.status != Status.SKIPPED and r.tags & PATCH_TAGS
    ]
    assert {r.title for r in executed} == {
        "check_add_attribute",
        "check_replace_attribute",
        "check_remove_attribute",
        "check_remove_required_attribute",
    }
    assert all(
        r.attribute == r.data["urn"]
        for r in executed
        if r.title != "check_remove_required_attribute"
    )
    assert all(r.attribute is not None for r in executed)
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
        in {r.attribute for r in executed}
    )
    keys = [(r.resource_type, r.title, r.attribute) for r in executed]
    assert len(keys) == len(set(keys))


def test_replacement_results_identify_their_attribute(scim_client):
    """Each PUT result has the path of its attribute, and scim2-server applies every replaced value."""
    results = check_server(scim_client, include_tags={"crud:update"})

    replaced = [r for r in results if r.title == "object_replacement"]
    assert all(r.status == Status.SUCCESS for r in replaced)
    assert all(r.attribute == r.data["urn"] for r in replaced)
    assert ("Group", "members") in {(r.resource_type, r.attribute) for r in replaced}


def test_attribute_filtering_results_identify_their_attribute(scim_client):
    """Each result of the attributes and excludedAttributes checks tells its attribute."""
    results = check_server(
        scim_client, include_tags={"crud:read:attributes"}, resource_types=["User"]
    )

    executed = [
        r
        for r in results
        if r.status != Status.SKIPPED and "crud:read:attributes" in r.tags
    ]
    keys = [(r.title, r.attribute) for r in executed]
    assert len(keys) == len(set(keys))
    assert {r.title for r in executed} == {
        "object_query_with_attributes",
        "object_query_with_excluded_attributes",
        "object_list_with_attributes",
        "object_list_with_excluded_attributes",
        "search_with_attributes",
        "search_with_excluded_attributes",
    }
    attributes = {r.attribute for r in executed}
    assert {"userName", "nickName", "password"} <= attributes
    assert None not in attributes


@pytest.mark.parametrize("tag", get_all_available_tags())
@pytest.mark.parametrize("resource_type", [None] + get_standard_resource_types())
def test_individual_filters(scim_client, tag, resource_type):
    """Test individual tags and resource types."""
    results = check_server(
        scim_client,
        raise_exceptions=True,
        include_tags={tag},
        resource_types=resource_type,
    )
    for result in results:
        assert result.status in (Status.SUCCESS, Status.SKIPPED), (
            f"Result {result.title} failed: {result.reason}"
        )


def test_filtering_functionality(scim2_server_app):
    """Test that filtering produces different result sets."""
    client = WSGISCIMClient(scim2_server_app)
    client.discover()

    all_results = check_server(client, raise_exceptions=False)
    all_executed = [r for r in all_results if r.status != Status.SKIPPED]

    discovery_results = check_server(
        client, raise_exceptions=False, include_tags={"discovery"}
    )
    discovery_executed = [r for r in discovery_results if r.status != Status.SKIPPED]
    discovery_skipped = [r for r in discovery_results if r.status == Status.SKIPPED]

    assert len(discovery_executed) > 0, "Expected some executed discovery results"

    assert len(discovery_skipped) > 0, "Expected some skipped non-discovery results"

    assert len(discovery_executed) < len(all_executed), (
        "Expected fewer results when filtering"
    )

    misc_results = check_server(client, raise_exceptions=False, include_tags={"misc"})
    misc_executed = [r for r in misc_results if r.status != Status.SKIPPED]

    assert len(misc_executed) > 0, "Expected at least one misc result"

    assert len(misc_executed) < len(all_executed), (
        "Expected fewer misc results than all results"
    )


def test_tag_discovery_utility(scim2_server_app):
    """Test that the tag discovery utility works correctly."""
    discovered_tags = get_all_available_tags()

    core_tags = {
        "discovery",
        "crud:create",
        "crud:read",
        "crud:update",
        "crud:delete",
        "misc",
        "service-provider-config",
        "resource-types",
        "schemas",
    }
    discovered_core = set(discovered_tags).intersection(core_tags)
    assert len(discovered_core) >= 8, (
        f"Expected at least 8 core tags, got {len(discovered_core)}: {discovered_core}"
    )

    client = WSGISCIMClient(scim2_server_app)
    client.discover()

    function_level_tags = {
        "discovery",
        "service-provider-config",
        "resource-types",
        "schemas",
        "crud:create",
        "misc",
    }
    for tag in function_level_tags.intersection(discovered_tags):
        results = check_server(client, raise_exceptions=False, include_tags={tag})
        executed = [r for r in results if r.status != Status.SKIPPED]
        assert len(executed) > 0, f"Tag '{tag}' produced no executed results"


def test_the_available_tags_hold_the_tags_above_the_check_tags():
    """The tags that select several groups of checks can be listed."""
    tags = get_all_available_tags()
    assert {"crud", "crud:read", "crud:read:attributes", "patch", "patch:add"} <= set(
        tags
    )
    assert "*" not in tags
    assert tags == sorted(tags)


def failing_server(app):
    """Answer 500 to every request, but the lists of the discovery endpoints."""
    discovery_lists = ("/ServiceProviderConfig", "/ResourceTypes", "/Schemas")

    def wrapped(environ, start_response):
        if environ["REQUEST_METHOD"] == "GET" and environ["PATH_INFO"].endswith(
            discovery_lists
        ):
            return app(environ, start_response)

        start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
        return [b"Internal Server Error"]

    return wrapped


def test_the_result_ids_are_unique_when_the_server_fails(scim2_server_app):
    """Each failed check has its own identifier."""
    client = WSGISCIMClient(failing_server(scim2_server_app))
    results = check_server(client)

    assert {r.status for r in results} >= {Status.SUCCESS, Status.ERROR}
    ids = Counter(r.id for r in results)
    assert [id for id, count in ids.items() if count > 1] == []
    assert "object_creation[User]" in ids
    assert "object_creation[Group]" in ids
    assert "query_resource_type_by_id[User]" in ids


def test_the_result_ids_are_unique_when_the_checks_are_skipped(scim_client):
    """Each check skipped by the tags has its own identifier."""
    results = check_server(scim_client, include_tags={"misc"})

    assert Status.SKIPPED in {r.status for r in results}
    ids = Counter(r.id for r in results)
    assert [id for id, count in ids.items() if count > 1] == []
    assert "object_creation[User]" in ids


def test_the_result_ids_are_unique(scim_client):
    """Each result of a run against a compliant server has its own identifier."""
    results = check_server(scim_client)

    ids = Counter(r.id for r in results)
    assert [id for id, count in ids.items() if count > 1] == []
