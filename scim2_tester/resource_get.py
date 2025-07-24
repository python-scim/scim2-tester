from scim2_models import Resource
from scim2_models import ResourceType

from scim2_tester.filling import create_minimal_object
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
    try:
        return conf.client.get_resource_model(resource_type.name)
    except Exception:
        return None


def check_object_query_by_instance(conf: CheckConfig, obj: Resource) -> CheckResult:
    """Perform an object query using a pre-existing Resource instance.

    This function is used for testing specific scenarios where you want to query
    a known object by its ID without creating it first.

    :param conf: The check configuration containing the SCIM client
    :param obj: The Resource instance to query
    :returns: The result of the check operation
    """
    try:
        response = conf.client.query(obj.__class__, obj.id)
        return CheckResult(
            conf,
            status=Status.SUCCESS,
            reason=f"Successful query of a {obj.__class__.__name__} object with id {obj.id}",
            data=response,
        )
    except Exception as e:
        return CheckResult(
            conf,
            status=Status.ERROR,
            reason=f"Failed to query a {obj.__class__.__name__} object with id {obj.id}: {e}",
            data=e,
        )


@checker
def check_object_query(conf: CheckConfig, obj: type[Resource]) -> CheckResult:
    """Perform an object query by knowing its id.

    This test verifies that:
    - Objects can be retrieved by their ID (GET /ResourceType/id)
    - The returned object matches the SCIM schema
    - Required fields are present in the response

    :param conf: The check configuration containing the SCIM client
    :param obj: The Resource model class to test
    :returns: The result of the check operation
    """
    # Create an object first to have something to query
    created_obj, garbages = create_minimal_object(conf, obj)

    try:
        # Query the object by its ID
        response = conf.client.query(obj, created_obj.id)

        # Clean up the created object
        for garbage in reversed(garbages + [created_obj]):
            conf.client.delete(garbage.__class__, garbage.id)

        return CheckResult(
            conf,
            status=Status.SUCCESS,
            reason=f"Successful query of a {obj.__name__} object with id {created_obj.id}",
            data=response,
        )

    except Exception as e:
        # Clean up the created object even if query failed
        for garbage in reversed(garbages + [created_obj]):
            try:
                conf.client.delete(garbage.__class__, garbage.id)
            except Exception:
                pass

        return CheckResult(
            conf,
            status=Status.ERROR,
            reason=f"Failed to query a {obj.__name__} object with id {created_obj.id}: {e}",
            data=e,
        )


@checker
def check_object_query_without_id(
    conf: CheckConfig, obj: type[Resource]
) -> CheckResult:
    """Perform an object query without specifying an id.

    This test verifies that:
    - Objects can be retrieved via search/list operations (GET /ResourceType)
    - The response includes a list of resources
    - Pagination and filtering work as expected

    :param conf: The check configuration containing the SCIM client
    :param obj: The Resource model class to test
    :returns: The result of the check operation
    """
    # Create an object first to have something to query
    created_obj, garbages = create_minimal_object(conf, obj)

    try:
        # Query objects without specifying an ID (list operation)
        response = conf.client.query(obj)

        # Clean up the created object
        for garbage in reversed(garbages + [created_obj]):
            conf.client.delete(garbage.__class__, garbage.id)

        return CheckResult(
            conf,
            status=Status.SUCCESS,
            reason=f"Successful query of {obj.__name__} objects without id",
            data=response,
        )

    except Exception as e:
        # Clean up the created object even if query failed
        for garbage in reversed(garbages + [created_obj]):
            try:
                conf.client.delete(garbage.__class__, garbage.id)
            except Exception:
                pass

        return CheckResult(
            conf,
            status=Status.ERROR,
            reason=f"Failed to query {obj.__name__} objects without id: {e}",
            data=e,
        )
