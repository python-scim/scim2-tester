from scim2_models import ResourceType

from scim2_tester.resource_delete import check_object_deletion
from scim2_tester.resource_get import check_object_query
from scim2_tester.resource_get import check_object_query_without_id
from scim2_tester.resource_get import model_from_resource_type
from scim2_tester.resource_post import check_object_creation
from scim2_tester.resource_put import check_object_replacement
from scim2_tester.utils import CheckContext
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status


def check_resource_type(
    context: CheckContext,
    resource_type: ResourceType,
) -> list[CheckResult]:
    """Orchestrate CRUD tests for a resource type.

    :param context: The check context containing the SCIM client and configuration
    :param resource_type: The ResourceType object to test
    :returns: A list of check results for all tested operations
    """
    model = model_from_resource_type(context, resource_type)
    if not model:
        return [
            CheckResult(
                status=Status.ERROR,
                reason=f"No Schema matching the ResourceType {resource_type.id}",
            )
        ]

    results = []

    # Each test is now completely independent and handles its own cleanup
    # These functions have @checker decorators so we call them with client, conf
    # The decorator will create a context and call the function appropriately
    # For now, call them directly - may need adjustment based on actual function signatures
    results.append(check_object_creation(context, model))
    results.append(check_object_query(context, model))
    results.append(check_object_query_without_id(context, model))
    results.append(check_object_replacement(context, model))
    results.append(check_object_deletion(context, model))

    return results
