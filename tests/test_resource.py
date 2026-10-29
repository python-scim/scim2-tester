from enum import StrEnum
from unittest.mock import MagicMock
from unittest.mock import patch

from scim2_models import ComplexAttribute
from scim2_models import Context
from scim2_models import EnterpriseUser
from scim2_models import Error
from scim2_models import ListResponse
from scim2_models import Mutability
from scim2_models import Reference
from scim2_models import Resource
from scim2_models import ResourceType
from scim2_models import User

from scim2_tester.checkers.resource import resource_type_tests
from scim2_tester.checkers.resource_delete import object_deletion
from scim2_tester.checkers.resource_get import _model_from_resource_type
from scim2_tester.checkers.resource_get import object_query_without_id
from scim2_tester.checkers.resource_post import object_creation
from scim2_tester.checkers.resource_put import object_replacement
from scim2_tester.filling import fill_with_random_values
from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckContext
from scim2_tester.utils import Status


class Complex(ComplexAttribute):
    str_unique: str | None = None
    str_multiple: list[str] | None = None


class CustomModel(Resource):
    __schema__: str = "org:test:CustomModel"

    class Type(StrEnum):
        foo = "foo"
        bar = "bar"

    str_unique: str | None = None
    str_multiple: list[str] | None = None

    int_unique: int | None = None
    int_multiple: list[int] | None = None

    bool_unique: bool | None = None
    bool_multiple: list[bool] | None = None

    reference_unique: Reference | None = None
    reference_multiple: list[Reference] | None = None

    email_unique: Reference | None = None
    email_multiple: list[Reference] | None = None

    enum_unique: Type | None = None
    enum_multiple: list[Type] | None = None

    complex_unique: Complex | None = None
    complex_multiple: list[Complex] | None = None


def test_fill_with_random_values_generates_valid_data(testing_context):
    """Test that fill_with_random_values populates all fields with valid data."""
    obj = CustomModel()
    obj = fill_with_random_values(testing_context, obj)

    assert obj is not None, (
        "fill_with_random_values should not return None for test object"
    )

    for field_name in obj.__class__.model_fields:
        if obj.get_field_annotation(field_name, Mutability) == Mutability.read_only:
            continue

        assert getattr(obj, field_name) is not None


def test_resource_type_tests_with_unknown_schema(testing_context):
    """Test CRUD operations on a resource type with unknown schema."""
    resource_type = ResourceType(
        id="urn:test:UnknownResource",
        name="UnknownResource",
        endpoint="/UnknownResource",
        schema_="urn:ietf:params:scim:schemas:core:2.0:UnknownResource",
    )

    results = resource_type_tests(testing_context, resource_type)

    assert len(results) == 1
    assert results[0].status == Status.ERROR
    assert (
        f"No Schema matching the ResourceType {resource_type.id}" in results[0].reason
    )


def test_model_resolution_from_resource_type(testing_context):
    """Test model resolution from ResourceType schema."""
    unknown_resource_type = ResourceType(
        id="urn:test:UnknownResource",
        name="UnknownResource",
        endpoint="/UnknownResource",
        schema_="urn:ietf:params:scim:schemas:core:2.0:UnknownResource",
    )

    model = _model_from_resource_type(testing_context, unknown_resource_type)
    assert model is None

    # Test when model matches the schema
    user_resource_type = ResourceType(
        id="urn:ietf:params:scim:schemas:core:2.0:User",
        name="User",
        endpoint="/Users",
        schema_="urn:ietf:params:scim:schemas:core:2.0:User",
    )

    model = _model_from_resource_type(testing_context, user_resource_type)
    assert model == User[EnterpriseUser]


def test_object_query_without_id_when_object_missing_from_list(
    httpserver, testing_context
):
    """Test querying objects when the created object is missing from the list response."""
    # Mock user creation first (it happens before the query)
    created_user = User(id="test-id", user_name="test-user")
    httpserver.expect_request("/Users", method="POST").respond_with_json(
        created_user.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=201,
        content_type="application/scim+json",
    )

    # Mock empty list response (doesn't include created user)
    httpserver.expect_request("/Users", method="GET").respond_with_json(
        ListResponse[User](resources=[], total_results=0).model_dump(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE
        ),
        status=200,
        content_type="application/scim+json",
    )

    result = object_query_without_id(testing_context, User)

    assert result[0].status == Status.ERROR
    assert (
        "Could not find User object with id test-id in list response"
        in result[0].reason
    )


def test_object_deletion_when_object_persists(httpserver, testing_context):
    """Test deletion failure when object persists after DELETE request."""
    user_id = "test-user-123"
    test_user = User(id=user_id, user_name="testuser")

    httpserver.expect_request("/Users", method="POST").respond_with_json(
        test_user.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=201,
        content_type="application/scim+json",
    )
    httpserver.expect_request(f"/Users/{user_id}", method="DELETE").respond_with_data(
        "", status=204, content_type="application/scim+json"
    )
    httpserver.expect_request(f"/Users/{user_id}", method="GET").respond_with_json(
        test_user.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=200,
        content_type="application/scim+json",
    )

    result = object_deletion(testing_context, User)

    assert result[0].status == Status.ERROR
    assert (
        f"User object with id {user_id} still exists after deletion" in result[0].reason
    )


def test_object_deletion_with_wrong_status_code(httpserver, testing_context):
    """Test deletion reports error when server returns non-404 error for deleted resource."""
    user_id = "test-user-789"
    test_user = User(id=user_id, user_name="testuser")
    error_response = Error(status=500, detail="Internal server error")

    httpserver.expect_request("/Users", method="POST").respond_with_json(
        test_user.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=201,
        content_type="application/scim+json",
    )
    httpserver.expect_request(f"/Users/{user_id}", method="DELETE").respond_with_data(
        "", status=204, content_type="application/scim+json"
    )
    httpserver.expect_request(f"/Users/{user_id}", method="GET").respond_with_json(
        error_response.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=500,
        content_type="application/scim+json",
    )

    result = object_deletion(testing_context, User)

    assert result[0].status == Status.ERROR
    assert "500 instead of 404" in result[0].reason


def test_object_deletion_successful(httpserver, testing_context):
    """Test successful object deletion when server returns 404."""
    user_id = "test-user-456"
    test_user = User(id=user_id, user_name="testuser")
    error_response = Error(status=404, detail="Not found")

    httpserver.expect_request("/Users", method="POST").respond_with_json(
        test_user.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=201,
        content_type="application/scim+json",
    )
    httpserver.expect_request(f"/Users/{user_id}", method="DELETE").respond_with_data(
        "", status=204, content_type="application/scim+json"
    )
    httpserver.expect_request(f"/Users/{user_id}", method="GET").respond_with_json(
        error_response.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=404,
        content_type="application/scim+json",
    )

    result = object_deletion(testing_context, User)

    assert result[0].status == Status.SUCCESS
    assert f"Successfully deleted User object with id {user_id}" in result[0].reason


def test_object_replacement_fails_when_no_mutable_fields(testing_context):
    """Test object replacement failure when object cannot be modified."""
    # Mock resource manager to avoid HTTP calls
    mock_rm = MagicMock()
    mock_rm.create_and_register.return_value = User(id="test-id", user_name="test")
    testing_context.resource_manager = mock_rm

    with patch(
        "scim2_tester.checkers.resource_put.fill_with_random_values"
    ) as mock_fill:
        mock_fill.return_value = None

        result = object_replacement(testing_context, User)

        # The @checker decorator catches ValueError and returns CheckResult with ERROR status
        assert result[0].status == Status.ERROR
        assert "Could not modify User object with mutable fields" in result[0].reason
        assert isinstance(result[0].data, ValueError)


def _refuse_user_creation(httpserver):
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "status": "501",
            "detail": "Cannot create Users.",
        },
        status=501,
    )


def test_object_creation_refused_with_501_is_acceptable(httpserver, testing_context):
    """A server answering 501 to the creation of a resource type is acceptable."""
    _refuse_user_creation(httpserver)

    results = object_creation(testing_context, User)

    assert len(results) == 1
    assert results[0].status == Status.ACCEPTABLE
    assert results[0].reason == (
        "The server does not support creating User resources (501): "
        "Cannot create Users."
    )


def test_object_creation_failure_keeps_the_server_response(httpserver, testing_context):
    """A server error keeps the payload the server answered as the data of the result."""
    payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
        "status": "500",
        "detail": "The storage is down",
    }
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        payload, status=500, content_type="application/scim+json"
    )

    results = object_creation(testing_context, User)

    assert results[0].status == Status.ERROR
    assert results[0].data == payload


def test_checks_needing_a_resource_refused_with_501_are_skipped(
    httpserver, testing_context
):
    """The checks needing a resource the server refuses to create with 501 are skipped."""
    _refuse_user_creation(httpserver)

    results = object_deletion(testing_context, User)

    assert len(results) == 1
    assert results[0].status == Status.SKIPPED
    assert results[0].reason == (
        "The server does not support creating User resources (501): "
        "Cannot create Users."
    )


def test_checks_needing_a_resource_refused_with_501_are_skipped_when_raising(
    httpserver, scim_client
):
    """A 501 to a creation skips the checks needing it, even when exceptions are raised."""
    _refuse_user_creation(httpserver)
    context = CheckContext(scim_client, CheckConfig(raise_exceptions=True))

    assert object_creation(context, User)[0].status == Status.ACCEPTABLE
    assert object_deletion(context, User)[0].status == Status.SKIPPED
