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
    }
    assert all(r.attribute == r.data["urn"] for r in executed)
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
        in {r.attribute for r in executed}
    )
    keys = [(r.resource_type, r.title, r.attribute) for r in executed]
    assert len(keys) == len(set(keys))


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
    assert len(executed) == 6
    assert {r.attribute for r in executed} == {"externalId", "name"}


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
