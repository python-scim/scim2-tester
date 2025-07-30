import uuid

from scim2_models import Error
from scim2_models import Schema

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import checker


def schemas_endpoint(context: CheckContext) -> list[CheckResult]:
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

    .. todo::

        - Check the POST/PUT/PATCH/DELETE methods on the endpoint
        - Check accessing every subschema with /Schemas/urn:ietf:params:scim:schemas:core:2.0:User
        - Check that query parameters are ignored
        - Check that a 403 response is returned if a filter is passed
        - Check that the 'ResourceType', 'ServiceProviderConfig' and 'Schema' schemas are provided.
    """
    schemas_result = query_all_schemas(context)
    results = [schemas_result]

    if schemas_result.status == Status.SUCCESS:
        for resource_type in schemas_result.data:
            results.append(query_schema_by_id(context, resource_type))

    results.append(access_invalid_schema(context))

    return results


@checker("discovery", "schemas")
def query_all_schemas(context: CheckContext) -> CheckResult:
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
    return CheckResult(
        status=Status.SUCCESS,
        reason=f"Schemas available are: {available}",
        data=response.resources,
    )


@checker("discovery", "schemas")
def query_schema_by_id(context: CheckContext, schema: Schema) -> CheckResult:
    """Validate individual schema retrieval by ID.

    Tests that specific schemas can be retrieved using GET requests to
    ``/Schemas/{id}`` with their complete attribute definitions and metadata.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: :class:`~scim2_models.Schema` retrieved successfully with valid data
    - :attr:`~scim2_tester.Status.ERROR`: Failed to retrieve or received invalid response

    .. pull-quote:: :rfc:`RFC 7644 Section 7 - Schema Definition <7644#section-7>`

       "Each schema specifies the name of the resource, the resource's base URI,
       and any attributes (including sub-attributes) of the resource."
    """
    response = context.client.query(
        Schema,
        schema.id,
        expected_status_codes=context.conf.expected_status_codes or [200],
    )
    if isinstance(response, Error):
        return CheckResult(status=Status.ERROR, reason=response.detail, data=response)

    reason = f"Successfully accessed the /Schemas/{schema.id} endpoint."
    return CheckResult(status=Status.SUCCESS, reason=reason, data=response)


@checker("discovery", "schemas")
def access_invalid_schema(context: CheckContext) -> CheckResult:
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
        return CheckResult(
            status=Status.ERROR,
            reason=f"/Schemas/{probably_invalid_id} invalid URL did not return an Error object",
            data=response,
        )

    if response.status != 404:
        return CheckResult(
            status=Status.ERROR,
            reason=f"/Schemas/{probably_invalid_id} invalid URL did return an Error object, but the status code is {response.status}",
            data=response,
        )

    return CheckResult(
        status=Status.SUCCESS,
        reason=f"/Schemas/{probably_invalid_id} invalid URL correctly returned a 404 error",
        data=response,
    )
