import uuid

from scim2_client import SCIMClientError
from scim2_models import Error
from scim2_models import Schema

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
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

    .. pull-quote:: :rfc:`RFC 7644 Section 4 - Discovery <7644#section-4>`

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

    results.extend(access_invalid_schema(context))

    return results


@checker("*", "discovery", "schemas")
def query_all_schemas(context: CheckContext) -> list[CheckResult]:
    """Validate retrieval of all available schemas.

    Tests that the ``/Schemas`` endpoint returns a complete list of all supported
    schemas including core schemas, extensions, and custom schemas.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Endpoint returns valid list of :class:`~scim2_models.Schema` objects
    - :attr:`~scim2_tester.Status.ERROR`: Endpoint is inaccessible or returns invalid response

    .. pull-quote:: :rfc:`RFC 7644 Section 4 - Discovery <7644#section-4>`

       "An HTTP GET to this endpoint is used to retrieve information about
       resource schemas supported by a SCIM service provider."
    """
    response = context.client.query(
        Schema, expected_status_codes=context.conf.expected_status_codes or [200]
    )
    available = ", ".join([f"'{resource.name}'" for resource in response.resources])
    return [
        CheckResult(
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

       "When returning HTTP error status codes, the server SHOULD return
       a SCIM error response."
    """
    probably_invalid_id = str(uuid.uuid4())
    response = context.client.query(
        Schema,
        probably_invalid_id,
        expected_status_codes=context.conf.expected_status_codes or [404],
        raise_scim_errors=False,
    )

    if not isinstance(response, Error):
        return [
            CheckResult(
                status=Status.ERROR,
                reason=f"/Schemas/{probably_invalid_id} invalid URL did not return an Error object",
                data=response,
            )
        ]

    if response.status != 404:
        return [
            CheckResult(
                status=Status.ERROR,
                reason=f"/Schemas/{probably_invalid_id} invalid URL did return an Error object, but the status code is {response.status}",
                data=response,
            )
        ]

    return [
        CheckResult(
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
    endpoint correctly return HTTP 405 Method Not Allowed status, as only GET is supported.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: All unsupported methods return 405 status
    - :attr:`~scim2_tester.Status.ERROR`: One or more methods return unexpected status

    .. pull-quote:: :rfc:`RFC 7644 Section 4 - Discovery <7644#section-4>`

       "An HTTP GET to this endpoint is used to retrieve information about
       resource schemas supported by a SCIM service provider."

       Only GET method is specified, other methods should return appropriate errors.
    """
    return _test_discovery_endpoint_methods(context, "/Schemas")


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
    schemas_response = context.client.query(
        Schema, expected_status_codes=context.conf.expected_status_codes or [200]
    )

    results = []
    for schema in schemas_response.resources:
        if schema.id:
            try:
                response = context.client.query(
                    Schema,
                    schema.id,
                    expected_status_codes=context.conf.expected_status_codes or [200],
                )
                results.append(
                    CheckResult(
                        status=Status.SUCCESS,
                        reason=f"Successfully accessed schema: {schema.id}",
                        data=response,
                    )
                )
            except SCIMClientError as e:
                results.append(
                    CheckResult(
                        status=Status.ERROR,
                        reason=f"Failed to access schema {schema.id}: {str(e)}",
                    )
                )

    if not results:
        results.append(
            CheckResult(
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

    .. pull-quote:: :rfc:`RFC 7644 Section 4 - Discovery <7644#section-4>`

       "Service providers MUST provide this endpoint."

       The core schemas for ResourceType, ServiceProviderConfig, and Schema
       objects are fundamental to SCIM operation and should always be available.
    """
    response = context.client.query(
        Schema, expected_status_codes=context.conf.expected_status_codes or [200]
    )

    required_schemas = {
        "ResourceType": False,
        "ServiceProviderConfig": False,
        "Schema": False,
    }

    for schema in response.resources:
        schema_name = getattr(schema, "name", "")
        if schema_name in required_schemas:
            required_schemas[schema_name] = True

    missing_schemas = [name for name, found in required_schemas.items() if not found]

    if missing_schemas:
        return [
            CheckResult(
                status=Status.ERROR,
                reason=f"Missing mandatory core schemas: {', '.join(missing_schemas)}",
                data=response,
            )
        ]

    return [
        CheckResult(
            status=Status.SUCCESS,
            reason="All mandatory core schemas (ResourceType, ServiceProviderConfig, Schema) are present",
            data=response,
        )
    ]
