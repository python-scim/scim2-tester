import re

from scim2_models import Context
from scim2_models import Error
from scim2_models import ListResponse
from scim2_models import ResourceType
from scim2_models import Schema

from scim2_tester.checkers.resource_types import _resource_types_endpoint
from scim2_tester.checkers.resource_types import access_invalid_resource_type
from scim2_tester.checkers.resource_types import query_resource_type_by_id
from scim2_tester.checkers.resource_types import resource_types_endpoint_methods
from scim2_tester.utils import Status


def test_resource_types_endpoint(httpserver, testing_context):
    """Test a fully functional resource types endpoint."""
    httpserver.expect_request(re.compile(r"^/ResourceTypes$")).respond_with_json(
        ListResponse[ResourceType](
            resources=testing_context.client.resource_types,
            total_results=len(testing_context.client.resource_types),
        ).model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=200,
        content_type="application/scim+json",
    )
    for resource_type in testing_context.client.resource_types:
        httpserver.expect_request(
            re.compile(rf"^/ResourceTypes/{resource_type.id}$")
        ).respond_with_json(
            resource_type.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
            status=200,
            content_type="application/scim+json",
        )
        mock_schema = Schema(
            id=resource_type.schema_,
            name=resource_type.name,
            description=f"Schema for {resource_type.name}",
        )
        httpserver.expect_request(
            re.compile(rf"^/Schemas/{re.escape(resource_type.schema_)}$")
        ).respond_with_json(
            mock_schema.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
            status=200,
            content_type="application/scim+json",
        )
    httpserver.expect_request(re.compile(r"^/ResourceTypes/.*$")).respond_with_json(
        Error(status=404, detail="ResourceType Not Found").model_dump(),
        status=404,
        content_type="application/scim+json",
    )

    results = _resource_types_endpoint(testing_context)

    assert all(result.status == Status.SUCCESS for result in results)


def test_resource_missing_query_endpoint(httpserver, testing_context):
    """Test that individual ResourceType endpoints are missing."""
    httpserver.expect_request(re.compile(r"^/ResourceTypes$")).respond_with_json(
        ListResponse[ResourceType](
            resources=testing_context.client.resource_types,
            total_results=len(testing_context.client.resource_types),
        ).model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=200,
        content_type="application/scim+json",
    )
    results = _resource_types_endpoint(testing_context)

    assert all(result.status == Status.ERROR for result in results[1:])


def test_resource_types_endpoint_methods(httpserver, testing_context):
    """Test that resource types endpoint returns proper errors for unsupported HTTP methods."""
    # Mock all HTTP methods to return 405
    for method in ["POST", "PUT", "PATCH", "DELETE"]:
        httpserver.expect_request(
            uri="/ResourceTypes", method=method
        ).respond_with_data("", status=405)

    results = resource_types_endpoint_methods(testing_context)

    assert len(results) == 4
    assert all(result.status == Status.SUCCESS for result in results)
    for i, method in enumerate(["POST", "PUT", "PATCH", "DELETE"]):
        assert (
            f"{method} /ResourceTypes correctly returned 405 Method Not Allowed"
            in results[i].reason
        )


def test_query_resource_type_by_id_client_returns_error(httpserver, testing_context):
    """Test query_resource_type_by_id when server returns HTTP error."""
    resource_type = ResourceType(
        id="test-id", name="Test", endpoint="/Test", schema_="urn:test"
    )

    # Mock server returning 404 error with proper SCIM Error response
    error = Error(status=404, detail="Resource Type not found")
    httpserver.expect_request(f"/ResourceTypes/{resource_type.id}").respond_with_json(
        error.model_dump(),
        status=404,
        content_type="application/scim+json",
    )

    result = query_resource_type_by_id(testing_context, resource_type)
    assert result[0].status == Status.ERROR
    assert "Resource Type not found" in result[0].reason


def test_access_resource_type_by_id_success(httpserver, testing_context):
    """Test successfully accessing a resource type by ID."""
    resource_type = testing_context.client.resource_types[0]
    httpserver.expect_request(f"/ResourceTypes/{resource_type.id}").respond_with_json(
        resource_type.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=200,
        content_type="application/scim+json",
    )

    result = query_resource_type_by_id(testing_context, resource_type)
    assert result[0].status == Status.SUCCESS
    assert (
        f"Successfully accessed the /ResourceTypes/{resource_type.id} endpoint."
        == result[0].reason
    )
    assert result[0].data.model_dump() == resource_type.model_dump()


def test_access_invalid_resource_type_non_error_response(httpserver, testing_context):
    """Test accessing an invalid resource type that returns a non-Error object."""
    mock_resource_type = ResourceType(
        id="invalid-resource-type",
        name="InvalidType",
        endpoint="/InvalidType",
        schema_="urn:invalid:schema",
    )

    httpserver.expect_request(
        re.compile(r"^/ResourceTypes/[0-9a-f-]+$")
    ).respond_with_json(
        mock_resource_type.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=404,
        content_type="application/scim+json",
    )

    result = access_invalid_resource_type(testing_context)

    assert result[0].status == Status.ERROR
    assert "invalid URL did not return an Error object" in result[0].reason
    assert result[0].data == mock_resource_type


def test_access_invalid_resource_type_wrong_status_code(httpserver, testing_context):
    """Test accessing an invalid resource type that returns wrong status code."""
    error = Error(status=400, detail="Bad Request")

    httpserver.expect_request(
        re.compile(r"^/ResourceTypes/[0-9a-f-]+$")
    ).respond_with_json(
        error.model_dump(),
        status=404,
        content_type="application/scim+json",
    )

    result = access_invalid_resource_type(testing_context)

    assert result[0].status == Status.ERROR
    assert "did return an object, but the status code is 400" in result[0].reason
    assert result[0].data == error
