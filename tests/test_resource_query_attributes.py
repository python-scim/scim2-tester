"""Unit tests for attribute filtering compliance checkers."""

import json
from unittest.mock import patch

from scim2_models import Error
from scim2_models import User
from werkzeug.wrappers import Response

from scim2_tester.checkers.resource_query_attributes import _check_attribute_filtering
from scim2_tester.checkers.resource_query_attributes import _find_resource_in_list
from scim2_tester.checkers.resource_query_attributes import _pick_attribute_names
from scim2_tester.checkers.resource_query_attributes import _run_attribute_checks
from scim2_tester.checkers.resource_query_attributes import object_list_with_attributes
from scim2_tester.checkers.resource_query_attributes import object_query_with_attributes
from scim2_tester.checkers.resource_query_attributes import search_with_attributes
from scim2_tester.utils import Status

INCLUDED_ATTR, EXCLUDED_ATTR = _pick_attribute_names(User)

USER_PAYLOAD = {
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    "id": "123",
    "userName": "bjensen@example.com",
    "displayName": "Barbara Jensen",
    "nickName": "Babs",
    "externalId": "ext-123",
    "name": {"givenName": "Barbara", "familyName": "Jensen"},
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
    """Apply attribute filtering to a payload dict."""
    result = dict(payload)
    if attributes is not None:
        keep = set(attributes) | {"schemas", "id"}
        result = {k: v for k, v in result.items() if k in keep}
    if excluded_attributes is not None:
        drop = set(excluded_attributes)
        result = {k: v for k, v in result.items() if k not in drop}
    return result


def _compliant_get_handler(request):
    """Return a filtered response depending on query params."""
    qs = request.args
    attrs = (
        [a.strip() for a in qs["attributes"].split(",")] if "attributes" in qs else None
    )
    excl = (
        [a.strip() for a in qs["excludedAttributes"].split(",")]
        if "excludedAttributes" in qs
        else None
    )
    payload = _filter_payload(USER_PAYLOAD, attrs, excl)
    return Response(
        json.dumps(payload),
        status=200,
        headers={"Content-Type": "application/scim+json"},
    )


def _unfiltered_get_handler(request):
    """Return the full payload, ignoring filter params."""
    return Response(
        json.dumps(USER_PAYLOAD),
        status=200,
        headers={"Content-Type": "application/scim+json"},
    )


def _compliant_list_handler(request):
    """Return a ListResponse with filtering applied."""
    qs = request.args
    attrs = (
        [a.strip() for a in qs["attributes"].split(",")] if "attributes" in qs else None
    )
    excl = (
        [a.strip() for a in qs["excludedAttributes"].split(",")]
        if "excludedAttributes" in qs
        else None
    )
    resource = _filter_payload(USER_PAYLOAD, attrs, excl)
    payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 1,
        "Resources": [resource],
    }
    return Response(
        json.dumps(payload),
        status=200,
        headers={"Content-Type": "application/scim+json"},
    )


def _compliant_search_handler(request):
    """Return a ListResponse with filtering applied from POST body."""
    body = json.loads(request.get_data(as_text=True)) if request.data else {}
    attrs = body.get("attributes")
    excl = body.get("excludedAttributes")
    resource = _filter_payload(USER_PAYLOAD, attrs, excl)
    payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 1,
        "Resources": [resource],
    }
    return Response(
        json.dumps(payload),
        status=200,
        headers={"Content-Type": "application/scim+json"},
    )


def _empty_list_response():
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 0,
        "Resources": [],
    }


def test_pick_attribute_names_returns_two_candidates():
    """User model has enough default-returned attributes to pick two."""
    included, excluded = _pick_attribute_names(User)
    assert included is not None
    assert excluded is not None
    assert included != excluded


def test_check_attribute_filtering_success():
    """Returns SUCCESS when included attribute is present and excluded is absent."""
    data = {"userName": "test", "id": "1"}
    status, _ = _check_attribute_filtering(data, "userName", None, "User", "GET")
    assert status == Status.SUCCESS


def test_check_attribute_filtering_missing_included():
    """Returns ERROR when the requested attribute is missing from the response."""
    data = {"id": "1"}
    status, reason = _check_attribute_filtering(data, "userName", None, "User", "GET")
    assert status == Status.ERROR
    assert "missing" in reason


def test_check_attribute_filtering_excluded_still_present():
    """Returns ERROR when the excluded attribute is still in the response."""
    data = {"userName": "test", "displayName": "Test", "id": "1"}
    status, reason = _check_attribute_filtering(
        data, None, "displayName", "User", "GET"
    )
    assert status == Status.ERROR
    assert "still present" in reason


def test_object_query_with_attributes_compliant_server(httpserver, testing_context):
    """GET /Users/{id} with attribute filtering succeeds on a compliant server."""
    _setup_creation_and_deletion(httpserver)
    httpserver.expect_request(uri="/Users/123", method="GET").respond_with_handler(
        _compliant_get_handler
    )

    results = object_query_with_attributes(testing_context, User)
    assert all(r.status == Status.SUCCESS for r in results)


def test_object_query_with_attributes_server_ignores_filter(
    httpserver, testing_context
):
    """GET /Users/{id} returns ERROR when server ignores excludedAttributes."""
    _setup_creation_and_deletion(httpserver)
    httpserver.expect_request(uri="/Users/123", method="GET").respond_with_handler(
        _unfiltered_get_handler
    )

    results = object_query_with_attributes(testing_context, User)
    error_results = [r for r in results if r.status == Status.ERROR]
    assert len(error_results) >= 1


def test_object_list_with_attributes_compliant_server(httpserver, testing_context):
    """GET /Users with attribute filtering succeeds on a compliant server."""
    _setup_creation_and_deletion(httpserver)
    httpserver.expect_request(uri="/Users", method="GET").respond_with_handler(
        _compliant_list_handler
    )

    results = object_list_with_attributes(testing_context, User)
    assert all(r.status == Status.SUCCESS for r in results)


def test_object_list_with_attributes_resource_not_found(httpserver, testing_context):
    """GET /Users returns ERROR when the created resource is not in the filtered list."""
    _setup_creation_and_deletion(httpserver)

    def empty_handler(request):
        return Response(
            json.dumps(_empty_list_response()),
            status=200,
            headers={"Content-Type": "application/scim+json"},
        )

    httpserver.expect_request(uri="/Users", method="GET").respond_with_handler(
        empty_handler
    )

    results = object_list_with_attributes(testing_context, User)
    error_results = [r for r in results if r.status == Status.ERROR]
    assert len(error_results) >= 1
    assert any("could not find" in r.reason for r in error_results)


def test_search_with_attributes_compliant_server(httpserver, testing_context):
    """POST /.search with attribute filtering succeeds on a compliant server."""
    _setup_creation_and_deletion(httpserver)
    httpserver.expect_request(uri="/.search", method="POST").respond_with_handler(
        _compliant_search_handler
    )

    results = search_with_attributes(testing_context, User)
    assert all(r.status == Status.SUCCESS for r in results)


def test_search_with_attributes_resource_not_found(httpserver, testing_context):
    """POST /.search returns ERROR when the created resource is absent from results."""
    _setup_creation_and_deletion(httpserver)

    def empty_handler(request):
        return Response(
            json.dumps(_empty_list_response()),
            status=200,
            headers={"Content-Type": "application/scim+json"},
        )

    httpserver.expect_request(uri="/.search", method="POST").respond_with_handler(
        empty_handler
    )

    results = search_with_attributes(testing_context, User)
    error_results = [r for r in results if r.status == Status.ERROR]
    assert len(error_results) >= 1
    assert any("could not find" in r.reason for r in error_results)


def test_find_resource_in_list_with_non_list_response():
    """Returns None when the input is not a ListResponse."""
    assert _find_resource_in_list({"some": "dict"}, "123") is None


def test_run_attribute_checks_skips_none_attributes(httpserver, testing_context):
    """Inclusion check is skipped when included is None."""
    _setup_creation_and_deletion(httpserver)
    httpserver.expect_request(uri="/Users/123", method="GET").respond_with_handler(
        _compliant_get_handler
    )

    test_obj = testing_context.resource_manager.create_and_register(User, fill_all=True)

    def query_fn(query_parameters):
        return testing_context.client.query(
            User,
            test_obj.id,
            query_parameters=query_parameters,
            expected_status_codes=[200],
        )

    results = _run_attribute_checks(
        testing_context, User, test_obj, None, EXCLUDED_ATTR, query_fn, "GET /test"
    )
    assert len(results) == 1
    assert results[0].status == Status.SUCCESS


def test_run_attribute_checks_unexpected_response_type(httpserver, testing_context):
    """Returns ERROR when the query returns an unexpected type like Error."""
    _setup_creation_and_deletion(httpserver)
    test_obj = testing_context.resource_manager.create_and_register(User, fill_all=True)

    error_obj = Error(status="400", detail="bad request")

    def query_fn(query_parameters):
        return error_obj

    results = _run_attribute_checks(
        testing_context, User, test_obj, INCLUDED_ATTR, None, query_fn, "GET /test"
    )
    assert len(results) == 1
    assert results[0].status == Status.ERROR
    assert "unexpected response type" in results[0].reason


_NO_ATTRS = "scim2_tester.checkers.resource_query_attributes._pick_attribute_names"


def test_object_query_skipped_when_no_suitable_attributes(httpserver, testing_context):
    """GET /Resource/{id} is skipped when the model has no suitable attributes."""
    with patch(_NO_ATTRS, return_value=(None, None)):
        results = object_query_with_attributes(testing_context, User)
    assert len(results) == 1
    assert results[0].status == Status.SKIPPED


def test_object_list_skipped_when_no_suitable_attributes(httpserver, testing_context):
    """GET /Resource is skipped when the model has no suitable attributes."""
    with patch(_NO_ATTRS, return_value=(None, None)):
        results = object_list_with_attributes(testing_context, User)
    assert len(results) == 1
    assert results[0].status == Status.SKIPPED


def test_search_skipped_when_no_suitable_attributes(httpserver, testing_context):
    """POST /.search is skipped when the model has no suitable attributes."""
    with patch(_NO_ATTRS, return_value=(None, None)):
        results = search_with_attributes(testing_context, User)
    assert len(results) == 1
    assert results[0].status == Status.SKIPPED
