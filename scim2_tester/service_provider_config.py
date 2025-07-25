from scim2_models import ServiceProviderConfig

from .utils import CheckConfig
from .utils import CheckResult
from .utils import Status
from .utils import checker


@checker("discovery", "service-provider-config")
def check_service_provider_config_endpoint(
    conf: CheckConfig,
) -> CheckResult:
    """As described in RFC7644 §4 <rfc7644#section-4>`, `/ServiceProviderConfig` is a mandatory endpoint, and should only be accessible by GET.

    .. todo::

        Check that POST/PUT/PATCH/DELETE methods on the endpoint
    """
    response = conf.client.query(
        ServiceProviderConfig, expected_status_codes=conf.expected_status_codes or [200]
    )
    return CheckResult(conf, status=Status.SUCCESS, data=response)
