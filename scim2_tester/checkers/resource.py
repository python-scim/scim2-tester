from scim2_models import ResourceType

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from .resource_delete import object_deletion
from .resource_get import model_from_resource_type
from .resource_get import object_query
from .resource_get import object_query_without_id
from .resource_post import object_creation
from .resource_put import object_replacement


def resource_type_tests(
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
    results.append(object_creation(context, model))
    results.append(object_query(context, model))
    results.append(object_query_without_id(context, model))
    results.append(object_replacement(context, model))
    results.append(object_deletion(context, model))

    return results
