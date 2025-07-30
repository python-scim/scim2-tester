import uuid

from scim2_client import SCIMClientError
from scim2_models import Error
from scim2_models import ResourceType
from scim2_models import Schema

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import checker
from ._discovery_utils import _test_discovery_endpoint_methods


def _resource_types_endpoint(context: CheckContext) -> list[CheckResult]:
    """Orchestrate validation of the ResourceTypes discovery endpoint.

    Runs comprehensive tests on the ``/ResourceTypes`` endpoint including listing
    all resource types, querying individual types by ID, and error handling for
    invalid requests.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: All sub-checks completed successfully
    - :attr:`~scim2_tester.Status.ERROR`: One or more sub-checks failed

    .. pull-quote:: :rfc:`RFC 7644 Section 4 - Discovery <7644#section-4>`

       "An HTTP GET to this endpoint is used to discover the types of resources
       available on a SCIM service provider (e.g., Users and Groups)."

       "Service providers MUST provide this endpoint."

    """
    resource_types_result = query_all_resource_types(context)
    results = [resource_types_result]

    if resource_types_result.status == Status.SUCCESS:
        for resource_type in resource_types_result.data:
            results.append(query_resource_type_by_id(context, resource_type))

        results.extend(resource_types_schema_validation(context))

    results.append(access_invalid_resource_type(context))

    return results


@checker("discovery", "resource-types")
def resource_types_endpoint_methods(
    context: CheckContext,
) -> list[CheckResult]:
    """Validate that unsupported HTTP methods return 405 Method Not Allowed.

    Tests that POST, PUT, PATCH, and DELETE methods on the ``/ResourceTypes``
    endpoint correctly return HTTP 405 Method Not Allowed status, as only GET is supported.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: All unsupported methods return 405 status
    - :attr:`~scim2_tester.Status.ERROR`: One or more methods return unexpected status

    .. pull-quote:: :rfc:`RFC 7644 Section 4 - Discovery <7644#section-4>`

       "An HTTP GET to this endpoint is used to discover the types of resources
       available on a SCIM service provider."

       Only GET method is specified, other methods should return appropriate errors.
    """
    return _test_discovery_endpoint_methods(context, "/ResourceTypes")


@checker("discovery", "resource-types")
def resource_types_schema_validation(
    context: CheckContext,
) -> list[CheckResult]:
    """Validate that ResourceType schemas exist and are accessible.

    Tests that all :class:`~scim2_models.ResourceType` objects returned by the
    ``/ResourceTypes`` endpoint reference valid schemas that can be retrieved
    from the ``/Schemas`` endpoint.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: All ResourceType schemas are accessible
    - :attr:`~scim2_tester.Status.ERROR`: One or more ResourceType schemas are missing or inaccessible

    .. pull-quote:: :rfc:`RFC 7644 Section 4 - Discovery <7644#section-4>`

       "Each resource type defines the endpoint, the core schema URI that defines
       the resource, and any supported schema extensions."
    """
    response = context.client.query(
        ResourceType, expected_status_codes=context.conf.expected_status_codes or [200]
    )

    results = []
    for resource_type in response.resources:
        schema_id = resource_type.schema_
        try:
            schema_response = context.client.query(
                Schema,
                schema_id,
                expected_status_codes=context.conf.expected_status_codes or [200],
            )
            results.append(
                CheckResult(
                    status=Status.SUCCESS,
                    reason=f"ResourceType '{resource_type.name}' schema '{schema_id}' is accessible",
                    data=schema_response,
                )
            )
        except SCIMClientError as e:
            results.append(
                CheckResult(
                    status=Status.ERROR,
                    reason=f"ResourceType '{resource_type.name}' schema '{schema_id}' is not accessible: {str(e)}",
                )
            )

    return results


@checker("discovery", "resource-types")
def query_all_resource_types(context: CheckContext) -> CheckResult:
    """Validate retrieval of all available resource types.

    Tests that the ``/ResourceTypes`` endpoint returns a list of all supported
    resource types with their metadata, schemas, and endpoint information.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Endpoint returns valid list of :class:`~scim2_models.ResourceType` objects
    - :attr:`~scim2_tester.Status.ERROR`: Endpoint is inaccessible or returns invalid response

    .. pull-quote:: :rfc:`RFC 7644 Section 4 - Discovery <7644#section-4>`

       "An HTTP GET to this endpoint is used to discover the types of resources
       available on a SCIM service provider (e.g., Users and Groups)."
    """
    response = context.client.query(
        ResourceType, expected_status_codes=context.conf.expected_status_codes or [200]
    )
    available = ", ".join([f"'{resource.name}'" for resource in response.resources])
    reason = f"Resource types available are: {available}"
    return CheckResult(status=Status.SUCCESS, reason=reason, data=response.resources)


@checker("discovery", "resource-types")
def query_resource_type_by_id(
    context: CheckContext, resource_type: ResourceType
) -> CheckResult:
    """Validate individual ResourceType retrieval by ID.

    Tests that specific resource types can be retrieved using GET requests
    to ``/ResourceTypes/{id}`` with their complete metadata and configuration.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: :class:`~scim2_models.ResourceType` retrieved successfully with valid data
    - :attr:`~scim2_tester.Status.ERROR`: Failed to retrieve or received invalid response

    .. pull-quote:: :rfc:`RFC 7644 Section 4 - Discovery <7644#section-4>`

       "Each resource type defines the endpoint, the core schema URI that defines
       the resource, and any supported schema extensions."
    """
    response = context.client.query(
        ResourceType,
        resource_type.id,
        expected_status_codes=context.conf.expected_status_codes or [200],
    )
    reason = f"Successfully accessed the /ResourceTypes/{resource_type.id} endpoint."
    return CheckResult(status=Status.SUCCESS, reason=reason, data=response)


@checker("discovery", "resource-types")
def access_invalid_resource_type(context: CheckContext) -> CheckResult:
    """Validate error handling for non-existent resource type IDs.

    Tests that accessing ``/ResourceTypes/{invalid_id}`` with a non-existent resource
    type ID returns appropriate :class:`~scim2_models.Error` object with 404 status.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Server returns :class:`~scim2_models.Error` object with 404 status
    - :attr:`~scim2_tester.Status.ERROR`: Server returns non-:class:`~scim2_models.Error` object or incorrect status

    .. pull-quote:: :rfc:`RFC 7644 Section 3.12 - Error Response Handling <7644#section-3.12>`

       "When returning HTTP error status codes, the server SHOULD return a SCIM error response."
    """
    probably_invalid_id = str(uuid.uuid4())
    response = context.client.query(
        ResourceType,
        probably_invalid_id,
        expected_status_codes=context.conf.expected_status_codes or [404],
        raise_scim_errors=False,
    )

    if not isinstance(response, Error):
        return CheckResult(
            status=Status.ERROR,
            reason=f"/resource_types/{probably_invalid_id} invalid URL did not return an Error object",
            data=response,
        )

    if response.status != 404:
        return CheckResult(
            status=Status.ERROR,
            reason=f"/resource_types/{probably_invalid_id} invalid URL did return an object, but the status code is {response.status}",
            data=response,
        )

    return CheckResult(
        status=Status.SUCCESS,
        reason=f"/resource_types/{probably_invalid_id} invalid URL correctly returned a 404 error",
        data=response,
    )
