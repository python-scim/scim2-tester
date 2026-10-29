"""Unit tests for attribute filtering compliance checkers."""

import json
from typing import Annotated
from unittest.mock import patch

import pytest
from scim2_models import Mutability
from scim2_models import Resource
from scim2_models import Returned
from scim2_models import User
from werkzeug.wrappers import Response

from scim2_tester.checkers.resource_query_attributes import ATTRIBUTES
from scim2_tester.checkers.resource_query_attributes import EXCLUDED_ATTRIBUTES
from scim2_tester.checkers.resource_query_attributes import _attribute_problems
from scim2_tester.checkers.resource_query_attributes import _candidate_attributes
from scim2_tester.checkers.resource_query_attributes import _is_testable
from scim2_tester.checkers.resource_query_attributes import _returned_attributes
from scim2_tester.checkers.resource_query_attributes import object_list_with_attributes
from scim2_tester.checkers.resource_query_attributes import (
    object_list_with_excluded_attributes,
)
from scim2_tester.checkers.resource_query_attributes import object_query_with_attributes
from scim2_tester.checkers.resource_query_attributes import (
    object_query_with_excluded_attributes,
)
from scim2_tester.checkers.resource_query_attributes import search_with_attributes
from scim2_tester.checkers.resource_query_attributes import (
    search_with_excluded_attributes,
)
from scim2_tester.utils import Status

USER_PAYLOAD = {
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    "id": "123",
    "userName": "bjensen@example.com",
    "displayName": "Barbara Jensen",
    "nickName": "Babs",
    "externalId": "ext-123",
    "name": {"givenName": "Barbara", "familyName": "Jensen"},
}

CHECKED_ATTRIBUTES = {
    "externalId",
    "userName",
    "name",
    "displayName",
    "nickName",
    "password",
}


def _setup_creation_and_deletion(httpserver):
    """Register POST /Users and DELETE /Users/123 handlers."""
    httpserver.expect_request(uri="/Users", method="POST").respond_with_json(
        USER_PAYLOAD,
        status=201,
    )
    httpserver.expect_request(uri="/Users/123", method="DELETE").respond_with_data(
        "", status=204
    )


def _filter_payload(payload, attributes=None, excluded_attributes=None):
    """Apply attribute filtering to a payload dict, as a compliant server does."""
    result = dict(payload)
    if attributes:
        keep = set(attributes) | {"schemas", "id"}
        result = {k: v for k, v in result.items() if k in keep}
    if excluded_attributes:
        drop = set(excluded_attributes)
        result = {k: v for k, v in result.items() if k not in drop}
    return result


def _scim_response(payload, status=200):
    return Response(
        json.dumps(payload),
        status=status,
        headers={"Content-Type": "application/scim+json"},
    )


def _list_response(resources):
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(resources),
        "Resources": resources,
    }


def _query_parameters(request):
    """Return the attributes and excludedAttributes of a GET or a search request."""
    if request.method == "POST":
        body = json.loads(request.get_data(as_text=True)) if request.data else {}
        return body.get("attributes"), body.get("excludedAttributes")

    def split(name):
        value = request.args.get(name)
        return [v.strip() for v in value.split(",")] if value else None

    return split("attributes"), split("excludedAttributes")


def _resource_handler(server):
    """Return a handler answering the resource as the server function does."""

    def handler(request):
        attributes, excluded = _query_parameters(request)
        return _scim_response(server(attributes, excluded))

    return handler


def _list_handler(server):
    """Return a handler answering a list of the resource as the server function does."""

    def handler(request):
        attributes, excluded = _query_parameters(request)
        return _scim_response(_list_response([server(attributes, excluded)]))

    return handler


def _compliant(attributes, excluded):
    return _filter_payload(USER_PAYLOAD, attributes, excluded)


def _ignoring(attributes, excluded):
    return USER_PAYLOAD


def _expect_get(httpserver, server):
    httpserver.expect_request(uri="/Users/123", method="GET").respond_with_handler(
        _resource_handler(server)
    )


def _by_attribute(results):
    return {r.attribute: r for r in results}


class Badge(Resource):
    __schema__: str = "urn:test:Badge"

    label: Annotated[str | None, Returned.default] = None
    color: Annotated[str | None, Returned.default] = None
    code: Annotated[str | None, Returned.request] = None
    secret: Annotated[str | None, Returned.never] = None
    serial: Annotated[str | None, Returned.always] = None


BADGE_ATTRIBUTES = {
    str(path): (path, returned, mutability)
    for path, returned, mutability in _candidate_attributes(Badge)
}


@pytest.mark.parametrize(
    ("parameter", "attribute", "expected"),
    [
        (ATTRIBUTES, "label", {"label", "serial"}),
        (ATTRIBUTES, "code", {"code", "serial"}),
        (ATTRIBUTES, "secret", {"serial"}),
        (ATTRIBUTES, "serial", {"serial"}),
        (EXCLUDED_ATTRIBUTES, "label", {"externalId", "color", "serial"}),
        (EXCLUDED_ATTRIBUTES, "code", {"externalId", "label", "color", "serial"}),
        (EXCLUDED_ATTRIBUTES, "secret", {"externalId", "label", "color", "serial"}),
        (EXCLUDED_ATTRIBUTES, "serial", {"externalId", "label", "color", "serial"}),
    ],
)
def test_returned_attributes_follow_the_returned_annotation(
    parameter, attribute, expected
):
    """A response keeps the attributes given by their returned annotation and the parameter."""
    path = BADGE_ATTRIBUTES[attribute][0]
    returned = _returned_attributes(Badge, parameter, path)
    assert returned & set(BADGE_ATTRIBUTES) == expected


def test_never_returned_attributes_are_always_checked():
    """An attribute never returned is checked even without a value in the response."""
    assert _is_testable(*BADGE_ATTRIBUTES["secret"], Badge())


def test_attributes_returned_on_request_are_checked_when_writable():
    """An attribute returned on request is checked when the check could give it a value."""
    path, returned, _ = BADGE_ATTRIBUTES["code"]
    assert _is_testable(path, returned, Mutability.read_write, Badge())
    assert not _is_testable(path, returned, Mutability.read_only, Badge())


def test_attributes_returned_by_default_are_checked_when_the_server_has_a_value():
    """An attribute returned by default is checked when the response without parameters has it."""
    assert not _is_testable(*BADGE_ATTRIBUTES["label"], Badge())
    assert _is_testable(*BADGE_ATTRIBUTES["label"], Badge(label="Gold"))


def test_attribute_returned_on_request_must_be_in_the_response_when_requested():
    """An attribute returned on request is missing when requested and not returned."""
    path = BADGE_ATTRIBUTES["code"][0]
    returned = _returned_attributes(Badge, ATTRIBUTES, path)

    missing, unexpected = _attribute_problems(
        list(BADGE_ATTRIBUTES.values()), Badge(), Badge(), returned, "code"
    )

    assert missing == ["code"]
    assert unexpected == []


def test_attribute_returned_on_request_must_not_be_in_the_response_otherwise():
    """An attribute returned on request is unexpected when another one is requested."""
    path = BADGE_ATTRIBUTES["label"][0]
    returned = _returned_attributes(Badge, ATTRIBUTES, path)

    missing, unexpected = _attribute_problems(
        list(BADGE_ATTRIBUTES.values()),
        Badge(label="Gold"),
        Badge(label="Gold", code="1234"),
        returned,
        "label",
    )

    assert missing == []
    assert unexpected == ["code"]


def test_object_query_with_attributes_compliant_server(httpserver, testing_context):
    """GET /Users/{id} with attributes gives one success per attribute on a compliant server."""
    _setup_creation_and_deletion(httpserver)
    _expect_get(httpserver, _compliant)

    results = object_query_with_attributes(testing_context, User)

    assert {r.attribute for r in results} == CHECKED_ATTRIBUTES
    assert all(r.status == Status.SUCCESS for r in results)


def test_object_query_with_excluded_attributes_compliant_server(
    httpserver, testing_context
):
    """GET /Users/{id} with excludedAttributes gives one success per attribute on a compliant server."""
    _setup_creation_and_deletion(httpserver)
    _expect_get(httpserver, _compliant)

    results = object_query_with_excluded_attributes(testing_context, User)

    assert {r.attribute for r in results} == CHECKED_ATTRIBUTES
    assert all(r.status == Status.SUCCESS for r in results)


def test_object_query_with_attributes_server_ignores_the_parameter(
    httpserver, testing_context
):
    """A server returning all the attributes despite attributes gives the unexpected ones."""
    _setup_creation_and_deletion(httpserver)
    _expect_get(httpserver, _ignoring)

    results = _by_attribute(object_query_with_attributes(testing_context, User))

    assert results["nickName"].status == Status.ERROR
    assert results["nickName"].reason == (
        "GET /Resource/{id} with attributes=nickName: "
        "unexpected externalId, userName, name, displayName"
    )


def test_object_query_with_excluded_attributes_server_ignores_the_parameter(
    httpserver, testing_context
):
    """A server returning an excluded attribute gives it as unexpected."""
    _setup_creation_and_deletion(httpserver)
    _expect_get(httpserver, _ignoring)

    results = _by_attribute(
        object_query_with_excluded_attributes(testing_context, User)
    )

    assert results["nickName"].status == Status.ERROR
    assert results["nickName"].reason == (
        "GET /Resource/{id} with excludedAttributes=nickName: unexpected nickName"
    )
    assert results["password"].status == Status.SUCCESS


def test_object_query_with_excluded_attributes_server_drops_other_attributes(
    httpserver, testing_context
):
    """A server dropping attributes that were not excluded gives them as missing."""
    _setup_creation_and_deletion(httpserver)

    def server(attributes, excluded):
        if excluded:
            return {"schemas": USER_PAYLOAD["schemas"], "id": "123"}
        return USER_PAYLOAD

    _expect_get(httpserver, server)

    results = _by_attribute(
        object_query_with_excluded_attributes(testing_context, User)
    )

    assert results["nickName"].status == Status.ERROR
    assert results["nickName"].reason == (
        "GET /Resource/{id} with excludedAttributes=nickName: "
        "missing externalId, userName, name, displayName"
    )


def test_object_query_with_attributes_server_returns_a_never_returned_attribute(
    httpserver, testing_context
):
    """A server returning the password when it is requested gives it as unexpected."""
    _setup_creation_and_deletion(httpserver)

    def server(attributes, excluded):
        if attributes == ["password"]:
            return {**_compliant(attributes, excluded), "password": "secret"}
        return _compliant(attributes, excluded)

    _expect_get(httpserver, server)

    results = _by_attribute(object_query_with_attributes(testing_context, User))

    assert results["password"].status == Status.ERROR
    assert results["password"].reason.startswith(
        "GET /Resource/{id} with attributes=password failed:"
    )
    assert "returnability 'never'" in results["password"].reason
    assert results["password"].data["password"] == "secret"
    assert results["nickName"].status == Status.SUCCESS


def test_object_query_with_attributes_server_drops_the_id(httpserver, testing_context):
    """A server dropping the id, which is always returned, gives an error."""
    _setup_creation_and_deletion(httpserver)

    def server(attributes, excluded):
        payload = _compliant(attributes, excluded)
        if attributes:
            del payload["id"]
        return payload

    _expect_get(httpserver, server)

    results = _by_attribute(object_query_with_attributes(testing_context, User))

    assert results["nickName"].status == Status.ERROR
    assert "returnability 'always'" in results["nickName"].reason


def test_object_query_with_attributes_failure_on_one_attribute(
    httpserver, testing_context
):
    """A request failing on one attribute gives an error for this attribute, and the others are checked."""
    _setup_creation_and_deletion(httpserver)

    def handler(request):
        attributes, excluded = _query_parameters(request)
        if attributes == ["nickName"]:
            return _scim_response(
                {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                    "status": "500",
                    "detail": "Something went wrong",
                },
                status=500,
            )
        return _scim_response(_compliant(attributes, excluded))

    httpserver.expect_request(uri="/Users/123", method="GET").respond_with_handler(
        handler
    )

    results = _by_attribute(object_query_with_attributes(testing_context, User))

    assert set(results) == CHECKED_ATTRIBUTES
    assert results["nickName"].status == Status.ERROR
    assert results["nickName"].reason.startswith(
        "GET /Resource/{id} with attributes=nickName failed:"
    )
    assert results["nickName"].data["detail"] == "Something went wrong"
    assert results["userName"].status == Status.SUCCESS


def test_object_query_with_attributes_invalid_response(httpserver, testing_context):
    """A response that is not a valid resource gives an error for the attribute."""
    _setup_creation_and_deletion(httpserver)

    def server(attributes, excluded):
        if attributes == ["nickName"]:
            return {**_compliant(attributes, excluded), "active": "maybe"}
        return _compliant(attributes, excluded)

    _expect_get(httpserver, server)

    results = _by_attribute(object_query_with_attributes(testing_context, User))

    assert results["nickName"].status == Status.ERROR
    assert "active" in results["nickName"].reason


def test_object_query_skipped_when_no_attribute_to_check(httpserver, testing_context):
    """GET /Users/{id} is skipped when the resource has no attribute to check."""
    _setup_creation_and_deletion(httpserver)
    _expect_get(httpserver, _compliant)

    with patch(
        "scim2_tester.checkers.resource_query_attributes._candidate_attributes",
        return_value=[],
    ):
        results = object_query_with_attributes(testing_context, User)

    assert len(results) == 1
    assert results[0].status == Status.SKIPPED
    assert results[0].reason == "No attribute of User to check attributes on"


def test_object_list_with_attributes_compliant_server(httpserver, testing_context):
    """GET /Users with attributes gives one success per attribute on a compliant server."""
    _setup_creation_and_deletion(httpserver)
    httpserver.expect_request(uri="/Users", method="GET").respond_with_handler(
        _list_handler(_compliant)
    )

    results = object_list_with_attributes(testing_context, User)

    assert {r.attribute for r in results} == CHECKED_ATTRIBUTES
    assert all(r.status == Status.SUCCESS for r in results)


def test_object_list_with_excluded_attributes_compliant_server(
    httpserver, testing_context
):
    """GET /Users with excludedAttributes gives one success per attribute on a compliant server."""
    _setup_creation_and_deletion(httpserver)
    httpserver.expect_request(uri="/Users", method="GET").respond_with_handler(
        _list_handler(_compliant)
    )

    results = object_list_with_excluded_attributes(testing_context, User)

    assert {r.attribute for r in results} == CHECKED_ATTRIBUTES
    assert all(r.status == Status.SUCCESS for r in results)


def test_object_list_without_the_created_resource(httpserver, testing_context):
    """GET /Users gives one error when the created resource is not in the list."""
    _setup_creation_and_deletion(httpserver)
    httpserver.expect_request(uri="/Users", method="GET").respond_with_json(
        _list_response([]), content_type="application/scim+json"
    )

    results = object_list_with_attributes(testing_context, User)

    assert len(results) == 1
    assert results[0].status == Status.ERROR
    assert results[0].attribute is None
    assert results[0].reason == "GET /Resource: the User 123 is not in the response"


def test_object_list_with_attributes_loses_the_resource(httpserver, testing_context):
    """GET /Users gives an error per attribute when the resource is only listed without parameters."""
    _setup_creation_and_deletion(httpserver)

    def handler(request):
        attributes, excluded = _query_parameters(request)
        resources = [] if attributes else [USER_PAYLOAD]
        return _scim_response(_list_response(resources))

    httpserver.expect_request(uri="/Users", method="GET").respond_with_handler(handler)

    results = _by_attribute(object_list_with_attributes(testing_context, User))

    assert results["nickName"].status == Status.ERROR
    assert results["nickName"].reason == (
        "GET /Resource with attributes=nickName: the User 123 is not in the response"
    )


def test_search_with_attributes_compliant_server(httpserver, testing_context):
    """POST /.search with attributes gives one success per attribute on a compliant server."""
    _setup_creation_and_deletion(httpserver)
    httpserver.expect_request(uri="/.search", method="POST").respond_with_handler(
        _list_handler(_compliant)
    )

    results = search_with_attributes(testing_context, User)

    assert {r.attribute for r in results} == CHECKED_ATTRIBUTES
    assert all(r.status == Status.SUCCESS for r in results)


def test_search_with_excluded_attributes_compliant_server(httpserver, testing_context):
    """POST /.search with excludedAttributes gives one success per attribute on a compliant server."""
    _setup_creation_and_deletion(httpserver)
    httpserver.expect_request(uri="/.search", method="POST").respond_with_handler(
        _list_handler(_compliant)
    )

    results = search_with_excluded_attributes(testing_context, User)

    assert {r.attribute for r in results} == CHECKED_ATTRIBUTES
    assert all(r.status == Status.SUCCESS for r in results)


def test_search_with_excluded_attributes_server_ignores_the_parameter(
    httpserver, testing_context
):
    """A search returning an excluded attribute gives it as unexpected."""
    _setup_creation_and_deletion(httpserver)
    httpserver.expect_request(uri="/.search", method="POST").respond_with_handler(
        _list_handler(_ignoring)
    )

    results = _by_attribute(search_with_excluded_attributes(testing_context, User))

    assert results["displayName"].status == Status.ERROR
    assert results["displayName"].reason == (
        "POST /.search with excludedAttributes=displayName: unexpected displayName"
    )


@pytest.mark.parametrize(
    "check", [search_with_attributes, search_with_excluded_attributes]
)
def test_search_skipped_when_the_server_does_not_search_at_the_root(
    httpserver, testing_context, check
):
    """POST /.search is skipped when the server answers 501 Not Implemented."""
    _setup_creation_and_deletion(httpserver)
    httpserver.expect_request(uri="/.search", method="POST").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "status": "501",
            "detail": "Searching several resource types at once is not supported",
        },
        status=501,
        content_type="application/scim+json",
    )

    results = check(testing_context, User)

    assert len(results) == 1
    assert results[0].status == Status.SKIPPED
    assert "several resource types" in results[0].reason


def _respond_to_search_with(httpserver, resources):
    httpserver.expect_request(uri="/.search", method="POST").respond_with_json(
        _list_response(resources), content_type="application/scim+json"
    )


def test_search_returning_a_resource_without_schemas_is_summed_up(
    httpserver, testing_context
):
    """A resource without schemas in a search at the root is reported in one sentence."""
    _setup_creation_and_deletion(httpserver)
    resource = {key: value for key, value in USER_PAYLOAD.items() if key != "schemas"}
    _respond_to_search_with(httpserver, [resource])

    results = search_with_attributes(testing_context, User)

    assert len(results) == 1
    assert results[0].status == Status.ERROR
    assert results[0].reason == (
        "The server returned 1 resource without the schema of a known resource "
        "type (RFC 7643 §3)"
    )


def test_search_returning_resources_without_schemas_is_summed_up(
    httpserver, testing_context
):
    """Several resources without schemas in a search at the root are counted in one sentence."""
    _setup_creation_and_deletion(httpserver)
    resource = {key: value for key, value in USER_PAYLOAD.items() if key != "schemas"}
    _respond_to_search_with(httpserver, [resource, {**resource, "id": "456"}])

    results = search_with_attributes(testing_context, User)

    assert results[0].reason == (
        "The server returned 2 resources without the schema of a known resource "
        "type (RFC 7643 §3)"
    )


def test_search_returning_other_invalid_resources_keeps_the_validation_details(
    httpserver, testing_context
):
    """A search returning invalid resources for another reason keeps the validation details."""
    _setup_creation_and_deletion(httpserver)
    resource = {key: value for key, value in USER_PAYLOAD.items() if key != "schemas"}
    invalid = {**USER_PAYLOAD, "id": "456", "active": "maybe"}
    _respond_to_search_with(httpserver, [resource, invalid])

    results = search_with_attributes(testing_context, User)

    assert results[0].status == Status.ERROR
    assert "union_tag_not_found" in results[0].reason
    assert "active" in results[0].reason
