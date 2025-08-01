import re

from scim2_models import Context
from scim2_models import Error
from scim2_models import ListResponse
from scim2_models import Schema

from scim2_tester.checkers.schemas import _schemas_endpoint
from scim2_tester.checkers.schemas import access_invalid_schema
from scim2_tester.checkers.schemas import access_schema_by_id
from scim2_tester.checkers.schemas import core_schemas_validation
from scim2_tester.checkers.schemas import schemas_endpoint_methods
from scim2_tester.utils import Status


def test_schemas_endpoint(httpserver, testing_context):
    """Test a fully functional schemas endpoint."""
    schemas = [model.to_schema() for model in testing_context.client.resource_models]
    httpserver.expect_request(re.compile(r"^/Schemas$")).respond_with_json(
        ListResponse[Schema](
            resources=schemas,
            total_results=len(schemas),
        ).model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=200,
        content_type="application/scim+json",
    )
    for schema in schemas:
        httpserver.expect_request(
            re.compile(rf"^/Schemas/{schema.id}$")
        ).respond_with_json(
            schema.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
            status=200,
            content_type="application/scim+json",
        )
    httpserver.expect_request(re.compile(r"^/Schemas/.*$")).respond_with_json(
        Error(status=404, detail="Schema Not Found").model_dump(),
        status=404,
        content_type="application/scim+json",
    )

    results = _schemas_endpoint(testing_context)

    assert all(result.status == Status.SUCCESS for result in results)


def test_missing_individual_schema_endpoints(httpserver, testing_context):
    """Test behavior when individual schema endpoints are not available."""
    schemas = [model.to_schema() for model in testing_context.client.resource_models]
    httpserver.expect_request(re.compile(r"^/Schemas$")).respond_with_json(
        ListResponse[Schema](
            resources=schemas,
            total_results=len(schemas),
        ).model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=200,
        content_type="application/scim+json",
    )
    results = _schemas_endpoint(testing_context)

    assert all(result.status == Status.ERROR for result in results[1:])


def test_invalid_schema_returns_non_error_response(httpserver, testing_context):
    """Test accessing an invalid schema that returns a valid schema instead of an error."""
    mock_schema = Schema(
        id="urn:ietf:params:scim:schemas:invalid:schema",
        name="InvalidSchema",
        description="This should not exist",
    )

    httpserver.expect_request(re.compile(r"^/Schemas/[0-9a-f-]+$")).respond_with_json(
        mock_schema.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=200,
        content_type="application/scim+json",
    )

    result = access_invalid_schema(testing_context)

    assert result.status == Status.ERROR
    # The client throws an exception when it gets unexpected status code
    assert "Unexpected response status code: 200" in result.reason


def test_invalid_schema_returns_wrong_error_status(httpserver, testing_context):
    """Test accessing an invalid schema that returns an error with wrong status code."""
    error_response = Error(status=400, detail="Bad Request")

    httpserver.expect_request(re.compile(r"^/Schemas/[0-9a-f-]+$")).respond_with_json(
        error_response.model_dump(), status=400, content_type="application/scim+json"
    )

    result = access_invalid_schema(testing_context)

    assert result.status == Status.ERROR
    assert "did return an Error object, but the status code is 400" in result.reason
    assert result.data == error_response


def test_schema_access_with_partial_failures(httpserver, testing_context):
    """Test accessing schemas when some individual schema requests fail."""
    schemas = [
        Schema(id="urn:ietf:params:scim:schemas:core:2.0:User", name="User"),
        Schema(id="urn:ietf:params:scim:schemas:core:2.0:Group", name="Group"),
        Schema(id="urn:error:schema", name="ErrorSchema"),
    ]

    httpserver.expect_request("/Schemas").respond_with_json(
        ListResponse[Schema](resources=schemas, total_results=len(schemas)).model_dump(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE
        ),
        status=200,
        content_type="application/scim+json",
    )

    # First two schemas succeed
    httpserver.expect_request(
        "/Schemas/urn:ietf:params:scim:schemas:core:2.0:User"
    ).respond_with_json(
        schemas[0].model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=200,
        content_type="application/scim+json",
    )

    httpserver.expect_request(
        "/Schemas/urn:ietf:params:scim:schemas:core:2.0:Group"
    ).respond_with_json(
        schemas[1].model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=200,
        content_type="application/scim+json",
    )

    # Third schema fails
    httpserver.expect_request("/Schemas/urn:error:schema").respond_with_data(
        "Internal Server Error", status=500
    )

    results = access_schema_by_id(testing_context)

    assert len(results) == 3
    assert results[0].status == Status.SUCCESS
    assert (
        "Successfully accessed schema: urn:ietf:params:scim:schemas:core:2.0:User"
        in results[0].reason
    )
    assert results[1].status == Status.SUCCESS
    assert (
        "Successfully accessed schema: urn:ietf:params:scim:schemas:core:2.0:Group"
        in results[1].reason
    )
    assert results[2].status == Status.ERROR
    assert "Failed to access schema urn:error:schema:" in results[2].reason


def test_schemas_without_ids(httpserver, testing_context):
    """Test handling of schemas that don't have IDs."""
    schemas = [
        Schema(name="User"),  # No id field
        Schema(name="Group"),  # No id field
    ]

    httpserver.expect_request("/Schemas").respond_with_json(
        ListResponse[Schema](resources=schemas, total_results=len(schemas)).model_dump(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE
        ),
        status=200,
        content_type="application/scim+json",
    )

    results = access_schema_by_id(testing_context)

    assert len(results) == 1
    assert results[0].status == Status.SUCCESS
    assert "No schemas with IDs found to test" in results[0].reason


def test_core_schemas_missing(httpserver, testing_context):
    """Test validation when mandatory core schemas are missing."""
    schemas = [
        Schema(name="User", description="User schema"),
        Schema(name="Group", description="Group schema"),
        Schema(name="ResourceType", description="ResourceType schema"),  # Present
        # Missing: ServiceProviderConfig, Schema
    ]

    httpserver.expect_request("/Schemas").respond_with_json(
        ListResponse[Schema](resources=schemas, total_results=len(schemas)).model_dump(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE
        ),
        status=200,
        content_type="application/scim+json",
    )

    result = core_schemas_validation(testing_context)

    assert result.status == Status.ERROR
    assert "Missing mandatory core schemas:" in result.reason
    assert "ServiceProviderConfig" in result.reason
    assert "Schema" in result.reason
    assert "ResourceType" not in result.reason


def test_core_schemas_all_present(httpserver, testing_context):
    """Test validation when all mandatory core schemas are present."""
    schemas = [
        Schema(name="User", description="User schema"),
        Schema(name="ResourceType", description="ResourceType schema"),
        Schema(
            name="ServiceProviderConfig", description="ServiceProviderConfig schema"
        ),
        Schema(name="Schema", description="Schema schema"),
        Schema(name="Group", description="Group schema"),
    ]

    httpserver.expect_request("/Schemas").respond_with_json(
        ListResponse[Schema](resources=schemas, total_results=len(schemas)).model_dump(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE
        ),
        status=200,
        content_type="application/scim+json",
    )

    result = core_schemas_validation(testing_context)

    assert result.status == Status.SUCCESS
    assert (
        "All mandatory core schemas (ResourceType, ServiceProviderConfig, Schema) are present"
        in result.reason
    )


def test_invalid_schema_returns_non_error_object_404(httpserver, testing_context):
    """Test accessing an invalid schema that returns a non-Error object with expected 404 status."""
    mock_schema = Schema(
        id="urn:ietf:params:scim:schemas:invalid:schema",
        name="InvalidSchema",
        description="This should not exist",
    )

    # Return a Schema object instead of an Error object, but with 404 status
    httpserver.expect_request(re.compile(r"^/Schemas/[0-9a-f-]+$")).respond_with_json(
        mock_schema.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=404,
        content_type="application/scim+json",
    )

    result = access_invalid_schema(testing_context)

    assert result.status == Status.ERROR
    assert "invalid URL did not return an Error object" in result.reason
    assert result.data == mock_schema


def test_schemas_endpoint_http_methods(httpserver, testing_context):
    """Test that schemas endpoint returns proper errors for unsupported HTTP methods."""
    # Mock all HTTP methods to return 405
    for method in ["POST", "PUT", "PATCH", "DELETE"]:
        httpserver.expect_request(uri="/Schemas", method=method).respond_with_data(
            "", status=405
        )

    results = schemas_endpoint_methods(testing_context)

    assert len(results) == 4
    assert all(result.status == Status.SUCCESS for result in results)
    for i, method in enumerate(["POST", "PUT", "PATCH", "DELETE"]):
        assert (
            f"{method} /Schemas correctly returned 405 Method Not Allowed"
            in results[i].reason
        )
