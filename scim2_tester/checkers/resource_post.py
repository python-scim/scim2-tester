from typing import Any

from scim2_models import Resource

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import checker


@checker("crud:create")
def object_creation(context: CheckContext, model: type[Resource[Any]]) -> CheckResult:
    """Validate SCIM resource creation via POST requests.

    Tests that resources can be successfully created using POST method on the
    appropriate resource endpoint, with automatic cleanup after validation.
    Creates a test object with all required fields populated with valid data.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Resource created successfully with valid response
    - :attr:`~scim2_tester.Status.ERROR`: Creation failed due to client/server error

    .. pull-quote:: :rfc:`RFC 7644 Section 3.3 - Creating Resources <7644#section-3.3>`

       "To create new resources, clients send HTTP POST requests to the resource
       endpoint, such as ``/Users`` or ``/Groups``."

       "If the resource is successfully created, the server SHALL return a ``201``
       'Created' response code with the newly created resource."
    """
    created_obj = context.resource_manager.create_and_register(model)

    return CheckResult(
        status=Status.SUCCESS,
        reason=f"Successfully created {model.__name__} object with id {created_obj.id}",
        data=created_obj,
    )
