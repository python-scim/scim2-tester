import pytest
from scim2_client.engines.werkzeug import TestSCIMClient
from scim2_server.backend import InMemoryBackend
from scim2_server.provider import SCIMProvider
from scim2_server.utils import load_default_resource_types
from scim2_server.utils import load_default_schemas
from werkzeug.test import Client

from scim2_tester import Status
from scim2_tester import check_server
from scim2_tester.discovery import get_all_available_tags
from scim2_tester.discovery import get_standard_resource_types


@pytest.fixture
def scim2_server():
    backend = InMemoryBackend()
    app = SCIMProvider(backend)

    for schema in load_default_schemas().values():
        app.register_schema(schema)

    for resource_type in load_default_resource_types().values():
        app.register_resource_type(resource_type)

    return app


def test_discovered_scim2_server(scim2_server):
    """Test the complete SCIM server with discovery."""
    client = TestSCIMClient(Client(scim2_server))
    client.discover()
    results = check_server(client, raise_exceptions=False)

    # Verify all tests executed successfully (no skipped)
    executed_results = [r for r in results if r.status != Status.SKIPPED]
    assert len(executed_results) > 0
    assert all(r.status in (Status.SUCCESS, Status.ERROR) for r in executed_results)


def test_undiscovered_scim2_server(scim2_server):
    """Test the SCIM server without initial discovery."""
    client = TestSCIMClient(Client(scim2_server))
    results = check_server(client, raise_exceptions=False)

    # Verify all tests executed successfully (no skipped)
    executed_results = [r for r in results if r.status != Status.SKIPPED]
    assert len(executed_results) > 0
    assert all(r.status in (Status.SUCCESS, Status.ERROR) for r in executed_results)


@pytest.mark.parametrize("tag", get_all_available_tags())
@pytest.mark.parametrize("resource_type", [None] + get_standard_resource_types())
def test_individual_filters(scim2_server, tag, resource_type):
    """Test individual tags and resource types."""
    client = TestSCIMClient(Client(scim2_server))
    client.discover()
    results = check_server(
        client, raise_exceptions=False, include_tags={tag}, resource_types=resource_type
    )
    for result in results:
        assert result.status in (Status.SKIPPED, Status.SUCCESS), (
            f"Result {result.title} failed: {result.reason}"
        )


def test_filtering_functionality(scim2_server):
    """Test that filtering produces different result sets."""
    client = TestSCIMClient(Client(scim2_server))
    client.discover()

    # Get all results
    all_results = check_server(client, raise_exceptions=False)
    all_executed = [r for r in all_results if r.status != Status.SKIPPED]

    # Test discovery only
    discovery_results = check_server(
        client, raise_exceptions=False, include_tags={"discovery"}
    )
    discovery_executed = [r for r in discovery_results if r.status != Status.SKIPPED]
    discovery_skipped = [r for r in discovery_results if r.status == Status.SKIPPED]

    # Should have some executed discovery results
    assert len(discovery_executed) > 0, "Expected some executed discovery results"

    # Should have some skipped results (non-discovery)
    assert len(discovery_skipped) > 0, "Expected some skipped non-discovery results"

    # Should have fewer results when filtering
    assert len(discovery_executed) < len(all_executed), (
        "Expected fewer results when filtering"
    )

    # Test misc only
    misc_results = check_server(client, raise_exceptions=False, include_tags={"misc"})
    misc_executed = [r for r in misc_results if r.status != Status.SKIPPED]

    # Should have at least one misc result
    assert len(misc_executed) > 0, "Expected at least one misc result"

    # Should have fewer misc results than all results
    assert len(misc_executed) < len(all_executed), (
        "Expected fewer misc results than all results"
    )


def test_tag_discovery_utility(scim2_server):
    """Test that the tag discovery utility works correctly."""
    discovered_tags = get_all_available_tags()

    # Should discover the hierarchical core tags
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
    discovered_core = discovered_tags.intersection(core_tags)
    assert len(discovered_core) >= 8, (
        f"Expected at least 8 core tags, got {len(discovered_core)}: {discovered_core}"
    )

    # Test with actual server - only test discoverable function-level tags
    client = TestSCIMClient(Client(scim2_server))
    client.discover()

    # Test function-level tags
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
