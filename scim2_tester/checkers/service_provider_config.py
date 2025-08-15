from scim2_models import ServiceProviderConfig

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import check_result
from ..utils import checker
from ._discovery_utils import _test_discovery_endpoint_methods


@checker("*", "discovery", "service-provider-config")
def service_provider_config_endpoint(
    context: CheckContext,
) -> list[CheckResult]:
    """Validate the mandatory ServiceProviderConfig discovery endpoint.

    Tests that the ``/ServiceProviderConfig`` endpoint is accessible via GET request
    and returns a valid :class:`~scim2_models.ServiceProviderConfig` object containing server capabilities
    and supported features.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Endpoint returns valid :class:`~scim2_models.ServiceProviderConfig` object
    - :attr:`~scim2_tester.Status.ERROR`: Endpoint is inaccessible or returns invalid response

    .. pull-quote:: :rfc:`RFC 7644 Section 4 - Discovery <7644#section-4>`

       "An HTTP GET to this endpoint will return a JSON structure that describes
       the SCIM specification features available on a service provider."

       "Service providers MUST provide this endpoint."

    """
    response = context.client.query(
        ServiceProviderConfig,
        expected_status_codes=context.conf.expected_status_codes or [200],
    )
    return [
        check_result(
            context,
            status=Status.SUCCESS,
            data=response,
        )
    ]


@checker("discovery", "service-provider-config")
def service_provider_config_endpoint_methods(
    context: CheckContext,
) -> list[CheckResult]:
    """Validate that unsupported HTTP methods return 405 Method Not Allowed.

    Tests that POST, PUT, PATCH, and DELETE methods on the ``/ServiceProviderConfig``
    endpoint correctly return HTTP 405 Method Not Allowed status, as only GET is supported.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: All unsupported methods return 405 status
    - :attr:`~scim2_tester.Status.ERROR`: One or more methods return unexpected status

    .. pull-quote:: :rfc:`RFC 7644 Section 4 - Discovery <7644#section-4>`

       "An HTTP GET to this endpoint will return a JSON structure that describes
       the SCIM specification features available on a service provider."

       Only GET method is specified, other methods should return appropriate errors.
    """
    return _test_discovery_endpoint_methods(context, "/ServiceProviderConfig")
