"""Tests of the checks of the request bodies that are not valid JSON."""

from scim2_models import EnterpriseUser
from scim2_models import User

from scim2_tester.checkers.resource_post import object_creation_with_invalid_syntax
from scim2_tester.checkers.resource_put import object_replacement_with_invalid_syntax
from scim2_tester.utils import Status

ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"

USER = {
    "schemas": [User.__schema__],
    "id": "123",
    "userName": "bjensen@example.com",
}


def _error(status, scim_type=None):
    payload = {"schemas": [ERROR_SCHEMA], "status": str(status), "detail": "Rejected"}
    if scim_type:
        payload["scimType"] = scim_type
    return payload


def _setup_user(httpserver):
    """Register the creation and the deletion of a user."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        USER, status=201, content_type="application/scim+json"
    )
    httpserver.expect_request(uri="/Users/123", method="DELETE").respond_with_data(
        "", status=204
    )


def test_creation_with_invalid_syntax_rejected(httpserver, testing_context):
    """A server rejecting a body that is not JSON with 400 invalidSyntax succeeds."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        _error(400, "invalidSyntax"), status=400, content_type="application/scim+json"
    )

    results = object_creation_with_invalid_syntax(testing_context, User[EnterpriseUser])

    assert len(results) == 1
    assert results[0].status == Status.SUCCESS
    assert results[0].reason == (
        "POST /Users with invalid JSON: the server answered 400 invalidSyntax"
    )
    request, _ = httpserver.log[0]
    assert request.get_data() == b'{"schemas": ['
    assert request.headers["Content-Type"] == "application/scim+json"


def test_creation_with_invalid_syntax_rejected_without_scim_type(
    httpserver, testing_context
):
    """A server rejecting a body that is not JSON with a 400 without scimType is acceptable."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        _error(400), status=400, content_type="application/scim+json"
    )

    results = object_creation_with_invalid_syntax(testing_context, User[EnterpriseUser])

    assert results[0].status == Status.ACCEPTABLE


def test_creation_with_invalid_syntax_rejected_with_another_scim_type(
    httpserver, testing_context
):
    """A server rejecting a body that is not JSON with 400 invalidValue deviates."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        _error(400, "invalidValue"), status=400, content_type="application/scim+json"
    )

    results = object_creation_with_invalid_syntax(testing_context, User[EnterpriseUser])

    assert results[0].status == Status.DEVIATION
    assert results[0].reason == (
        "POST /Users with invalid JSON: "
        "the server answered 400 invalidValue instead of invalidSyntax"
    )


def test_creation_with_invalid_syntax_accepted(httpserver, testing_context):
    """A server creating a resource from a body that is not JSON fails, and the resource is deleted."""
    _setup_user(httpserver)

    results = object_creation_with_invalid_syntax(testing_context, User[EnterpriseUser])

    assert results[0].status == Status.ERROR
    assert results[0].reason == (
        "POST /Users with invalid JSON: the server accepted the request"
    )
    assert [request.method for request, _ in httpserver.log] == ["POST", "DELETE"]


def test_creation_with_invalid_syntax_server_error(httpserver, testing_context):
    """A server answering 500 to a body that is not JSON fails."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        _error(500), status=500, content_type="application/scim+json"
    )

    results = object_creation_with_invalid_syntax(testing_context, User[EnterpriseUser])

    assert results[0].status == Status.ERROR
    assert results[0].reason == (
        "POST /Users with invalid JSON: the server answered 500"
    )


def test_replacement_with_invalid_syntax_rejected(httpserver, testing_context):
    """A server rejecting a replacement that is not JSON with 400 invalidSyntax succeeds."""
    _setup_user(httpserver)
    httpserver.expect_request(uri="/Users/123", method="PUT").respond_with_json(
        _error(400, "invalidSyntax"), status=400, content_type="application/scim+json"
    )

    results = object_replacement_with_invalid_syntax(
        testing_context, User[EnterpriseUser]
    )

    assert len(results) == 1
    assert results[0].status == Status.SUCCESS
    assert results[0].reason == (
        "PUT /Users/123 with invalid JSON: the server answered 400 invalidSyntax"
    )
    request = next(r for r, _ in httpserver.log if r.method == "PUT")
    assert request.get_data() == b'{"schemas": ['
    assert request.headers["Content-Type"] == "application/scim+json"


def test_replacement_with_invalid_syntax_accepted(httpserver, testing_context):
    """A server replacing a resource with a body that is not JSON fails."""
    _setup_user(httpserver)
    httpserver.expect_request(uri="/Users/123", method="PUT").respond_with_json(
        USER, status=200, content_type="application/scim+json"
    )

    results = object_replacement_with_invalid_syntax(
        testing_context, User[EnterpriseUser]
    )

    assert results[0].status == Status.ERROR
    assert results[0].reason == (
        "PUT /Users/123 with invalid JSON: the server accepted the request"
    )
