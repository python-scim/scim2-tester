"""Test service provider config functionality."""

from scim2_models import Context
from scim2_models import ServiceProviderConfig

from scim2_tester.checkers.service_provider_config import (
    service_provider_config_endpoint,
)
from scim2_tester.checkers.service_provider_config import (
    service_provider_config_endpoint_methods,
)
from scim2_tester.utils import Status


def test_service_provider_config_endpoint_methods(httpserver, check_config):
    """Test that service provider config endpoint returns proper errors for unsupported HTTP methods."""
    # Mock all HTTP methods to return 405
    for method in ["POST", "PUT", "PATCH", "DELETE"]:
        httpserver.expect_request(
            uri="/ServiceProviderConfig", method=method
        ).respond_with_data("", status=405)

    results = service_provider_config_endpoint_methods(check_config)

    assert len(results) == 4
    assert all(result.status == Status.SUCCESS for result in results)
    for i, method in enumerate(["POST", "PUT", "PATCH", "DELETE"]):
        assert (
            f"{method} /ServiceProviderConfig correctly returned 405 Method Not Allowed"
            in results[i].reason
        )


def test_service_provider_config_endpoint(httpserver, check_config):
    """Test successful access to service provider config endpoint."""
    spc = ServiceProviderConfig()

    httpserver.expect_request("/ServiceProviderConfig").respond_with_json(
        spc.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=200,
        content_type="application/scim+json",
    )

    result = service_provider_config_endpoint(check_config)
    assert result.status == Status.SUCCESS
    assert result.data == spc
