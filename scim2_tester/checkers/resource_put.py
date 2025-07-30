from typing import Any

from scim2_models import Mutability
from scim2_models import Resource

from ..filling import fill_with_random_values
from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import checker


@checker("crud:update")
def object_replacement(
    context: CheckContext, model: type[Resource[Any]]
) -> CheckResult:
    """Test object replacement (PUT) with automatic cleanup.

    Creates a test object, modifies its mutable fields, performs a replacement
    operation to validate the update functionality.

    :param context: The check context containing the SCIM client and configuration
    :param model: The Resource model class to test
    :returns: The result of the check operation
    """
    test_obj = context.resource_manager.create_and_register(model)

    mutable_fields = [
        field_name
        for field_name in model.model_fields.keys()
        if model.get_field_annotation(field_name, Mutability)
        in (Mutability.read_write, Mutability.write_only)
    ]

    modified_obj = fill_with_random_values(
        context, test_obj, context.resource_manager, mutable_fields
    )

    if modified_obj is None:
        raise ValueError(
            f"Could not modify {model.__name__} object with mutable fields"
        )

    response = context.client.replace(
        modified_obj, expected_status_codes=context.conf.expected_status_codes or [200]
    )

    return CheckResult(
        status=Status.SUCCESS,
        reason=f"Successfully replaced {model.__name__} object with id {test_obj.id}",
        data=response,
    )
