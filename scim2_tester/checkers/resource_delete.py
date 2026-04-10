from typing import Any

from scim2_models import Error
from scim2_models import Resource

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import check_result
from ..utils import checker


@checker("crud:delete")
def object_deletion(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate SCIM resource deletion via DELETE requests.

    Tests that resources can be successfully deleted using DELETE method and
    verifies that the server returns HTTP 404 when attempting to retrieve the
    deleted resource.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Resource deleted successfully and server returns 404 on retrieval
    - :attr:`~scim2_tester.Status.ERROR`: Deletion failed, resource still exists, or server does not return 404

    .. pull-quote:: :rfc:`RFC 7644 Section 3.6 - Deleting Resources <7644#section-3.6>`

       "Clients request resource removal via HTTP DELETE requests to the
       resource endpoint (e.g., ``/Users/{id}`` or ``/Groups/{id}``)."

       "In response to a successful DELETE, the server SHALL return HTTP status
       code 204 (No Content)."

       "If a client sends a retrieval request and the consumer has been
       deleted, the server responds with HTTP status code 404."
    """
    test_obj = context.resource_manager.create_and_register(model)

    context.client.delete(
        model,
        test_obj.id,
        expected_status_codes=context.conf.expected_status_codes or [204],
    )

    response = context.client.query(
        model,
        test_obj.id,
        raise_scim_errors=False,
        expected_status_codes=None,
    )

    if not isinstance(response, Error):
        return [
            check_result(
                context,
                status=Status.ERROR,
                reason=f"{model.__name__} object with id {test_obj.id} still exists after deletion",
            )
        ]

    if response.status != 404:
        return [
            check_result(
                context,
                status=Status.ERROR,
                reason=f"Server returned {response.status} instead of 404 when retrieving deleted {model.__name__} object with id {test_obj.id}",
            )
        ]

    return [
        check_result(
            context,
            status=Status.SUCCESS,
            reason=f"Successfully deleted {model.__name__} object with id {test_obj.id}",
        )
    ]
