from scim2_models import Resource
from scim2_models import ResourceType

from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status
from scim2_tester.utils import checker


def model_from_resource_type(
    conf: CheckConfig, resource_type: ResourceType
) -> type[Resource] | None:
    """Return the Resource model class from a given ResourceType.

    ResourceType.name contains the resource type name (e.g., "User", "Group").
    This function looks up the corresponding model class from the client.

    :param conf: The check configuration containing the SCIM client
    :param resource_type: The ResourceType object containing metadata
    :returns: The Resource model class, or None if not found
    """
    for resource_model in conf.client.resource_models:
        if resource_model.model_fields["schemas"].default[0] == resource_type.schema_:
            return resource_model

    return None


@checker("crud:read")
def check_object_query(conf: CheckConfig, obj: Resource) -> CheckResult:
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


@checker("crud:read")
def check_object_query_without_id(conf: CheckConfig, obj: Resource) -> CheckResult:
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
