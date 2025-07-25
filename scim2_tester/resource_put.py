from scim2_models import Mutability
from scim2_models import Resource

from scim2_tester.filling import fill_with_random_values
from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckResult
from scim2_tester.utils import ResourceManager
from scim2_tester.utils import Status
from scim2_tester.utils import checker


@checker("crud:update")
def check_object_replacement(
    conf: CheckConfig, model: type[Resource], resources: ResourceManager
) -> CheckResult:
    """Test object replacement (PUT) with automatic cleanup.

    Creates a test object, modifies its mutable fields, performs a replacement
    operation to validate the update functionality.

    :param conf: The check configuration containing the SCIM client
    :param model: The Resource model class to test
    :param resources: Resource manager for automatic cleanup
    :returns: The result of the check operation
    """
    test_obj = resources.create_and_register(model)

    mutable_fields = [
        field_name
        for field_name in model.model_fields.keys()
        if model.get_field_annotation(field_name, Mutability)
        in (Mutability.read_write, Mutability.write_only)
    ]

    modified_obj = fill_with_random_values(conf, test_obj, resources, mutable_fields)

    if modified_obj is None:
        raise ValueError(
            f"Could not modify {model.__name__} object with mutable fields"
        )

    response = conf.client.replace(
        modified_obj, expected_status_codes=conf.expected_status_codes or [200]
    )

    return CheckResult(
        conf,
        status=Status.SUCCESS,
        reason=f"Successfully replaced {model.__name__} object with id {test_obj.id}",
        data=response,
    )
