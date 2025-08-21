from typing import Any

from scim2_models import Mutability
from scim2_models import Resource

from ..filling import fill_with_random_values
from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import check_result
from ..utils import checker


@checker("crud:update")
def object_replacement(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
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

    # Dirty hotfix, waiting to path management in scim2-models
    # to have a more generic way to do things
    # https://github.com/python-scim/scim2-models/issues/111
    # Store original immutable values to preserve them
    original_immutable_values = {}
    for field_name, field_info in model.model_fields.items():  # pragma: no cover
        # Check if field is immutable
        is_immutable = any(
            isinstance(metadata, Mutability) and metadata == Mutability.immutable
            for metadata in field_info.metadata
        )
        if is_immutable:
            original_value = getattr(test_obj, field_name, None)
            if original_value is not None:
                original_immutable_values[field_name] = original_value

    modified_obj = fill_with_random_values(
        context,
        test_obj,
        mutability=[Mutability.read_write, Mutability.write_only, Mutability.immutable],
    )

    # Dirty hotfix, waiting to path management in scim2-models
    # to have a more generic way to do things
    # https://github.com/python-scim/scim2-models/issues/111
    # Restore original immutable values for non-complex fields
    if modified_obj is not None:
        for (
            field_name,
            original_value,
        ) in original_immutable_values.items():  # pragma: no cover
            # Only restore if it's not a complex list (like members)
            if not (
                isinstance(original_value, list)
                and original_value
                and hasattr(original_value[0], "__class__")
                and hasattr(original_value[0].__class__, "model_fields")
            ):
                setattr(modified_obj, field_name, original_value)

    if modified_obj is None:
        raise ValueError(
            f"Could not modify {model.__name__} object with mutable fields"
        )

    response = context.client.replace(
        modified_obj, expected_status_codes=context.conf.expected_status_codes or [200]
    )

    return [
        check_result(
            context,
            status=Status.SUCCESS,
            reason=f"Successfully replaced {model.__name__} object with id {test_obj.id}",
            data=response,
        )
    ]
