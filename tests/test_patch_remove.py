"""Unit tests for PATCH remove operation checkers."""

import json

from scim2_models import EnterpriseUser
from scim2_models import User
from werkzeug.wrappers import Response

from scim2_tester.checkers.patch_remove import check_remove_attribute
from scim2_tester.utils import Status


def test_successful_remove(httpserver, testing_context):
    """Test successful PATCH remove returns SUCCESS in CheckResult."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
            "displayName": "Test User",
            "nickName": "testy",
        },
        status=201,
    )

    # Track the state of the resource
    resource_state = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": "123",
        "userName": "test@example.com",
        "displayName": "Test User",
        "nickName": "testy",
    }

    def get_handler(request):
        return Response(
            json.dumps(resource_state),
            status=200,
            headers={"Content-Type": "application/scim+json"},
        )

    def patch_handler(request):
        nonlocal resource_state
        patch_data = json.loads(request.get_data(as_text=True))
        operation = patch_data["Operations"][0]
        path = operation["path"]

        field_mapping = {
            "display_name": "displayName",
            "nick_name": "nickName",
            "profile_url": "profileUrl",
            "user_type": "userType",
            "preferred_language": "preferredLanguage",
        }

        json_field = field_mapping.get(path, path)
        del resource_state[json_field]

        return Response(
            json.dumps(resource_state),
            status=200,
            headers={"Content-Type": "application/scim+json"},
        )

    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_handler(
        patch_handler
    )
    httpserver.expect_request(uri="/Users/123", method="GET").respond_with_handler(
        get_handler
    )

    results = check_remove_attribute(testing_context, User)
    unexpected = [r for r in results if r.status != Status.SUCCESS]
    assert not unexpected


def test_remove_server_error(httpserver, testing_context):
    """Test PATCH remove server error returns ERROR in CheckResult."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
            "displayName": "Test User",
        },
        status=201,
    )

    def patch_handler(request):
        return Response(
            json.dumps(
                {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                    "status": "500",
                    "detail": "Internal Server Error",
                }
            ),
            status=500,
            headers={"Content-Type": "application/scim+json"},
        )

    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_handler(
        patch_handler
    )

    results = check_remove_attribute(testing_context, User)
    unexpected = [r for r in results if r.status != Status.ERROR]
    assert not unexpected


def test_attribute_not_removed(httpserver, testing_context):
    """Test attribute not removed returns ERROR in CheckResult."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
            "displayName": "Test User",
            "nickName": "testy",
        },
        status=201,
    )

    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
            "displayName": "Test User",
            "nickName": "testy",
        },
        status=200,
    )

    results = check_remove_attribute(testing_context, User)
    unexpected = [r for r in results if r.status != Status.ERROR]
    assert not unexpected


def test_no_removable_attributes(testing_context):
    """Test no removable attributes returns SKIPPED."""
    from unittest.mock import patch

    with patch(
        "scim2_tester.checkers.patch_remove.iter_all_urns",
        return_value=iter([]),
    ):
        results = check_remove_attribute(testing_context, User)
        unexpected = [r for r in results if r.status != Status.SKIPPED]
    assert not unexpected


def test_complex_successful_remove(httpserver, testing_context):
    """Test successful PATCH remove for complex attributes returns SUCCESS."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
            "name": {
                "givenName": "Test",
                "familyName": "User",
            },
        },
        status=201,
    )

    # Track the state of the resource
    resource_state = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": "123",
        "userName": "test@example.com",
        "name": {
            "givenName": "Test",
            "familyName": "User",
        },
    }

    def get_handler(request):
        return Response(
            json.dumps(resource_state),
            status=200,
            headers={"Content-Type": "application/scim+json"},
        )

    def patch_handler(request):
        nonlocal resource_state
        patch_data = json.loads(request.get_data(as_text=True))
        operation = patch_data["Operations"][0]
        path = operation["path"]

        del resource_state[path]

        return Response(
            json.dumps(resource_state),
            status=200,
            headers={"Content-Type": "application/scim+json"},
        )

    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_handler(
        patch_handler
    )
    httpserver.expect_request(uri="/Users/123", method="GET").respond_with_handler(
        get_handler
    )

    results = check_remove_attribute(testing_context, User)
    unexpected = [r for r in results if r.status != Status.SUCCESS]
    assert not unexpected


def test_user_with_enterprise_extension_remove(httpserver, testing_context):
    """Test PATCH remove with User[EnterpriseUser] extension support."""

    def create_handler(request):
        request_data = json.loads(request.get_data(as_text=True))
        resource_id = "123e4567-e89b-12d3-a456-426614174000"

        response_data = {
            "schemas": [
                "urn:ietf:params:scim:schemas:core:2.0:User",
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            ],
            "id": resource_id,
            "meta": {
                "resourceType": "User",
                "location": f"http://localhost/Users/{resource_id}",
                "created": "2024-01-01T00:00:00Z",
                "lastModified": "2024-01-01T00:00:00Z",
                "version": 'W/"1"',
            },
        }

        for key in [
            "userName",
            "displayName",
            "nickName",
            "profileUrl",
            "userType",
            "preferredLanguage",
        ]:
            response_data[key] = request_data[key]

        return Response(
            json.dumps(response_data),
            status=201,
            headers={
                "Content-Type": "application/scim+json",
                "Location": f"http://localhost/Users/{resource_id}",
            },
        )

    httpserver.expect_request(uri="/Users", method="POST").respond_with_handler(
        create_handler
    )

    # Track the state of the resource
    resource_state = {
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "meta": {
            "resourceType": "User",
            "location": "http://localhost/Users/123e4567-e89b-12d3-a456-426614174000",
            "created": "2024-01-01T00:00:00Z",
            "lastModified": "2024-01-01T00:00:00Z",
            "version": 'W/"2"',
        },
        "userName": "test@example.com",
        "displayName": "Test User",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
            "employeeNumber": "EMP001",
            "department": "Engineering",
        },
    }

    def get_handler(request):
        return Response(
            json.dumps(resource_state),
            status=200,
            headers={"Content-Type": "application/scim+json"},
        )

    def update_patch_handler(request):
        nonlocal resource_state
        patch_data = json.loads(request.get_data(as_text=True))
        operation = patch_data["Operations"][0]
        path = operation["path"]

        field_mapping = {
            "display_name": "displayName",
            "nick_name": "nickName",
            "profile_url": "profileUrl",
            "user_type": "userType",
            "preferred_language": "preferredLanguage",
        }
        json_field = field_mapping.get(path, path)
        if json_field in resource_state:
            del resource_state[json_field]

        return Response(
            json.dumps(resource_state),
            status=200,
            headers={"Content-Type": "application/scim+json"},
        )

    httpserver.expect_request(
        uri="/Users/123e4567-e89b-12d3-a456-426614174000", method="PATCH"
    ).respond_with_handler(update_patch_handler)

    httpserver.expect_request(
        uri="/Users/123e4567-e89b-12d3-a456-426614174000", method="GET"
    ).respond_with_handler(get_handler)

    httpserver.expect_request(
        uri="/Users/123e4567-e89b-12d3-a456-426614174000", method="DELETE"
    ).respond_with_data("", status=204)

    results = check_remove_attribute(testing_context, User[EnterpriseUser])

    unexpected = [r for r in results if r.status != Status.SUCCESS]
    assert not unexpected, (
        f"All results should be SUCCESS, got: {[r.reason for r in results if r.status != Status.SUCCESS]}"
    )


def test_patch_remove_query_failure_after_patch(httpserver, testing_context):
    """Test PATCH remove when query fails after successful patch."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
            "displayName": "test_display",
        },
        status=201,
    )

    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
        },
        status=200,
    )

    httpserver.expect_request(uri="/Users/123", method="GET").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "detail": "Resource not found after remove",
            "status": "404",
        },
        status=404,
    )

    httpserver.expect_request(uri="/Users/123", method="DELETE").respond_with_data(
        "", status=204
    )

    results = check_remove_attribute(testing_context, User)

    error_results = [
        r
        for r in results
        if r.status == Status.ERROR
        and "Failed to query resource after remove" in r.reason
    ]
    assert len(error_results) > 0


def test_patch_remove_attribute_not_removed(testing_context):
    """Test PATCH remove when modify result shows attribute was not removed."""
    from unittest.mock import Mock

    mock_client = Mock()
    mock_user = User(id="123", user_name="test@example.com", display_name="persistent")
    mock_client.create.return_value = mock_user

    # Mock modify to return a resource where the attribute is still present
    mock_modified_user = User(
        id="123",
        user_name="test@example.com",
        display_name="persistent",  # Still there after remove attempt
    )
    mock_client.modify.return_value = mock_modified_user
    mock_client.query.return_value = mock_modified_user

    testing_context.client = mock_client

    results = check_remove_attribute(testing_context, User)

    error_results = [
        r
        for r in results
        if r.status == Status.ERROR and "did not remove attribute" in r.reason
    ]
    assert len(error_results) > 0


def test_patch_remove_writeonly_attribute(testing_context):
    """Test PATCH remove when modify result has writeOnly attribute value."""
    from unittest.mock import Mock

    mock_client = Mock()
    mock_user = User(id="123", user_name="test@example.com", password="secret123")
    mock_client.create.return_value = mock_user

    # Mock modify to return a resource with writeOnly attribute still present
    mock_modified_user = User(
        id="123",
        user_name="test@example.com",
        password="secret123",  # writeOnly attribute still present
    )
    mock_client.modify.return_value = mock_modified_user
    mock_client.query.return_value = User(
        id="123",
        user_name="test@example.com",
        # password not returned in query (writeOnly)
    )

    testing_context.client = mock_client

    results = check_remove_attribute(testing_context, User)

    # For writeOnly attributes, should continue to query step
    success_results = [
        r
        for r in results
        if r.status == Status.SUCCESS and "password" in r.data.get("urn", "")
    ]
    assert len(success_results) > 0


def test_patch_not_supported(testing_context):
    """Test PATCH remove returns SKIPPED when PATCH is not supported."""
    from unittest.mock import Mock

    # Mock ServiceProviderConfig with patch.supported = False
    mock_service_provider_config = Mock()
    mock_service_provider_config.patch.supported = False
    testing_context.client.service_provider_config = mock_service_provider_config

    results = check_remove_attribute(testing_context, User)

    assert len(results) == 1
    assert results[0].status == Status.SKIPPED
    assert "PATCH operations not supported by server" in results[0].reason
    assert results[0].resource_type == "User"
