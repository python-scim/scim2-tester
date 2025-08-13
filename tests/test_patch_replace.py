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

    def patch_handler(request):
        patch_data = json.loads(request.get_data(as_text=True))
        operation = patch_data["Operations"][0]
        path = operation["path"]
        value = operation["value"]

        response_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
            "displayName": "Initial Name",
        }

        # Use build_nested_response to handle all path types
        response_data = build_nested_response(response_data, path, value)

        return Response(
            json.dumps(response_data),
            status=200,
            headers={"Content-Type": "application/scim+json"},
        )

    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_handler(
        patch_handler
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
    from unittest.mock import patch

    with (
        patch(
            "scim2_tester.checkers.patch_replace.iter_all_urns",
            return_value=iter([]),
        ),
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

    def patch_handler(request):
        patch_data = json.loads(request.get_data(as_text=True))
        operation = patch_data["Operations"][0]
        path = operation["path"]
        value = operation["value"]

        response_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
            "name": {
                "givenName": "Initial",
                "familyName": "User",
            },
        }

        # Use build_nested_response to handle all path types
        response_data = build_nested_response(response_data, path, value)

        return Response(
            json.dumps(response_data),
            status=200,
            headers={"Content-Type": "application/scim+json"},
        )

    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_handler(
        patch_handler
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

    def patch_handler(request):
        patch_data = json.loads(request.get_data(as_text=True))
        operation = patch_data["Operations"][0]
        path = operation["path"]
        value = operation["value"]

        response_data = {
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

        # Use build_nested_response to handle all path types including extensions
        response_data = build_nested_response(response_data, path, value)

        return Response(
            json.dumps(response_data),
            status=200,
            headers={"Content-Type": "application/scim+json"},
        )

    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_handler(
        patch_handler
    )

    results = check_replace_attribute(testing_context, User[EnterpriseUser])
    unexpected = [r for r in results if r.status != Status.SUCCESS]
    assert not unexpected
