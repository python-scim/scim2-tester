from scim2_models import Mutability
from scim2_models import ResourceType

from scim2_tester.filling import fill_with_random_values
from scim2_tester.resource_delete import check_object_deletion
from scim2_tester.resource_get import check_object_query
from scim2_tester.resource_get import check_object_query_without_id
from scim2_tester.resource_get import model_from_resource_type
from scim2_tester.resource_post import check_object_creation
from scim2_tester.resource_put import check_object_replacement
from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status


def check_resource_type(
    conf: CheckConfig,
    resource_type: ResourceType,
) -> list[CheckResult]:
    model = model_from_resource_type(conf, resource_type)
    if not model:
        return [
            CheckResult(
                conf,
                status=Status.ERROR,
                reason=f"No Schema matching the ResourceType {resource_type.id}",
            )
        ]

    results = []
    garbages = []
    created_obj = None

    # Always try to create an object - the decorator will decide if it should be skipped
    field_names = [
        field_name
        for field_name in model.model_fields.keys()
        if model.get_field_annotation(field_name, Mutability)
        in (Mutability.read_write, Mutability.write_only, Mutability.immutable)
    ]
    obj, obj_garbages = fill_with_random_values(conf, model(), field_names)
    garbages += obj_garbages

    create_result = check_object_creation(conf, obj)

    # Only add to results if creation was explicitly requested (not skipped)
    if create_result.status != Status.SKIPPED:
        results.append(create_result)

    # If creation succeeded (either explicitly or as dependency), we have an object
    if create_result.status == Status.SUCCESS:
        created_obj = create_result.data

        # Try read operations - decorator will skip if not needed
        read_result = check_object_query(conf, created_obj)
        if read_result.status != Status.SKIPPED:
            results.append(read_result)

        read_without_id_result = check_object_query_without_id(conf, created_obj)
        if read_without_id_result.status != Status.SKIPPED:
            results.append(read_without_id_result)

        # Try update operations - decorator will skip if not needed
        field_names = [
            field_name
            for field_name in model.model_fields.keys()
            if model.get_field_annotation(field_name, Mutability)
            in (Mutability.read_write, Mutability.write_only)
        ]
        _, obj_garbages = fill_with_random_values(conf, created_obj, field_names)
        garbages += obj_garbages

        update_result = check_object_replacement(conf, created_obj)
        if update_result.status != Status.SKIPPED:
            results.append(update_result)

        # Try delete operations - decorator will skip if not needed
        delete_result = check_object_deletion(conf, created_obj)
        if delete_result.status != Status.SKIPPED:
            results.append(delete_result)

    # Cleanup remaining garbage
    for garbage in reversed(garbages):
        conf.client.delete(garbage)

    return results
