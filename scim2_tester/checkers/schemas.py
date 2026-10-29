from typing import cast

from scim2_client import SCIMClientException
from scim2_client import UnexpectedStatusCodeException
from scim2_models import Error
from scim2_models import ListResponse
from scim2_models import Schema
from scim2_models import SCIMException

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import check_result
from ..utils import checker
from ._discovery_utils import _test_discovery_endpoint_methods


def _schemas_endpoint(context: CheckContext) -> list[CheckResult]:
    """Orchestrate validation of the Schemas discovery endpoint.

    Runs comprehensive tests on the ``/Schemas`` endpoint including listing
    all schemas, querying individual schemas by ID, and error handling for
    invalid schema requests.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: All sub-checks completed successfully
    - :attr:`~scim2_tester.Status.ERROR`: One or more sub-checks failed

    .. pull-quote:: :rfc:`RFC 7644 Section 4 - Service Provider Configuration Endpoints <7644#section-4>`

       "An HTTP GET to this endpoint is used to retrieve information about
       resource schemas supported by a SCIM service provider."

       "Service providers MUST provide this endpoint."

    """
    schemas_result_list = query_all_schemas(context)
    results = []
    results.extend(schemas_result_list)
    schemas_result = schemas_result_list[0]  # Get the first (and only) result

    if schemas_result.status == Status.SUCCESS:
        results.extend(access_schema_by_id(context))
        for schema in schemas_result.data or []:
            if schema.id:
                for result in schema_by_id_methods(context, schema):
                    result.attribute = schema.id
                    results.append(result)

    results.extend(access_invalid_schema(context))
    results.extend(schemas_endpoint_methods(context))

    return results


@checker("*", "discovery", "schemas")
def query_all_schemas(context: CheckContext) -> list[CheckResult]:
    """Validate retrieval of all available schemas.

    Tests that the ``/Schemas`` endpoint returns a complete list of all supported
    schemas including core schemas, extensions, and custom schemas.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Endpoint returns valid list of :class:`~scim2_models.Schema` objects
    - :attr:`~scim2_tester.Status.ERROR`: Endpoint is inaccessible or returns invalid response

    .. pull-quote:: :rfc:`RFC 7644 Section 4 - Service Provider Configuration Endpoints <7644#section-4>`

       "An HTTP GET to this endpoint is used to retrieve information about
       resource schemas supported by a SCIM service provider."
    """
    response = cast(
        "ListResponse[Schema]",
        context.client.query(
            Schema, expected_status_codes=context.conf.expected_status_codes or [200]
        ),
    )
    if not response.resources:
        return [
            check_result(
                context,
                status=Status.ERROR,
                reason="The /Schemas endpoint published nothing",
                data=response,
            )
        ]

    available = ", ".join([f"'{resource.name}'" for resource in response.resources])
    return [
        check_result(
            context,
            status=Status.SUCCESS,
            reason=f"Schemas available are: {available}",
            data=response.resources,
        )
    ]


@checker("discovery", "schemas")
def access_invalid_schema(context: CheckContext) -> list[CheckResult]:
    """Validate error handling for non-existent schema IDs.

    Tests that accessing ``/Schemas/{invalid_id}`` with a non-existent schema
    ID returns appropriate :class:`~scim2_models.Error` object with 404 status.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Server returns :class:`~scim2_models.Error` object with 404 status
    - :attr:`~scim2_tester.Status.ERROR`: Server returns non-:class:`~scim2_models.Error` object or incorrect status

    .. pull-quote:: :rfc:`RFC 7644 Section 3.12 - Error Response Handling <7644#section-3.12>`

       "In addition to returning an HTTP response code, implementers MUST return
       the errors in the body of the response in a JSON format"
    """
    probably_invalid_id = str(context.random_uuid())
    try:
        response = context.client.query(
            Schema,
            probably_invalid_id,
            expected_status_codes=context.conf.expected_status_codes or [404],
            raise_scim_errors=False,
        )
    except UnexpectedStatusCodeException as exc:
        return [
            check_result(
                context,
                status=Status.ERROR,
                reason=f"/Schemas/{probably_invalid_id} invalid URL did not return an Error object: {exc}",
                data=exc,
            )
        ]

    if not isinstance(response, Error):
        return [
            check_result(
                context,
                status=Status.ERROR,
                reason=f"/Schemas/{probably_invalid_id} invalid URL did not return an Error object",
                data=response,
            )
        ]

    if response.status != 404:
        return [
            check_result(
                context,
                status=Status.ERROR,
                reason=f"/Schemas/{probably_invalid_id} invalid URL did return an Error object, but the status code is {response.status}",
                data=response,
            )
        ]

    return [
        check_result(
            context,
            status=Status.SUCCESS,
            reason=f"/Schemas/{probably_invalid_id} invalid URL correctly returned a 404 error",
            data=response,
        )
    ]


@checker("discovery", "schemas")
def schemas_endpoint_methods(
    context: CheckContext,
) -> list[CheckResult]:
    """Validate that unsupported HTTP methods return 405 Method Not Allowed.

    Tests that POST, PUT, PATCH, and DELETE methods on the ``/Schemas``
    endpoint return HTTP 405 Method Not Allowed, as :rfc:`7644` §4 only defines GET.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Every method returns 405
    - :attr:`~scim2_tester.Status.DEVIATION`: A method returns 404, 501 or another 4xx status
    - :attr:`~scim2_tester.Status.ERROR`: A method succeeds, or returns another 5xx status

    The check returns one result, with the worst status of the methods.

    .. pull-quote:: :rfc:`RFC 7644 Section 4 - Service Provider Configuration Endpoints <7644#section-4>`

       "An HTTP GET to this endpoint is used to retrieve information about
       resource schemas supported by a SCIM service provider."

    .. pull-quote:: :rfc:`RFC 9110 Section 15.5.6 - 405 Method Not Allowed <9110#section-15.5.6>`

       "The 405 (Method Not Allowed) status code indicates that the method
       received in the request-line is known by the origin server but not
       supported by the target resource."
    """
    return _test_discovery_endpoint_methods(context, "/Schemas")


@checker("discovery", "schemas")
def schema_by_id_methods(context: CheckContext, schema: Schema) -> list[CheckResult]:
    """Validate that unsupported HTTP methods on a schema return 405 Method Not Allowed.

    Tests that POST, PUT, PATCH, and DELETE methods on the ``/Schemas/{id}``
    endpoint return HTTP 405 Method Not Allowed, as :rfc:`7644` §4 only defines GET.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Every method returns 405
    - :attr:`~scim2_tester.Status.DEVIATION`: A method returns 404, 501 or another 4xx status
    - :attr:`~scim2_tester.Status.ERROR`: A method succeeds, or returns another 5xx status

    The check returns one result, with the worst status of the methods.

    .. pull-quote:: :rfc:`RFC 7644 Section 4 - Service Provider Configuration Endpoints <7644#section-4>`

       "Individual schema definitions can be returned by appending the schema
       URI to the /Schemas endpoint."

    .. pull-quote:: :rfc:`RFC 9110 Section 15.5.6 - 405 Method Not Allowed <9110#section-15.5.6>`

       "The 405 (Method Not Allowed) status code indicates that the method
       received in the request-line is known by the origin server but not
       supported by the target resource."
    """
    return _test_discovery_endpoint_methods(context, f"/Schemas/{schema.id}")


@checker("discovery", "schemas")
def access_schema_by_id(
    context: CheckContext,
) -> list[CheckResult]:
    """Validate individual schema retrieval by ID.

    Tests that all schemas can be retrieved using GET requests to
    ``/Schemas/{id}`` with their complete attribute definitions and metadata.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: All schemas retrieved successfully with valid data
    - :attr:`~scim2_tester.Status.ERROR`: One or more schemas failed to retrieve

    .. pull-quote:: :rfc:`RFC 7644 Section 7 - Schema Definition <7644#section-7>`

       "Each schema specifies the name of the resource, the resource's base URI,
       and any attributes (including sub-attributes) of the resource."
    """
    schemas_response = cast(
        "ListResponse[Schema]",
        context.client.query(
            Schema, expected_status_codes=context.conf.expected_status_codes or [200]
        ),
    )

    # CheckResult has no field for the queried schema. Its URN goes in the
    # attribute field, as an attribute path starts with the URN of its schema.
    results = []
    for schema in schemas_response.resources or []:
        if schema.id:
            try:
                response = context.client.query(
                    Schema,
                    schema.id,
                    expected_status_codes=context.conf.expected_status_codes or [200],
                )
                results.append(
                    check_result(
                        context,
                        status=Status.SUCCESS,
                        reason=f"Successfully accessed schema: {schema.id}",
                        data=response,
                        attribute=schema.id,
                    )
                )
            except (SCIMClientException, SCIMException) as e:
                results.append(
                    check_result(
                        context,
                        status=Status.ERROR,
                        reason=f"Failed to access schema {schema.id}: {str(e)}",
                        attribute=schema.id,
                    )
                )

    if not results:
        results.append(
            check_result(
                context,
                status=Status.SUCCESS,
                reason="No schemas with IDs found to test",
            )
        )

    return results


@checker("discovery", "schemas")
def core_schemas_validation(
    context: CheckContext,
) -> list[CheckResult]:
    """Validate that mandatory core schemas are provided.

    Tests that the ``/Schemas`` endpoint provides the three mandatory core schemas:
    ResourceType, ServiceProviderConfig, and Schema schemas themselves.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: All mandatory core schemas are present
    - :attr:`~scim2_tester.Status.ERROR`: One or more mandatory schemas are missing

    .. pull-quote:: :rfc:`RFC 7644 Section 4 - Service Provider Configuration Endpoints <7644#section-4>`

       "Service providers MUST provide this endpoint."

       The core schemas for ResourceType, ServiceProviderConfig, and Schema
       objects are fundamental to SCIM operation and should always be available.
    """
    response = cast(
        "ListResponse[Schema]",
        context.client.query(
            Schema, expected_status_codes=context.conf.expected_status_codes or [200]
        ),
    )

    required_schemas = {
        "ResourceType": False,
        "ServiceProviderConfig": False,
        "Schema": False,
    }

    for schema in response.resources or []:
        schema_name = getattr(schema, "name", "")
        if schema_name in required_schemas:
            required_schemas[schema_name] = True

    missing_schemas = [name for name, found in required_schemas.items() if not found]

    if missing_schemas:
        return [
            check_result(
                context,
                status=Status.ERROR,
                reason=f"Missing mandatory core schemas: {', '.join(missing_schemas)}",
                data=response,
            )
        ]

    return [
        check_result(
            context,
            status=Status.SUCCESS,
            reason="All mandatory core schemas (ResourceType, ServiceProviderConfig, Schema) are present",
            data=response,
        )
    ]
