from scim2_models import Resource
from scim2_models import ResourceType

from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckResult
from scim2_tester.utils import ResourceManager
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
def check_object_query(
    conf: CheckConfig, model: type[Resource], resources: ResourceManager
) -> CheckResult:
    """Test object query by ID with automatic cleanup.

    Creates a temporary test object, queries it by ID to validate the
    read operation.

    :param conf: The check configuration containing the SCIM client
    :param model: The Resource model class to test
    :param resources: Resource manager for automatic cleanup
    :returns: The result of the check operation
    """
    test_obj = resources.create_and_register(model)

    response = conf.client.query(
        model, test_obj.id, expected_status_codes=conf.expected_status_codes or [200]
    )

    return CheckResult(
        conf,
        status=Status.SUCCESS,
        reason=f"Successfully queried {model.__name__} object with id {test_obj.id}",
        data=response,
    )


@checker("crud:read")
def check_object_query_without_id(
    conf: CheckConfig, model: type[Resource], resources: ResourceManager
) -> CheckResult:
    """Test object listing without ID with automatic cleanup.

    Creates a temporary test object, performs a list/search operation to
    validate bulk retrieval.

    :param conf: The check configuration containing the SCIM client
    :param model: The Resource model class to test
    :param resources: Resource manager for automatic cleanup
    :returns: The result of the check operation
    """
    test_obj = resources.create_and_register(model)

    response = conf.client.query(
        model, expected_status_codes=conf.expected_status_codes or [200]
    )

    found = any(test_obj.id == resource.id for resource in response.resources)
    if not found:
        return CheckResult(
            conf,
            status=Status.ERROR,
            reason=f"Could not find {model.__name__} object with id {test_obj.id} in list response",
            data=response,
        )

    return CheckResult(
        conf,
        status=Status.SUCCESS,
        reason=f"Successfully found {model.__name__} object with id {test_obj.id} in list response",
        data=response,
    )
