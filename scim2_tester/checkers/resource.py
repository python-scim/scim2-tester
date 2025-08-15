from scim2_models import ResourceType

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import check_result
from .patch_add import check_add_attribute
from .patch_remove import check_remove_attribute
from .patch_replace import check_replace_attribute
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
            check_result(
                context,
                status=Status.ERROR,
                reason=f"No Schema matching the ResourceType {resource_type.id}",
            )
        ]

    results = []

    results.extend(object_creation(context, model))
    results.extend(object_query(context, model))
    results.extend(object_query_without_id(context, model))
    results.extend(object_replacement(context, model))
    results.extend(object_deletion(context, model))

    # PATCH operations
    results.extend(check_add_attribute(context, model))
    results.extend(check_remove_attribute(context, model))
    results.extend(check_replace_attribute(context, model))

    return results
