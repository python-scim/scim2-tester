from scim2_models import Resource

from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status
from scim2_tester.utils import checker


@checker("crud:delete")
def check_object_deletion(conf: CheckConfig, obj: Resource) -> CheckResult:
    """Perform an object deletion."""
    conf.client.delete(
        obj.__class__, obj.id, expected_status_codes=conf.expected_status_codes or [204]
    )
    return CheckResult(
        conf,
        status=Status.SUCCESS,
        reason=f"Successful deletion of a {obj.__class__.__name__} object with id {obj.id}",
    )
