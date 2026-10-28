from typing import Any

from scim2_models import Resource

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import CreationNotSupportedError
from ..utils import Status
from ..utils import check_result
from ..utils import checker


@checker("crud:create")
def object_creation(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate SCIM resource creation via POST requests.

    Tests that resources can be successfully created using POST method on the
    appropriate resource endpoint, with automatic cleanup after validation.
    Creates a test object with all required fields populated with valid data.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Resource created successfully with valid response
    - :attr:`~scim2_tester.Status.ACCEPTABLE`: The server answers 501, as it does not support
      the creation of this resource type
    - :attr:`~scim2_tester.Status.ERROR`: Creation failed due to client/server error

    .. pull-quote:: :rfc:`RFC 7644 Section 3.3 - Creating Resources <7644#section-3.3>`

       "To create new resources, clients send HTTP POST requests to the resource
       endpoint, such as ``/Users`` or ``/Groups``."

       "If the resource is successfully created, the server SHALL return a ``201``
       'Created' response code with the newly created resource."

    .. pull-quote:: :rfc:`RFC 7644 Section 3.12 - HTTP Status and Error Response Handling <7644#section-3.12>`

       501 (Not Implemented): "Service provider does not support the request
       operation, e.g., PATCH."
    """
    try:
        created_obj = context.resource_manager.create_and_register(model)
    except CreationNotSupportedError as exc:
        return [check_result(context, status=Status.ACCEPTABLE, reason=str(exc))]

    return [
        check_result(
            context,
            status=Status.SUCCESS,
            reason=f"Successfully created {model.__name__} object with id {created_obj.id}",
            data=created_obj,
        )
    ]
