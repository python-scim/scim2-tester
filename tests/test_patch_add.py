"""Unit tests for PATCH add operation checkers."""

import json

from scim2_models import EnterpriseUser
from scim2_models import User
from werkzeug.wrappers import Response

from scim2_tester.checkers.patch_add import check_add_attribute
from scim2_tester.utils import Status
from tests.utils import build_nested_response


def test_successful_add(httpserver, testing_context):
    """Test successful PATCH add returns SUCCESS in CheckResult."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
        },
        status=201,
    )

    # Track the state of the resource
    resource_state = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": "123",
        "userName": "test@example.com",
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
        value = operation["value"]

        # Update resource state with the patched value
        resource_state = build_nested_response(resource_state, path, value)

        return Response(
            json.dumps(resource_state),
            status=200,
            headers={"Content-Type": "application/scim+json"},
        )

    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_handler(
        update_patch_handler
    )
    httpserver.expect_request(uri="/Users/123", method="GET").respond_with_handler(
        get_handler
    )

    testing_context.conf.raise_exceptions = True
    results = check_add_attribute(testing_context, User)
    unexpected = [r for r in results if r.status != Status.SUCCESS]
    assert not unexpected


def test_server_error(httpserver, testing_context):
    """Test server error returns ERROR in CheckResult."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
        },
        status=201,
    )

    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "detail": "Internal server error",
            "status": "500",
        },
        status=500,
    )

    results = check_add_attribute(testing_context, User)
    # Filter out write_only fields which always return SUCCESS since they can't be verified
    non_writeonly_results = [
        r for r in results if "password" not in r.data.get("urn", "").lower()
    ]
    assert all(r.status == Status.ERROR for r in non_writeonly_results)
    assert len(non_writeonly_results) > 0, (
        "Should have non-write_only fields that failed"
    )


def test_attribute_not_added(httpserver, testing_context):
    """Test attribute not added returns ERROR in CheckResult."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
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

    results = check_add_attribute(testing_context, User)
    # Filter out write_only fields which always return SUCCESS since they can't be verified
    non_writeonly_results = [
        r
        for r in results
        if "password"
        not in r.data.get("urn", "").lower()  # password is the main write_only field
    ]
    assert all(r.status == Status.ERROR for r in non_writeonly_results)
    # Verify that we have both types of results
    assert len(non_writeonly_results) > 0, (
        "Should have non-write_only fields that failed"
    )


def test_no_patchable_attributes(testing_context):
    """Test no patchable attributes returns SKIPPED."""
    from unittest.mock import patch

    with (
        patch(
            "scim2_tester.checkers.patch_add.iter_all_urns",
            return_value=iter([]),
        ),
    ):
        results = check_add_attribute(testing_context, User)
        assert len(results) == 1
        unexpected = [r for r in results if r.status != Status.SKIPPED]
    assert not unexpected


def test_complex_successful_add(httpserver, testing_context):
    """Test successful PATCH add for complex attributes returns SUCCESS."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
        },
        status=201,
    )

    # Track the state of the resource
    resource_state = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": "123",
        "userName": "test@example.com",
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

    results = check_add_attribute(testing_context, User)
    unexpected = [r for r in results if r.status != Status.SUCCESS]
    assert not unexpected


def test_complex_server_error(httpserver, testing_context):
    """Test server error for complex attributes returns ERROR."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
        },
        status=201,
    )

    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "detail": "Complex attribute error",
            "status": "500",
        },
        status=500,
    )

    results = check_add_attribute(testing_context, User)
    # Filter out write_only fields which always return SUCCESS since they can't be verified
    non_writeonly_results = [
        r for r in results if "password" not in r.data.get("urn", "").lower()
    ]
    assert all(r.status == Status.ERROR for r in non_writeonly_results)
    assert len(non_writeonly_results) > 0, (
        "Should have non-write_only fields that failed"
    )


def test_complex_attribute_not_added(httpserver, testing_context):
    """Test complex attribute not added returns ERROR."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
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

    results = check_add_attribute(testing_context, User)
    # Filter out write_only fields which always return SUCCESS since they can't be verified
    non_writeonly_results = [
        r for r in results if "password" not in r.data.get("urn", "").lower()
    ]
    assert all(r.status == Status.ERROR for r in non_writeonly_results)
    assert len(non_writeonly_results) > 0, (
        "Should have non-write_only fields that failed"
    )


def test_no_complex_patchable_attributes(testing_context):
    """Test no complex patchable attributes returns SKIPPED."""
    from unittest.mock import patch

    with (
        patch(
            "scim2_tester.checkers.patch_add.iter_all_urns",
            return_value=iter([]),
        ),
    ):
        results = check_add_attribute(testing_context, User)
        assert len(results) == 1
        unexpected = [r for r in results if r.status != Status.SKIPPED]
    assert not unexpected


def test_user_with_enterprise_extension(httpserver, testing_context):
    """Test PATCH add with User[EnterpriseUser] extension support."""
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

    results = check_add_attribute(testing_context, User[EnterpriseUser])
    unexpected = [r for r in results if r.status != Status.SUCCESS]
    assert not unexpected


def test_patch_add_modify_result_incorrect_value(testing_context):
    """Test PATCH add when modify result returns incorrect value."""
    from unittest.mock import Mock

    mock_client = Mock()
    mock_user = User(id="123", user_name="test@example.com")
    mock_client.create.return_value = mock_user

    # Mock modify to return a different value than expected
    mock_modified_user = User(
        id="123", user_name="test@example.com", display_name="wrong_value"
    )
    mock_client.modify.return_value = mock_modified_user
    mock_client.query.return_value = mock_modified_user

    testing_context.client = mock_client

    results = check_add_attribute(testing_context, User)

    error_results = [
        r for r in results if r.status == Status.ERROR and "incorrect value" in r.reason
    ]
    assert len(error_results) > 0


def test_patch_add_query_failure_after_patch(httpserver, testing_context):
    """Test PATCH add when query fails after successful patch."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
        },
        status=201,
    )

    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
            "displayName": "test_display",
        },
        status=200,
    )

    httpserver.expect_request(uri="/Users/123", method="GET").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test@example.com",
            # displayName missing - attribute not actually added
        },
        status=200,
    )

    results = check_add_attribute(testing_context, User)

    error_results = [
        r
        for r in results
        if r.status == Status.ERROR
        and "was not added or has incorrect value" in r.reason
    ]
    assert len(error_results) > 0
