from typing import Any

from scim2_models import Resource

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import checker


@checker("crud:delete")
def object_deletion(context: CheckContext, model: type[Resource[Any]]) -> CheckResult:
    """Validate SCIM resource deletion via DELETE requests.

    Tests that resources can be successfully deleted using DELETE method and
    verifies that the resource no longer exists after deletion.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Resource deleted successfully and no longer accessible
    - :attr:`~scim2_tester.Status.ERROR`: Deletion failed or resource still exists after deletion

    .. pull-quote:: :rfc:`RFC 7644 Section 3.6 - Deleting Resources <7644#section-3.6>`

       "Clients request resource removal via HTTP DELETE requests to the
       resource endpoint (e.g., ``/Users/{id}`` or ``/Groups/{id}``)."

       "In response to a successful DELETE, the server SHALL return HTTP status
       code 204 (No Content)."
    """
    test_obj = context.resource_manager.create_and_register(model)

    if test_obj.id is not None:
        context.client.delete(
            model,
            test_obj.id,
            expected_status_codes=context.conf.expected_status_codes or [204],
        )

    try:
        context.client.query(model, test_obj.id)
        return CheckResult(
            status=Status.ERROR,
            reason=f"{model.__name__} object with id {test_obj.id} still exists after deletion",
        )
    except Exception:
        pass

    return CheckResult(
        status=Status.SUCCESS,
        reason=f"Successfully deleted {model.__name__} object with id {test_obj.id}",
    )
