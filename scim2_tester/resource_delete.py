from scim2_models import Resource

from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckResult
from scim2_tester.utils import ResourceManager
from scim2_tester.utils import Status
from scim2_tester.utils import checker


@checker("crud:delete")
def check_object_deletion(
    conf: CheckConfig, model: type[Resource], resources: ResourceManager
) -> CheckResult:
    """Test object deletion with automatic cleanup.

    Creates a test object specifically for deletion testing, performs the
    delete operation, and verifies the object no longer exists.

    :param conf: The check configuration containing the SCIM client
    :param model: The Resource model class to test
    :param resources: Resource manager for automatic cleanup
    :returns: The result of the check operation
    """
    test_obj = resources.create_and_register(model)

    # Remove from resource manager since we're testing deletion explicitly
    if test_obj in resources.resources:
        resources.resources.remove(test_obj)

    conf.client.delete(
        model, test_obj.id, expected_status_codes=conf.expected_status_codes or [204]
    )

    try:
        conf.client.query(model, test_obj.id)
        return CheckResult(
            conf,
            status=Status.ERROR,
            reason=f"{model.__name__} object with id {test_obj.id} still exists after deletion",
        )
    except Exception:
        # Expected - object should not exist after deletion
        pass

    return CheckResult(
        conf,
        status=Status.SUCCESS,
        reason=f"Successfully deleted {model.__name__} object with id {test_obj.id}",
    )
