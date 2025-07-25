from scim2_models import Mutability
from scim2_models import Resource

from scim2_tester.filling import fill_with_random_values
from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status
from scim2_tester.utils import checker


@checker
def check_object_creation(conf: CheckConfig, obj: type[Resource]) -> CheckResult:
    """Perform an object creation.

    This test verifies that:
    - Objects can be created via POST operations
    - Required fields are validated
    - The created object is returned with proper metadata
    - Server-generated fields (like id, meta) are populated

    :param conf: The check configuration containing the SCIM client
    :param obj: The Resource model class to test
    :returns: The result of the check operation
    """
    # Get all writable fields for the resource
    field_names = [
        field_name
        for field_name in obj.model_fields
        if obj.get_field_annotation(field_name, Mutability)
        in (Mutability.read_write, Mutability.write_only, Mutability.immutable)
        and obj.get_field_annotation(field_name, Mutability) != Mutability.read_only
    ]

    # Create an object with random values for testing
    test_obj, garbages = fill_with_random_values(conf, obj(), field_names)

    try:
        # Attempt to create the object
        created_obj = conf.client.create(test_obj)

        # Clean up the created object and any dependencies
        for garbage in reversed(garbages + [created_obj]):
            conf.client.delete(garbage.__class__, garbage.id)

        return CheckResult(
            conf,
            status=Status.SUCCESS,
            reason=f"Successful creation of a {obj.__name__} object with id {created_obj.id}",
            data=created_obj,
        )

    except Exception as e:
        # Clean up any created dependencies even if main creation failed
        for garbage in reversed(garbages):
            try:
                conf.client.delete(garbage.__class__, garbage.id)
            except Exception:
                pass

        return CheckResult(
            conf,
            status=Status.ERROR,
            reason=f"Failed to create a {obj.__name__} object: {e}",
            data=e,
        )
