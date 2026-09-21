from typing import Any

from scim2_client import BaseSyncSCIMClient
from scim2_models import ScimProvider
from scim2_models import ScimProviderError

from scim2_tester.checkers import random_url
from scim2_tester.checkers import resource_type_tests
from scim2_tester.checkers import service_provider_config_endpoint
from scim2_tester.checkers.resource_types import _resource_types_endpoint
from scim2_tester.checkers.schemas import _schemas_endpoint
from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckContext
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status
from scim2_tester.utils import check_result


def _discovered_objects(results: list[CheckResult]) -> Any:
    """Extract the objects a discovery endpoint exposed.

    Discovery orchestrators run the check querying the whole collection first,
    so its result comes first. The data of the other statuses describes why the
    check failed and must not be mistaken for discovered objects.
    """
    return results[0].data if results[0].status == Status.SUCCESS else None


def _describe_service(
    context: CheckContext,
    results_spc: list[CheckResult],
    results_resource_types: list[CheckResult],
    results_schemas: list[CheckResult],
) -> tuple[ScimProvider | None, list[CheckResult]]:
    """Compose the description of the server from what its discovery endpoints published.

    What the client already describes wins over what the server publishes, as
    :meth:`~scim2_client.BaseSyncSCIMClient.discover` does. The description is
    registered on the client so the remaining checks are run against it.
    """
    provider = context.client.provider
    config = provider.config or _discovered_objects(results_spc)

    if provider.models:
        described = ScimProvider(
            provider.models, provider.resource_types, config, provider.policy
        )
        context.client.provider = described
        return described, []

    resource_types = _discovered_objects(results_resource_types)
    schemas = _discovered_objects(results_schemas)
    if not resource_types or not schemas:
        return None, []

    try:
        described = ScimProvider.from_discovery(
            schemas, resource_types, config, provider.policy
        )
    except ScimProviderError as exc:
        return None, [
            check_result(
                context,
                status=Status.ERROR,
                title="service_description",
                description="Compose the resource models the server serves from "
                "the schemas and the resource types it publishes.",
                reason=str(exc),
                tags={"discovery"},
            )
        ]

    context.client.provider = described
    return described, []


def check_server(
    client: BaseSyncSCIMClient,
    raise_exceptions: bool = False,
    include_tags: set[str] | None = None,
    exclude_tags: set[str] | None = None,
    resource_types: list[str] | None = None,
) -> list[CheckResult]:
    """Perform a series of check to a SCIM server.

    It starts by retrieving the standard :class:`~scim2_models.ServiceProviderConfig`,
    :class:`~scim2_models.Schema` and :class:`~scim2_models.ResourceType` endpoints.
    What they publish describes the server as a :class:`~scim2_models.ScimProvider`
    registered on the client, leaving untouched whatever the client already described.

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

    results_resource_types = _resource_types_endpoint(context)
    results.extend(results_resource_types)

    results_schemas = _schemas_endpoint(context)
    results.extend(results_schemas)

    provider, results_description = _describe_service(
        context, results_spc, results_resource_types, results_schemas
    )
    results.extend(results_description)

    if provider is None or not provider.config:
        return results

    result_random = random_url(context)
    results.extend(result_random)

    for resource_type in provider.resource_types:
        if conf.resource_types and resource_type.name not in conf.resource_types:
            continue

        resource_results = resource_type_tests(context, resource_type)
        for result in resource_results:
            result.resource_type = resource_type.name
        results.extend(resource_results)

    return results
