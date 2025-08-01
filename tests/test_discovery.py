"""Test discovery endpoints functionality."""

from scim2_client import SCIMClientError

from scim2_tester.checkers._discovery_utils import _test_discovery_endpoint_methods
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
    """Test that non-405 responses are reported as errors."""
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
    assert results[1].status == Status.ERROR
    assert "PUT /ResourceTypes returned 404 instead of 405" in results[1].reason
    assert results[2].status == Status.ERROR
    assert "PATCH /ResourceTypes returned 500 instead of 405" in results[2].reason
    assert results[3].status == Status.SUCCESS
    assert (
        "DELETE /ResourceTypes correctly returned 405 Method Not Allowed"
        in results[3].reason
    )
    assert all(result.data is not None for result in results)


def test_discovery_endpoint_methods_connection_error(testing_context):
    """Test handling of connection errors during HTTP method testing."""
    # Mock the client to raise SCIMClientError
    original_request = testing_context.client.client.request

    def mock_request(*args, **kwargs):
        raise SCIMClientError("Connection failed")

    testing_context.client.client.request = mock_request

    try:
        results = _test_discovery_endpoint_methods(testing_context, "/TestEndpoint")

        assert len(results) == 4
        assert all(result.status == Status.ERROR for result in results)
        for result in results:
            assert "failed: Connection failed" in result.reason
    finally:
        # Restore original method
        testing_context.client.client.request = original_request
