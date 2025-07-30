from scim2_models import ServiceProviderConfig

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import checker


@checker("discovery", "service-provider-config")
def service_provider_config_endpoint(
    context: CheckContext,
) -> CheckResult:
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

    .. todo::

        Check that POST/PUT/PATCH/DELETE methods on the endpoint return appropriate errors
    """
    response = context.client.query(
        ServiceProviderConfig,
        expected_status_codes=context.conf.expected_status_codes or [200],
    )
    return CheckResult(status=Status.SUCCESS, data=response)
