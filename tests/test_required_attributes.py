"""Tests of the checks of the required attributes."""

import pytest
from scim2_client import UnexpectedStatusCodeException
from scim2_models import EnterpriseUser
from scim2_models import Error
from scim2_models import Patch
from scim2_models import Resource
from scim2_models import ScimProvider
from scim2_models import ServiceProviderConfig
from scim2_models import User

from scim2_tester.checkers._required_utils import rejection_status
from scim2_tester.checkers.patch_remove import check_remove_required_attribute
from scim2_tester.checkers.resource_post import (
    object_creation_without_required_attribute,
)
from scim2_tester.checkers.resource_put import (
    object_replacement_without_required_attribute,
)
from scim2_tester.utils import Status

ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"


class Note(Resource):
    __schema__: str = "urn:test:Note"

    text: str | None = None


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


@pytest.mark.parametrize(
    ("response", "status", "reason"),
    [
        (
            Error(status=400, scim_type="invalidValue"),
            Status.SUCCESS,
            "the server answered 400 invalidValue",
        ),
        (
            Error(status=400),
            Status.ACCEPTABLE,
            "the server answered 400 without a scimType",
        ),
        (
            Error(status=400, scim_type="mutability"),
            Status.DEVIATION,
            "the server answered 400 mutability instead of invalidValue",
        ),
        (
            Error(status=422),
            Status.DEVIATION,
            "the server answered 422 instead of 400",
        ),
        (Error(status=500), Status.ERROR, "the server answered 500"),
        (Error(), Status.ERROR, "the server answered None"),
        (
            UnexpectedStatusCodeException(400),
            Status.DEVIATION,
            "the server answered 400 without a SCIM error",
        ),
        (
            UnexpectedStatusCodeException(502),
            Status.ERROR,
            "the server answered 502 without a SCIM error",
        ),
        ({"id": "123"}, Status.ERROR, "the server accepted the request"),
        (None, Status.ERROR, "the server accepted the request"),
    ],
)
def test_rejection_status(response, status, reason):
    """A server answering a request it should reject is graded on its status and scimType."""
    assert rejection_status(response, "invalidValue", Status.ACCEPTABLE) == (
        status,
        reason,
    )


def test_rejection_status_without_scim_type_takes_the_given_status():
    """A 400 without scimType gets the status the check gives it."""
    status, _ = rejection_status(Error(status=400), "mutability", Status.DEVIATION)
    assert status == Status.DEVIATION


def test_creation_without_required_attribute_rejected(httpserver, testing_context):
    """A server rejecting a resource without userName with 400 invalidValue succeeds."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        _error(400, "invalidValue"), status=400, content_type="application/scim+json"
    )

    results = object_creation_without_required_attribute(
        testing_context, User[EnterpriseUser]
    )

    assert len(results) == 1
    assert results[0].status == Status.SUCCESS
    assert results[0].attribute == "userName"
    assert results[0].reason == (
        "POST /Users without userName: the server answered 400 invalidValue"
    )
    request, _ = httpserver.log[0]
    assert "userName" not in request.get_json()


def test_creation_without_required_attribute_accepted(httpserver, testing_context):
    """A server creating a resource without userName fails, and the resource is deleted."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        {"schemas": [User.__schema__], "id": "123"},
        status=201,
        content_type="application/scim+json",
    )
    httpserver.expect_request(uri="/Users/123", method="DELETE").respond_with_data(
        "", status=204
    )

    results = object_creation_without_required_attribute(
        testing_context, User[EnterpriseUser]
    )

    assert results[0].status == Status.ERROR
    assert results[0].reason == (
        "POST /Users without userName: the server accepted the request"
    )
    assert [request.method for request, _ in httpserver.log] == ["POST", "DELETE"]


def test_creation_without_required_attribute_without_scim_error(
    httpserver, testing_context
):
    """A server rejecting the resource without a SCIM error deviates."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_data(
        "Bad request", status=400
    )

    results = object_creation_without_required_attribute(
        testing_context, User[EnterpriseUser]
    )

    assert results[0].status == Status.DEVIATION
    assert results[0].reason == (
        "POST /Users without userName: the server answered 400 without a SCIM error"
    )


def test_creation_without_required_attribute_unreadable_response(
    httpserver, testing_context
):
    """A response that cannot be read gives an error on the attribute."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        _error(400, "invalidValue"), status=400, content_type="text/plain"
    )

    results = object_creation_without_required_attribute(
        testing_context, User[EnterpriseUser]
    )

    assert results[0].status == Status.ERROR
    assert results[0].attribute == "userName"
    assert results[0].reason.startswith("POST /Users without userName failed:")


def test_creation_without_required_attribute_skipped(testing_context):
    """A resource without required attributes has nothing to check."""
    results = object_creation_without_required_attribute(testing_context, Note)

    assert len(results) == 1
    assert results[0].status == Status.SKIPPED
    assert results[0].reason == "No required attribute to check for Note"


def test_replacement_without_required_attribute_rejected(httpserver, testing_context):
    """A server rejecting a replacement without userName with 400 invalidValue succeeds."""
    _setup_user(httpserver)
    httpserver.expect_request(uri="/Users/123", method="PUT").respond_with_json(
        _error(400, "invalidValue"), status=400, content_type="application/scim+json"
    )

    results = object_replacement_without_required_attribute(
        testing_context, User[EnterpriseUser]
    )

    assert len(results) == 1
    assert results[0].status == Status.SUCCESS
    assert results[0].attribute == "userName"
    assert results[0].reason == (
        "PUT /Users/123 without userName: the server answered 400 invalidValue"
    )
    request = next(r for r, _ in httpserver.log if r.method == "PUT")
    assert "userName" not in request.get_json()


def test_replacement_without_required_attribute_accepted(httpserver, testing_context):
    """A server replacing a resource without userName fails."""
    _setup_user(httpserver)
    httpserver.expect_request(uri="/Users/123", method="PUT").respond_with_json(
        USER, status=200, content_type="application/scim+json"
    )

    results = object_replacement_without_required_attribute(
        testing_context, User[EnterpriseUser]
    )

    assert results[0].status == Status.ERROR
    assert results[0].reason == (
        "PUT /Users/123 without userName: the server accepted the request"
    )


def test_remove_required_attribute_rejected(httpserver, testing_context):
    """A server rejecting the removal of userName with 400 mutability succeeds."""
    _setup_user(httpserver)
    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_json(
        _error(400, "mutability"), status=400, content_type="application/scim+json"
    )

    results = check_remove_required_attribute(testing_context, User[EnterpriseUser])

    assert len(results) == 1
    assert results[0].status == Status.SUCCESS
    assert results[0].attribute == "userName"
    assert results[0].reason == (
        "PATCH /Users/123 removing userName: the server answered 400 mutability"
    )
    request = next(r for r, _ in httpserver.log if r.method == "PATCH")
    assert request.get_json()["Operations"] == [{"op": "remove", "path": "userName"}]


@pytest.mark.parametrize("scim_type", ["invalidValue", None])
def test_remove_required_attribute_rejected_without_mutability(
    httpserver, testing_context, scim_type
):
    """A server rejecting the removal of userName without the mutability scimType deviates."""
    _setup_user(httpserver)
    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_json(
        _error(400, scim_type), status=400, content_type="application/scim+json"
    )

    results = check_remove_required_attribute(testing_context, User[EnterpriseUser])

    assert results[0].status == Status.DEVIATION


def test_remove_required_attribute_accepted(httpserver, testing_context):
    """A server removing userName fails."""
    _setup_user(httpserver)
    httpserver.expect_request(uri="/Users/123", method="PATCH").respond_with_data(
        "", status=204
    )

    results = check_remove_required_attribute(testing_context, User[EnterpriseUser])

    assert results[0].status == Status.ERROR
    assert results[0].reason == (
        "PATCH /Users/123 removing userName: the server accepted the request"
    )


def test_remove_required_attribute_patch_not_supported(testing_context):
    """The removal of a required attribute is skipped when PATCH is not supported."""
    provider = testing_context.client.provider
    testing_context.client.provider = ScimProvider(
        provider.models,
        provider.resource_types,
        ServiceProviderConfig(patch=Patch(supported=False)),
    )

    results = check_remove_required_attribute(testing_context, User[EnterpriseUser])

    assert len(results) == 1
    assert results[0].status == Status.SKIPPED
    assert results[0].reason == "PATCH operations not supported by server"
