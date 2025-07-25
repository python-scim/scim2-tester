import argparse
import uuid

from scim2_client import SCIMClient
from scim2_models import Error

from scim2_tester.resource import check_resource_type
from scim2_tester.resource_types import check_resource_types_endpoint
from scim2_tester.schemas import check_schemas_endpoint
from scim2_tester.service_provider_config import check_service_provider_config_endpoint
from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status
from scim2_tester.utils import checker


@checker("misc")
def check_random_url(conf: CheckConfig) -> CheckResult:
    """Check that a request to a random URL returns a 404 Error object."""
    probably_invalid_url = f"/{str(uuid.uuid4())}"
    response = conf.client.query(url=probably_invalid_url, raise_scim_errors=False)

    if not isinstance(response, Error):
        return CheckResult(
            conf,
            status=Status.ERROR,
            reason=f"{probably_invalid_url} did not return an Error object",
            data=response,
        )

    if response.status != 404:
        return CheckResult(
            conf,
            status=Status.ERROR,
            reason=f"{probably_invalid_url} did return an object, but the status code is {response.status}",
            data=response,
        )

    return CheckResult(
        conf,
        status=Status.SUCCESS,
        reason=f"{probably_invalid_url} correctly returned a 404 error",
        data=response,
    )


def check_server(
    client: SCIMClient,
    raise_exceptions=False,
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
        client=client,
        raise_exceptions=raise_exceptions,
        include_tags=include_tags,
        exclude_tags=exclude_tags,
        resource_types=resource_types,
    )
    results = []

    # Get the initial basic objects
    result_spc = check_service_provider_config_endpoint(conf)
    results.append(result_spc)
    if result_spc.status != Status.SKIPPED and not conf.client.service_provider_config:
        conf.client.service_provider_config = result_spc.data

    results_resource_types = check_resource_types_endpoint(conf)
    results.extend(results_resource_types)
    if not conf.client.resource_types:
        # Find first non-skipped result with data
        for rt_result in results_resource_types:
            if rt_result.status != Status.SKIPPED and rt_result.data:
                conf.client.resource_types = rt_result.data
                break

    results_schemas = check_schemas_endpoint(conf)
    results.extend(results_schemas)
    if not conf.client.resource_models:
        # Find first non-skipped result with data
        for schema_result in results_schemas:
            if schema_result.status != Status.SKIPPED and schema_result.data:
                conf.client.resource_models = conf.client.build_resource_models(
                    conf.client.resource_types or [], schema_result.data or []
                )
                break

    if (
        not conf.client.service_provider_config
        or not conf.client.resource_types
        or not conf.client.resource_models
    ):
        return results

    # Miscelleaneous checks
    result_random = check_random_url(conf)
    results.append(result_random)

    # Resource checks
    for resource_type in conf.client.resource_types or []:
        # Filter by resource type if specified
        if conf.resource_types and resource_type.name not in conf.resource_types:
            continue

        resource_results = check_resource_type(conf, resource_type)
        # Add resource type to each result for better tracking
        for result in resource_results:
            result.resource_type = resource_type.name
        results.extend(resource_results)

    return results


if __name__ == "__main__":
    from httpx import Client
    from scim2_client.engines.httpx import SyncSCIMClient

    parser = argparse.ArgumentParser(description="SCIM server compliance checker.")
    parser.add_argument("host")
    parser.add_argument("--token", required=False)
    parser.add_argument("--verbose", required=False, action="store_true")
    parser.add_argument(
        "--include-tags",
        nargs="+",
        help="Run only checks with these tags",
        required=False,
    )
    parser.add_argument(
        "--exclude-tags",
        nargs="+",
        help="Skip checks with these tags",
        required=False,
    )
    parser.add_argument(
        "--resource-types",
        nargs="+",
        help="Filter by resource type names",
        required=False,
    )
    args = parser.parse_args()

    client = Client(
        base_url=args.host,
        headers={"Authorization": f"Bearer {args.token}"} if args.token else None,
    )
    scim = SyncSCIMClient(client)
    scim.discover()

    include_tags: set[str] | None = (
        set(args.include_tags) if args.include_tags else None
    )
    exclude_tags: set[str] | None = (
        set(args.exclude_tags) if args.exclude_tags else None
    )

    results = check_server(
        scim,
        include_tags=include_tags,
        exclude_tags=exclude_tags,
        resource_types=args.resource_types,
    )

    for result in results:
        resource_info = f" [{result.resource_type}]" if result.resource_type else ""
        print(f"{result.status.name} {result.title}{resource_info}")
        if result.reason:
            print("  ", result.reason)
            if args.verbose and result.data:
                print("  ", result.data)
