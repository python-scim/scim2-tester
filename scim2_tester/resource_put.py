from scim2_models import Resource

from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status
from scim2_tester.utils import checker


@checker("crud:update")
def check_object_replacement(conf: CheckConfig, obj: Resource) -> CheckResult:
    """Perform an object replacement.

    Todo:
      - check if the fields of the result object are the same than the
      fields of the request object

    """
    response = conf.client.replace(
        obj, expected_status_codes=conf.expected_status_codes or [200]
    )
    return CheckResult(
        conf,
        status=Status.SUCCESS,
        reason=f"Successful replacement of a {obj.__class__.__name__} object with id {response.id}",
        data=response,
    )
