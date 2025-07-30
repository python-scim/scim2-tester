from typing import Any

from scim2_models import Mutability
from scim2_models import Resource

from ..filling import fill_with_random_values
from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import checker


@checker("crud:update")
def object_replacement(
    context: CheckContext, model: type[Resource[Any]]
) -> CheckResult:
    """Validate SCIM resource replacement via PUT requests.

    Tests that resources can be successfully replaced using PUT method, modifying
    mutable fields and validating the complete resource replacement operation.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Resource replaced successfully with valid response
    - :attr:`~scim2_tester.Status.ERROR`: Replacement failed due to client/server error

    .. pull-quote:: :rfc:`RFC 7644 Section 3.5.1 - Replacing Resources <7644#section-3.5.1>`

       "To replace a resource's attributes, clients issue an HTTP PUT request
       to the resource endpoint (e.g., ``/Users/{id}`` or ``/Groups/{id}``)."

       "If successful, the server responds with HTTP status code 200 (OK) and
       includes the updated resource within the response body."
    """
    test_obj = context.resource_manager.create_and_register(model)

    mutable_fields = [
        field_name
        for field_name in model.model_fields.keys()
        if model.get_field_annotation(field_name, Mutability)
        in (Mutability.read_write, Mutability.write_only)
    ]

    modified_obj = fill_with_random_values(
        context, test_obj, context.resource_manager, mutable_fields
    )

    if modified_obj is None:
        raise ValueError(
            f"Could not modify {model.__name__} object with mutable fields"
        )

    response = context.client.replace(
        modified_obj, expected_status_codes=context.conf.expected_status_codes or [200]
    )

    return CheckResult(
        status=Status.SUCCESS,
        reason=f"Successfully replaced {model.__name__} object with id {test_obj.id}",
        data=response,
    )
