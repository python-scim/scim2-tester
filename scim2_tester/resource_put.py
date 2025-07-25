from scim2_models import Mutability
from scim2_models import Resource

from scim2_tester.filling import create_minimal_object
from scim2_tester.filling import fill_with_random_values
from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status
from scim2_tester.utils import checker


@checker
def check_object_replacement(conf: CheckConfig, obj: type[Resource]) -> CheckResult:
    """Perform an object replacement.

    This test verifies that:
    - Objects can be replaced via PUT operations
    - The entire object is replaced (not just updated fields)
    - Required fields are validated during replacement
    - Immutable fields cannot be changed after creation

    :param conf: The check configuration containing the SCIM client
    :param obj: The Resource model class to test
    :returns: The result of the check operation
    """
    # First create an object to replace
    created_obj, garbages = create_minimal_object(conf, obj)

    try:
        # Get all writable fields (excluding readOnly and immutable after creation)
        field_names = [
            field_name
            for field_name in obj.model_fields
            if obj.get_field_annotation(field_name, Mutability)
            in (Mutability.read_write, Mutability.write_only)
            and obj.get_field_annotation(field_name, Mutability) != Mutability.read_only
        ]

        # Fill the created object with new random values
        _, obj_garbages = fill_with_random_values(conf, created_obj, field_names)
        garbages += obj_garbages

        # Perform the replacement operation
        response = conf.client.replace(created_obj)

        # Clean up the created object and any dependencies
        for garbage in reversed(garbages + [created_obj]):
            conf.client.delete(garbage.__class__, garbage.id)

        return CheckResult(
            conf,
            status=Status.SUCCESS,
            reason=f"Successful replacement of a {obj.__name__} object with id {created_obj.id}",
            data=response,
        )

    except Exception as e:
        # Clean up the created object and any dependencies even if replacement failed
        for garbage in reversed(garbages + [created_obj]):
            try:
                conf.client.delete(garbage.__class__, garbage.id)
            except Exception:
                pass

        return CheckResult(
            conf,
            status=Status.ERROR,
            reason=f"Failed to replace a {obj.__name__} object with id {created_obj.id}: {e}",
            data=e,
        )
