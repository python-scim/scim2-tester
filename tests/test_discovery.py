"""Test discovery endpoints functionality."""

import pytest
from scim2_client import SCIMClientException
from scim2_client.engines.wsgi import WSGISCIMClient

from scim2_tester.checkers._discovery_utils import _test_discovery_endpoint_methods
from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckContext
from scim2_tester.utils import Status


def test_discovery_endpoint_methods_return_405(httpserver, testing_context):
    """Test that discovery endpoints return 405 for unsupported HTTP methods."""
    endpoint = "/ServiceProviderConfig"

    # Mock all unsupported methods to return 405
    for method in ["POST", "PUT", "PATCH", "DELETE"]:
        httpserver.expect_request(uri=endpoint, method=method).respond_with_data(
            "", status=405
        )

    results = _test_discovery_endpoint_methods(testing_context, endpoint)

    assert len(results) == 4
    assert all(result.status == Status.SUCCESS for result in results)
    for i, method in enumerate(["POST", "PUT", "PATCH", "DELETE"]):
        assert (
            f"{method} {endpoint} correctly returned 405 Method Not Allowed"
            in results[i].reason
        )


def test_discovery_endpoint_methods_wrong_status_codes(httpserver, testing_context):
    """A success or a server error is an error, a 404 is a deviation."""
    endpoint = "/ResourceTypes"

    # Mock methods to return wrong status codes
    httpserver.expect_request(uri=endpoint, method="POST").respond_with_data(
        "", status=200
    )

    httpserver.expect_request(uri=endpoint, method="PUT").respond_with_data(
        "", status=404
    )

    httpserver.expect_request(uri=endpoint, method="PATCH").respond_with_data(
        "", status=500
    )

    httpserver.expect_request(uri=endpoint, method="DELETE").respond_with_data(
        "", status=405
    )  # This one should succeed

    results = _test_discovery_endpoint_methods(testing_context, endpoint)

    assert len(results) == 4
    assert results[0].status == Status.ERROR
    assert "POST /ResourceTypes returned 200 instead of 405" in results[0].reason
    assert results[1].status == Status.DEVIATION
    assert "PUT /ResourceTypes returned 404 instead of 405" in results[1].reason
    assert results[2].status == Status.ERROR
    assert "PATCH /ResourceTypes returned 500 instead of 405" in results[2].reason
    assert results[3].status == Status.SUCCESS
    assert (
        "DELETE /ResourceTypes correctly returned 405 Method Not Allowed"
        in results[3].reason
    )
    assert all(result.data is not None for result in results)


def test_discovery_endpoint_methods_connection_error(testing_context, monkeypatch):
    """A request that cannot be sent is reported as an error."""

    def fail(*args, **kwargs):
        raise SCIMClientException("Connection failed")

    monkeypatch.setattr(testing_context.client, "request", fail)

    results = _test_discovery_endpoint_methods(testing_context, "/TestEndpoint")

    assert len(results) == 4
    assert all(result.status == Status.ERROR for result in results)
    for result in results:
        assert "failed: Connection failed" in result.reason


def test_discovery_endpoint_methods_with_the_wsgi_engine():
    """The HTTP method checks send their requests with the WSGI engine."""

    def application(environ, start_response):
        start_response("405 Method Not Allowed", [])
        return []

    client = WSGISCIMClient(application, base_url="http://localhost/scim/v2")
    context = CheckContext(client, CheckConfig())

    results = _test_discovery_endpoint_methods(context, "/Schemas")

    assert [result.status for result in results] == [Status.SUCCESS] * 4


@pytest.mark.parametrize("status_code", [400, 403, 404, 501])
def test_discovery_endpoint_methods_refused_without_405_deviate(
    httpserver, testing_context, status_code
):
    """A discovery endpoint refusing a method with a 4xx or 501 status other than 405 deviates."""
    for method in ["POST", "PUT", "PATCH", "DELETE"]:
        httpserver.expect_request(uri="/Schemas", method=method).respond_with_data(
            "", status=status_code
        )

    results = _test_discovery_endpoint_methods(testing_context, "/Schemas")

    assert [result.status for result in results] == [Status.DEVIATION] * 4
    assert results[0].reason == f"POST /Schemas returned {status_code} instead of 405"


@pytest.mark.parametrize("status_code", [201, 204, 500, 503])
def test_discovery_endpoint_methods_accepted_or_crashing_fail(
    httpserver, testing_context, status_code
):
    """A discovery endpoint accepting a method, or failing with a 5xx status other than 501, is an error."""
    for method in ["POST", "PUT", "PATCH", "DELETE"]:
        httpserver.expect_request(uri="/Schemas", method=method).respond_with_data(
            "", status=status_code
        )

    results = _test_discovery_endpoint_methods(testing_context, "/Schemas")

    assert [result.status for result in results] == [Status.ERROR] * 4
