from scim2_models import Mutability
from scim2_models import Resource
from scim2_models import ResourceType

from scim2_tester.filling import fill_with_random_values
from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status
from scim2_tester.utils import checker


def model_from_resource_type(
    conf: CheckConfig, resource_type: ResourceType
) -> type[Resource] | None:
    for resource_model in conf.client.resource_models:
        if resource_model.model_fields["schemas"].default[0] == resource_type.schema_:
            return resource_model

    return None


@checker
def check_object_creation(conf: CheckConfig, obj: type[Resource]) -> CheckResult:
    """Perform an object creation.

    Todo:
      - check if the fields of the result object are the same than the
      fields of the request object

    """
    response = conf.client.create(
        obj, expected_status_codes=conf.expected_status_codes or [201]
    )

    return CheckResult(
        conf,
        status=Status.SUCCESS,
        reason=f"Successful creation of a {obj.__class__.__name__} object with id {response.id}",
        data=response,
    )


@checker
def check_object_query(conf: CheckConfig, obj: type[Resource]) -> CheckResult:
    """Perform an object query by knowing its id.

    Todo:
      - check if the fields of the result object are the same than the
      fields of the request object

    """
    response = conf.client.query(
        obj.__class__, obj.id, expected_status_codes=conf.expected_status_codes or [200]
    )
    return CheckResult(
        conf,
        status=Status.SUCCESS,
        reason=f"Successful query of a {obj.__class__.__name__} object with id {response.id}",
        data=response,
    )


@checker
def check_object_query_without_id(
    conf: CheckConfig, obj: type[Resource]
) -> CheckResult:
    """Perform the query of all objects of one kind.

    Todo:
      - look for the object across several pages
      - check if the fields of the result object are the same than the
      fields of the request object

    """
    response = conf.client.query(
        obj.__class__, expected_status_codes=conf.expected_status_codes or [200]
    )
    found = any(obj.id == resource.id for resource in response.resources)
    if not found:
        return CheckResult(
            conf,
            status=Status.ERROR,
            reason=f"Could not find object {obj.__class__.__name__} with id : {obj.id}",
            data=response,
        )

    return CheckResult(
        conf,
        status=Status.SUCCESS,
        reason=f"Successful query of a {obj.__class__.__name__} object with id {obj.id}",
        data=response,
    )


@checker
def check_object_replacement(conf: CheckConfig, obj: type[Resource]) -> CheckResult:
    """Perform an object replacement.

    Todo:
      - check if the fields of the result object are the same than the
      fields of the request object

    """
    response = conf.client.replace(
        obj, expected_status_codes=conf.expected_status_codes or [200]
    )
    return CheckResult(
        conf,
        status=Status.SUCCESS,
        reason=f"Successful replacement of a {obj.__class__.__name__} object with id {response.id}",
        data=response,
    )


@checker
def check_object_deletion(conf: CheckConfig, obj: type[Resource]) -> CheckResult:
    """Perform an object deletion."""
    conf.client.delete(
        obj.__class__, obj.id, expected_status_codes=conf.expected_status_codes or [204]
    )
    return CheckResult(
        conf,
        status=Status.SUCCESS,
        reason=f"Successful deletion of a {obj.__class__.__name__} object with id {obj.id}",
    )


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
        result = check_object_deletion(conf, garbage)
        results.append(result)

    return results
