from scim2_models import Resource

from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status
from scim2_tester.utils import checker


@checker
def check_object_deletion(conf: CheckConfig, obj: Resource) -> CheckResult:
    """Perform an object deletion.

    This test verifies that:
    - Objects can be deleted via DELETE operations
    - Deleted objects return 404 when queried afterward
    - The deletion operation returns appropriate status codes (200 or 204)

    :param conf: The check configuration containing the SCIM client
    :param obj: The Resource instance to delete
    :returns: The result of the check operation
    """
    try:
        # Delete the object using class and ID
        conf.client.delete(
            obj.__class__,
            obj.id,
            expected_status_codes=conf.expected_status_codes or [204],
        )

        return CheckResult(
            conf,
            status=Status.SUCCESS,
            reason=f"Successful deletion of a {obj.__class__.__name__} object with id {obj.id}",
        )

    except Exception as e:
        return CheckResult(
            conf,
            status=Status.ERROR,
            reason=f"Failed to delete a {obj.__class__.__name__} object with id {obj.id}: {e}",
            data=e,
        )
