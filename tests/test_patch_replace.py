"""Unit tests for PATCH replace operation checkers."""

import json

from scim2_models import EnterpriseUser
from scim2_models import User
from werkzeug.wrappers import Response

from scim2_tester.checkers.patch_replace import check_replace_attribute
from scim2_tester.utils import Status
from tests.utils import build_nested_response


def test_successful_replace(httpserver, testing_context):
    """Test successful PATCH replace returns SUCCESS in CheckResult."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
            "displayName": "Initial Name",
        },
        status=201,
    )

    # Track the state of the resource
    resource_state = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": "123",
        "userName": "test@example.com",
        "displayName": "Initial Name",
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
        value = operation["value"]

        # Update resource state with the patched value
        resource_state = build_nested_response(resource_state, path, value)

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

    results = check_replace_attribute(testing_context, User)
    unexpected = [r for r in results if r.status != Status.SUCCESS]
    assert not unexpected


def test_replace_server_error(httpserver, testing_context):
    """Test PATCH replace server error returns ERROR in CheckResult."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
            "displayName": "Initial Name",
        },
        status=201,
    )

    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "status": "500",
            "detail": "Internal Server Error",
        },
        status=500,
    )

    results = check_replace_attribute(testing_context, User)
    unexpected = [r for r in results if r.status != Status.ERROR]
    assert not unexpected


def test_replace_attribute_not_updated(httpserver, testing_context):
    """Test PATCH replace where attribute is not actually updated returns ERROR."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
            "displayName": "Initial Name",
        },
        status=201,
    )

    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
            "displayName": "Initial Name",
        },
        status=200,
    )

    results = check_replace_attribute(testing_context, User)
    # Filter out write_only fields which always return SUCCESS since they can't be verified
    non_writeonly_results = [
        r for r in results if "password" not in r.data.get("urn", "").lower()
    ]
    assert all(r.status == Status.ERROR for r in non_writeonly_results)
    assert len(non_writeonly_results) > 0, (
        "Should have non-write_only fields that failed"
    )


def test_no_replaceable_attributes(testing_context):
    """Test no replaceable attributes returns SKIPPED."""
    from unittest.mock import MagicMock
    from unittest.mock import patch

    mock_bound_path = MagicMock()
    mock_bound_path.iter_paths.return_value = iter([])

    with patch(
        "scim2_tester.checkers.patch_replace.Path.__class_getitem__",
        return_value=mock_bound_path,
    ):
        results = check_replace_attribute(testing_context, User)
        unexpected = [r for r in results if r.status != Status.SKIPPED]
    assert not unexpected


def test_complex_successful_replace(httpserver, testing_context):
    """Test successful PATCH replace for complex attributes returns SUCCESS."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
            "name": {
                "givenName": "Initial",
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
            "givenName": "Initial",
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
        value = operation["value"]

        # Update resource state with the patched value
        resource_state = build_nested_response(resource_state, path, value)

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

    results = check_replace_attribute(testing_context, User)
    unexpected = [r for r in results if r.status != Status.SUCCESS]
    assert not unexpected


def test_user_with_enterprise_extension_replace(httpserver, testing_context):
    """Test PATCH replace with User[EnterpriseUser] extension support."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": [
                "urn:ietf:params:scim:schemas:core:2.0:User",
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            ],
            "id": "123",
            "userName": "test@example.com",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                "employeeNumber": "EMP001"
            },
        },
        status=201,
    )

    # Track the state of the resource
    resource_state = {
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
        "id": "123",
        "userName": "test@example.com",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
            "employeeNumber": "EMP001"
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
        value = operation["value"]

        # Update resource state with the patched value
        resource_state = build_nested_response(resource_state, path, value)

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

    results = check_replace_attribute(testing_context, User[EnterpriseUser])
    unexpected = [r for r in results if r.status != Status.SUCCESS]
    assert not unexpected


def test_patch_replace_attribute_not_replaced(httpserver, testing_context):
    """Test PATCH replace when attribute is not actually replaced."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
            "displayName": "original_display",
        },
        status=201,
    )

    original_state = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": "123",
        "userName": "test@example.com",
        "displayName": "original_display",
    }

    def patch_handler(request):
        patch_data = json.loads(request.get_data(as_text=True))
        operation = patch_data["Operations"][0]

        if operation["path"] == "displayName" and operation["op"] == "replace":
            return Response(
                json.dumps(original_state),
                status=200,
                headers={"Content-Type": "application/scim+json"},
            )

        return Response(
            json.dumps(original_state),
            status=200,
            headers={"Content-Type": "application/scim+json"},
        )

    def get_handler(request):
        return Response(
            json.dumps(original_state),
            status=200,
            headers={"Content-Type": "application/scim+json"},
        )

    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_handler(
        patch_handler
    )
    httpserver.expect_request(uri="/Users/123", method="GET").respond_with_handler(
        get_handler
    )

    results = check_replace_attribute(testing_context, User)

    error_results = [
        r
        for r in results
        if r.status == Status.ERROR
        and (
            "was not replaced" in r.reason
            or "PATCH modify() returned unexpected value" in r.reason
        )
        and hasattr(r, "data")
        and r.data
        and r.data.get("urn") == "displayName"
    ]
    assert len(error_results) > 0


def test_patch_replace_get_returns_different_value(httpserver, testing_context):
    """Test PATCH replace when GET returns a different value than what was patched."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
            "displayName": "original_display",
        },
        status=201,
    )

    def patch_handler(request):
        patch_data = json.loads(request.get_data(as_text=True))
        operation = patch_data["Operations"][0]

        if operation["path"] == "displayName" and operation["op"] == "replace":
            return Response(
                json.dumps(
                    {
                        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                        "id": "123",
                        "userName": "test@example.com",
                        "displayName": operation["value"],
                    }
                ),
                status=200,
                headers={"Content-Type": "application/scim+json"},
            )

        return Response(
            json.dumps(
                {
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                    "id": "123",
                    "userName": "test@example.com",
                }
            ),
            status=200,
            headers={"Content-Type": "application/scim+json"},
        )

    def get_handler(request):
        return Response(
            json.dumps(
                {
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                    "id": "123",
                    "userName": "test@example.com",
                    "displayName": "original_display",
                }
            ),
            status=200,
            headers={"Content-Type": "application/scim+json"},
        )

    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_handler(
        patch_handler
    )
    httpserver.expect_request(uri="/Users/123", method="GET").respond_with_handler(
        get_handler
    )

    results = check_replace_attribute(testing_context, User)

    error_results = [
        r
        for r in results
        if r.status == Status.ERROR
        and "was not replaced or has unexpected value" in r.reason
        and hasattr(r, "data")
        and r.data
        and r.data.get("urn") == "displayName"
    ]
    assert len(error_results) > 0


def test_patch_replace_modify_returns_none(httpserver, testing_context):
    """Test PATCH replace when modify returns None (no content)."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
            "displayName": "original_display",
        },
        status=201,
    )

    saved_values = {}

    def patch_handler(request):
        patch_data = json.loads(request.get_data(as_text=True))
        operation = patch_data["Operations"][0]
        path = operation.get("path", "")
        value = operation.get("value")

        saved_values[path] = value

        return Response(
            "",
            status=204,
            headers={"Content-Type": "application/scim+json"},
        )

    def get_handler(request):
        response_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
        }

        for path, value in saved_values.items():
            if path == "displayName":
                response_data["displayName"] = value
            elif path == "title":
                response_data["title"] = value

        return Response(
            json.dumps(response_data),
            status=200,
            headers={"Content-Type": "application/scim+json"},
        )

    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_handler(
        patch_handler
    )
    httpserver.expect_request(uri="/Users/123", method="GET").respond_with_handler(
        get_handler
    )

    results = check_replace_attribute(testing_context, User)

    success_results = [r for r in results if r.status == Status.SUCCESS]
    assert len(success_results) > 0


def test_patch_not_supported(testing_context):
    """Test PATCH replace returns SKIPPED when PATCH is not supported."""
    from unittest.mock import Mock

    # Mock ServiceProviderConfig with patch.supported = False
    mock_service_provider_config = Mock()
    mock_service_provider_config.patch.supported = False
    testing_context.client.service_provider_config = mock_service_provider_config

    results = check_replace_attribute(testing_context, User)

    assert len(results) == 1
    assert results[0].status == Status.SKIPPED
    assert "PATCH operations not supported by server" in results[0].reason
    assert results[0].resource_type == "User"
