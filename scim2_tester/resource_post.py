from scim2_models import Resource

from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckResult
from scim2_tester.utils import ResourceManager
from scim2_tester.utils import Status
from scim2_tester.utils import checker


@checker("crud:create")
def check_object_creation(
    conf: CheckConfig, model: type[Resource], resources: ResourceManager
) -> CheckResult:
    """Test object creation with automatic cleanup.

    Creates a test object of the specified model type, validates the creation
    operation.

    :param conf: The check configuration containing the SCIM client
    :param model: The Resource model class to test
    :param resources: Resource manager for automatic cleanup
    :returns: The result of the check operation
    """
    created_obj = resources.create_and_register(model)

    return CheckResult(
        conf,
        status=Status.SUCCESS,
        reason=f"Successfully created {model.__name__} object with id {created_obj.id}",
        data=created_obj,
    )
