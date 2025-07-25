from scim2_models import ResourceType

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
    """Orchestrate CRUD tests for a resource type.

    :param conf: The check configuration containing the SCIM client
    :param resource_type: The ResourceType object to test
    :returns: A list of check results for all tested operations
    """
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

    # Each test is now completely independent and handles its own cleanup
    results.append(check_object_creation(conf, model))
    results.append(check_object_query(conf, model))
    results.append(check_object_query_without_id(conf, model))
    results.append(check_object_replacement(conf, model))
    results.append(check_object_deletion(conf, model))

    return results
