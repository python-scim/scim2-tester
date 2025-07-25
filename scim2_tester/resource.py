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
    field_names = [
        field_name
        for field_name in model.model_fields.keys()
        if model.get_field_annotation(field_name, Mutability)
        in (Mutability.read_write, Mutability.write_only, Mutability.immutable)
    ]
    obj, obj_garbages = fill_with_random_values(conf, model(), field_names)
    garbages += obj_garbages

    result = check_object_creation(conf, obj)
    results.append(result)

    if result.status == Status.SUCCESS:
        created_obj = result.data
        result = check_object_query(conf, created_obj)
        results.append(result)

        result = check_object_query_without_id(conf, created_obj)
        results.append(result)

        field_names = [
            field_name
            for field_name in model.model_fields.keys()
            if model.get_field_annotation(field_name, Mutability)
            in (Mutability.read_write, Mutability.write_only)
        ]
        _, obj_garbages = fill_with_random_values(conf, created_obj, field_names)
        garbages += obj_garbages
        result = check_object_replacement(conf, created_obj)
        results.append(result)

        result = check_object_deletion(conf, created_obj)
        results.append(result)

    for garbage in reversed(garbages):
        conf.client.delete(garbage)

    return results
