from typing import Any

from scim2_client.engines.httpx2 import SyncSCIMClient

from scim2_tester.checkers import random_url
from scim2_tester.checkers import resource_type_tests
from scim2_tester.checkers import service_provider_config_endpoint
from scim2_tester.checkers.resource_types import _resource_types_endpoint
from scim2_tester.checkers.schemas import _schemas_endpoint
from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckContext
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status


def _discovered_objects(results: list[CheckResult]) -> Any:
    """Extract the objects a discovery endpoint exposed.

    Discovery orchestrators run the check querying the whole collection first,
    so its result comes first. The data of the other statuses describes why the
    check failed and must not be mistaken for discovered objects.
    """
    return results[0].data if results[0].status == Status.SUCCESS else None


def check_server(
    client: SyncSCIMClient,
    raise_exceptions: bool = False,
    include_tags: set[str] | None = None,
    exclude_tags: set[str] | None = None,
    resource_types: list[str] | None = None,
) -> list[CheckResult]:
    """Perform a series of check to a SCIM server.

    It starts by retrieving the standard :class:`~scim2_models.ServiceProviderConfig`,
    :class:`~scim2_models.Schema` and :class:`~scim2_models.ResourceType` endpoints.
    Those configuration resources will be registered to the client if no other have been registered yet.

    Then for all available resources (whether they have been manually configured in the client,
    or dynamically discovered by the checker), it perform a series of creation, query, replacement and deletion.

    :param client: A SCIM client that will perform the requests.
    :param raise_exceptions: Whether exceptions should be raised or stored in a :class:`~scim2_tester.CheckResult` object.
    :param include_tags: Execute only checks with at least one of these tags.
    :param exclude_tags: Skip checks with any of these tags.
    :param resource_types: Filter by resource type names (e.g., ["User", "Group"]).

    Available tags:
        - **discovery**: Tests for configuration endpoints (ServiceProviderConfig, ResourceTypes, Schemas)
        - **service-provider-config**: Tests for ServiceProviderConfig endpoint
        - **resource-types**: Tests for ResourceTypes endpoint
        - **schemas**: Tests for Schemas endpoint
        - **crud**: All CRUD operation tests
        - **crud:create**: Resource creation tests
        - **crud:read**: Resource reading tests
        - **crud:update**: Resource update tests
        - **crud:delete**: Resource deletion tests
        - **misc**: Miscellaneous tests (e.g., random URL access)

    Example usage::

        # Run only discovery tests
        results = check_server(client, include_tags={"discovery"})

        # Run CRUD tests except delete operations
        results = check_server(
            client, include_tags={"crud"}, exclude_tags={"crud:delete"}
        )

        # Test only User resources
        results = check_server(client, resource_types=["User"])

        # Test only User creation and reading
        results = check_server(
            client, include_tags={"crud:create", "crud:read"}, resource_types=["User"]
        )
    """
    conf = CheckConfig(
        raise_exceptions=raise_exceptions,
        include_tags=include_tags,
        exclude_tags=exclude_tags,
        resource_types=resource_types,
    )
    context = CheckContext(client, conf)
    results = []

    results_spc = service_provider_config_endpoint(context)
    results.extend(results_spc)
    if not client.service_provider_config:
        client.service_provider_config = _discovered_objects(results_spc)

    results_resource_types = _resource_types_endpoint(context)
    results.extend(results_resource_types)
    if not client.resource_types:
        client.resource_types = _discovered_objects(results_resource_types)

    results_schemas = _schemas_endpoint(context)
    results.extend(results_schemas)
    schemas = _discovered_objects(results_schemas)
    if not client.resource_models and schemas:
        client.resource_models = client.build_resource_models(
            client.resource_types or [], schemas
        )

    if (
        not client.service_provider_config
        or not client.resource_types
        or not client.resource_models
    ):
        return results

    result_random = random_url(context)
    results.extend(result_random)

    for resource_type in client.resource_types or []:
        if conf.resource_types and resource_type.name not in conf.resource_types:
            continue

        resource_results = resource_type_tests(context, resource_type)
        for result in resource_results:
            result.resource_type = resource_type.name
        results.extend(resource_results)

    return results
