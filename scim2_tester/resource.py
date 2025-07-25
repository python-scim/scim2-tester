from scim2_models import ResourceType

from scim2_tester.filling import create_minimal_object
from scim2_tester.resource_delete import check_object_deletion
from scim2_tester.resource_get import check_object_query
from scim2_tester.resource_get import check_object_query_without_id
from scim2_tester.resource_get import model_from_resource_type
from scim2_tester.resource_patch import check_object_modification
from scim2_tester.resource_post import check_object_creation
from scim2_tester.resource_put import check_object_replacement
from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status
from scim2_tester.utils import checker
from scim2_tester.utils import should_test_patch


@checker
def check_resource_type(
    conf: CheckConfig,
    resource_type: ResourceType,
) -> list[CheckResult]:
    """Test all SCIM operations for a specific resource type.

    This function orchestrates comprehensive testing of a SCIM resource type by:
    1. Creating test objects
    2. Testing all CRUD operations (POST, GET, PUT, PATCH, DELETE)
    3. Verifying compliance with SCIM specifications

    :param conf: The check configuration containing the SCIM client
    :param resource_type: The ResourceType object to test
    :returns: A list of check results for all tested operations
    """
    results = []

    # Get the resource model class from the resource type
    model = model_from_resource_type(conf, resource_type)
    if model is None:
        return [
            CheckResult(
                conf,
                status=Status.ERROR,
                reason=f"Could not find model for resource type {resource_type.name}",
                data=resource_type,
            )
        ]

    # Test object creation (POST)
    result = check_object_creation(conf, model)
    results.append(result)

    # Test object query without ID (GET /ResourceTypes)
    result = check_object_query_without_id(conf, model)
    results.append(result)

    # Create an object for testing other operations
    try:
        created_obj, garbages = create_minimal_object(conf, model)
    except Exception as e:
        return results + [
            CheckResult(
                conf,
                status=Status.ERROR,
                reason=f"Failed to create test object for {model.__name__}: {e}",
                data=e,
            )
        ]

    # Test object query by ID (GET /ResourceTypes/id)
    result = check_object_query(conf, model)
    results.append(result)

    # Test object replacement (PUT)
    result = check_object_replacement(conf, model)
    results.append(result)

    # Test PATCH operations if supported (RFC7644 §3.5.2)
    if should_test_patch(conf):
        patch_results = check_object_modification(conf, created_obj)
        results.extend(patch_results)

    # Test object deletion (DELETE)
    result = check_object_deletion(conf, created_obj)
    results.append(result)

    # Clean up any remaining garbage objects
    for garbage in reversed(garbages):
        try:
            conf.client.delete(garbage.__class__, garbage.id)
        except Exception:
            pass

    return results
