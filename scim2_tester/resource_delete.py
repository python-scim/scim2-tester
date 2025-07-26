from typing import Any

from scim2_models import Resource

from scim2_tester.utils import CheckContext
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status
from scim2_tester.utils import checker


@checker("crud:delete")
def check_object_deletion(
    context: CheckContext, model: type[Resource[Any]]
) -> CheckResult:
    """Test object deletion with automatic cleanup.

    Creates a test object specifically for deletion testing, performs the
    delete operation, and verifies the object no longer exists.

    :param context: The check context containing the SCIM client and configuration
    :param model: The Resource model class to test
    :returns: The result of the check operation
    """
    test_obj = context.resource_manager.create_and_register(model)

    # Remove from resource manager since we're testing deletion explicitly
    if test_obj in context.resource_manager.resources:
        context.resource_manager.resources.remove(test_obj)

    if test_obj.id is not None:
        context.client.delete(
            model,
            test_obj.id,
            expected_status_codes=context.conf.expected_status_codes or [204],
        )

    try:
        context.client.query(model, test_obj.id)
        return CheckResult(
            status=Status.ERROR,
            reason=f"{model.__name__} object with id {test_obj.id} still exists after deletion",
        )
    except Exception:
        # Expected - object should not exist after deletion
        pass

    return CheckResult(
        status=Status.SUCCESS,
        reason=f"Successfully deleted {model.__name__} object with id {test_obj.id}",
    )
