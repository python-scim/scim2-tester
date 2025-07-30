from typing import Any

from scim2_models import Resource

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import checker


@checker("crud:create")
def object_creation(context: CheckContext, model: type[Resource[Any]]) -> CheckResult:
    """Test object creation with automatic cleanup.

    Creates a test object of the specified model type, validates the creation
    operation.

    :param context: The check context containing the SCIM client and configuration
    :param model: The Resource model class to test
    :returns: The result of the check operation
    """
    created_obj = context.resource_manager.create_and_register(model)

    return CheckResult(
        status=Status.SUCCESS,
        reason=f"Successfully created {model.__name__} object with id {created_obj.id}",
        data=created_obj,
    )
