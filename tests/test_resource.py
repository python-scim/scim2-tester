from enum import Enum
from unittest.mock import MagicMock
from unittest.mock import patch

from pydantic import Field
from scim2_models import ComplexAttribute
from scim2_models import Context
from scim2_models import ListResponse
from scim2_models import Reference
from scim2_models import Resource
from scim2_models import ResourceType
from scim2_models import User

from scim2_tester.checkers.resource import resource_type_tests
from scim2_tester.checkers.resource_delete import object_deletion
from scim2_tester.checkers.resource_get import _model_from_resource_type
from scim2_tester.checkers.resource_get import object_query_without_id
from scim2_tester.checkers.resource_put import object_replacement
from scim2_tester.filling import fill_with_random_values
from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckContext
from scim2_tester.utils import Status


class Complex(ComplexAttribute):
    str_unique: str | None = None
    str_multiple: list[str] | None = None


class CustomModel(Resource):
    schemas: list[str] = ["org:test:CustomModel"]

    class Type(str, Enum):
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

    example_unique: str | None = Field(None, examples=["foo", "bar"])
    example_multiple: list[str] | None = Field(None, examples=["foo", "bar"])


def test_fill_with_random_values_generates_valid_data():
    """Test that fill_with_random_values populates all fields with valid data."""

    class MockClient:
        pass

    conf = CheckConfig()
    context = CheckContext(MockClient(), conf)

    obj = CustomModel()
    obj = fill_with_random_values(context, obj, context.resource_manager)

    assert obj is not None, (
        "fill_with_random_values should not return None for test object"
    )

    for field_name in obj.__class__.model_fields:
        if field_name == "meta":
            continue

        assert getattr(obj, field_name) is not None

    assert obj.example_unique in ["foo", "bar"]
    assert all(val in ["foo", "bar"] for val in obj.example_multiple)


def test_resource_type_tests_with_unknown_schema(check_config):
    """Test CRUD operations on a resource type with unknown schema."""
    resource_type = ResourceType(
        id="urn:test:UnknownResource",
        name="UnknownResource",
        endpoint="/UnknownResource",
        schema_="urn:ietf:params:scim:schemas:core:2.0:UnknownResource",
    )

    results = resource_type_tests(check_config, resource_type)

    assert len(results) == 1
    assert results[0].status == Status.ERROR
    assert (
        f"No Schema matching the ResourceType {resource_type.id}" in results[0].reason
    )


def test_model_resolution_from_resource_type(check_config):
    """Test model resolution from ResourceType schema."""
    unknown_resource_type = ResourceType(
        id="urn:test:UnknownResource",
        name="UnknownResource",
        endpoint="/UnknownResource",
        schema_="urn:ietf:params:scim:schemas:core:2.0:UnknownResource",
    )

    model = _model_from_resource_type(check_config, unknown_resource_type)
    assert model is None

    # Test when model matches the schema
    user_resource_type = ResourceType(
        id="urn:ietf:params:scim:schemas:core:2.0:User",
        name="User",
        endpoint="/Users",
        schema_="urn:ietf:params:scim:schemas:core:2.0:User",
    )

    model = _model_from_resource_type(check_config, user_resource_type)
    assert model == User


def test_object_query_without_id_when_object_missing_from_list(
    httpserver, check_config
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

    result = object_query_without_id(check_config, User)

    assert result.status == Status.ERROR
    assert (
        "Could not find User object with id test-id in list response" in result.reason
    )


def test_object_deletion_with_null_id(check_config):
    """Test deletion of objects without an ID."""

    class MockResourceManager:
        def __init__(self):
            self.resources = []

        def create_and_register(self, model):
            obj = model(user_name="test")
            obj.id = None
            self.resources.append(obj)
            return obj

        def cleanup(self):
            pass

    original_rm = check_config.resource_manager
    check_config.resource_manager = MockResourceManager()

    try:
        result = object_deletion(check_config, User)
        assert result.status == Status.SUCCESS
        assert "Successfully deleted User object with id None" in result.reason
    finally:
        check_config.resource_manager = original_rm


def test_object_deletion_when_object_persists(httpserver, check_config):
    """Test deletion failure when object persists after DELETE request."""
    user_id = "test-user-123"
    test_user = User(id=user_id, user_name="testuser")

    # Mock user creation
    httpserver.expect_request("/Users", method="POST").respond_with_json(
        test_user.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=201,
        content_type="application/scim+json",
    )

    # Mock deletion request
    httpserver.expect_request(f"/Users/{user_id}", method="DELETE").respond_with_data(
        "", status=204, content_type="application/scim+json"
    )

    # Mock query showing object still exists
    httpserver.expect_request(f"/Users/{user_id}").respond_with_json(
        test_user.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=200,
        content_type="application/scim+json",
    )

    result = object_deletion(check_config, User)

    assert result.status == Status.ERROR
    assert f"User object with id {user_id} still exists after deletion" in result.reason


def test_object_deletion_successful(httpserver, check_config):
    """Test successful object deletion when object is properly removed."""
    user_id = "test-user-456"
    test_user = User(id=user_id, user_name="testuser")

    # Mock user creation
    httpserver.expect_request("/Users", method="POST").respond_with_json(
        test_user.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=201,
        content_type="application/scim+json",
    )

    # Mock deletion
    httpserver.expect_request(f"/Users/{user_id}", method="DELETE").respond_with_data(
        "", status=204, content_type="application/scim+json"
    )

    # Mock query returning 404 (object properly deleted)
    httpserver.expect_request(f"/Users/{user_id}").respond_with_data(
        "Not Found", status=404
    )

    result = object_deletion(check_config, User)

    assert result.status == Status.SUCCESS
    assert f"Successfully deleted User object with id {user_id}" in result.reason


def test_object_replacement_fails_when_no_mutable_fields():
    """Test object replacement failure when object cannot be modified."""

    # Create a context with mock resource manager
    class MockClient:
        pass

    conf = CheckConfig()
    context = CheckContext(MockClient(), conf)

    # Mock resource manager to avoid HTTP calls
    mock_rm = MagicMock()
    mock_rm.create_and_register.return_value = User(id="test-id", user_name="test")
    context.resource_manager = mock_rm

    with patch(
        "scim2_tester.checkers.resource_put.fill_with_random_values"
    ) as mock_fill:
        mock_fill.return_value = None

        result = object_replacement(context, User)

        # The @checker decorator catches ValueError and returns CheckResult with ERROR status
        assert result.status == Status.ERROR
        assert "Could not modify User object with mutable fields" in result.reason
        assert isinstance(result.data, ValueError)
