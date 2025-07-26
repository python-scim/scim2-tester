from typing import Any

from scim2_models import Resource
from scim2_models import ResourceType

from scim2_tester.utils import CheckContext
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status
from scim2_tester.utils import checker


def model_from_resource_type(
    context: CheckContext, resource_type: ResourceType
) -> type[Resource[Any]] | None:
    """Return the Resource model class from a given ResourceType.

    ResourceType.name contains the resource type name (e.g., "User", "Group").
    This function looks up the corresponding model class from the client.

    :param context: The check context containing the SCIM client and configuration
    :param resource_type: The ResourceType object containing metadata
    :returns: The Resource model class, or None if not found
    """
    for resource_model in context.client.resource_models:
        if resource_model.model_fields["schemas"].default[0] == resource_type.schema_:
            return resource_model

    return None


@checker("crud:read")
def check_object_query(
    context: CheckContext, model: type[Resource[Any]]
) -> CheckResult:
    """Test object query by ID with automatic cleanup.

    Creates a temporary test object, queries it by ID to validate the
    read operation.

    :param context: The check context containing the SCIM client and configuration
    :param model: The Resource model class to test
    :returns: The result of the check operation
    """
    test_obj = context.resource_manager.create_and_register(model)

    response = context.client.query(
        model,
        test_obj.id,
        expected_status_codes=context.conf.expected_status_codes or [200],
    )

    return CheckResult(
        status=Status.SUCCESS,
        reason=f"Successfully queried {model.__name__} object with id {test_obj.id}",
        data=response,
    )


@checker("crud:read")
def check_object_query_without_id(
    context: CheckContext, model: type[Resource[Any]]
) -> CheckResult:
    """Test object listing without ID with automatic cleanup.

    Creates a temporary test object, performs a list/search operation to
    validate bulk retrieval.

    :param context: The check context containing the SCIM client and configuration
    :param model: The Resource model class to test
    :returns: The result of the check operation
    """
    test_obj = context.resource_manager.create_and_register(model)

    response = context.client.query(
        model, expected_status_codes=context.conf.expected_status_codes or [200]
    )

    found = any(test_obj.id == resource.id for resource in response.resources)
    if not found:
        return CheckResult(
            status=Status.ERROR,
            reason=f"Could not find {model.__name__} object with id {test_obj.id} in list response",
            data=response,
        )

    return CheckResult(
        status=Status.SUCCESS,
        reason=f"Successfully found {model.__name__} object with id {test_obj.id} in list response",
        data=response,
    )
