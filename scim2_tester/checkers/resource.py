from scim2_models import ResourceType

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from .resource_delete import object_deletion
from .resource_get import _model_from_resource_type
from .resource_get import object_query
from .resource_get import object_query_without_id
from .resource_post import object_creation
from .resource_put import object_replacement


def resource_type_tests(
    context: CheckContext,
    resource_type: ResourceType,
) -> list[CheckResult]:
    """Orchestrate comprehensive CRUD testing for a specific resource type.

    Runs the complete suite of CRUD operations (Create, Read, Update, Delete)
    on a given resource type to validate full lifecycle management compliance.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: All CRUD operations completed successfully
    - :attr:`~scim2_tester.Status.ERROR`: One or more CRUD operations failed or no schema found

    .. pull-quote:: :rfc:`RFC 7644 Section 3 - SCIM Protocol <7644#section-3>`

       "SCIM is intended to reduce the cost and complexity of user management
       operations by providing a common user schema and extension model, as
       well as binding documents to provide patterns for exchanging this schema
       using standard protocols."
    """
    model = _model_from_resource_type(context, resource_type)
    if not model:
        return [
            CheckResult(
                status=Status.ERROR,
                reason=f"No Schema matching the ResourceType {resource_type.id}",
            )
        ]

    results = []

    results.append(object_creation(context, model))
    results.append(object_query(context, model))
    results.append(object_query_without_id(context, model))
    results.append(object_replacement(context, model))
    results.append(object_deletion(context, model))

    return results
