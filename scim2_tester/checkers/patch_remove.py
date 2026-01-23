"""PATCH remove operation checkers for SCIM compliance testing."""

from typing import Any

from scim2_client import SCIMClientError
from scim2_models import Mutability
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import Required
from scim2_models import Resource
from scim2_models.path import Path

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import check_result
from ..utils import checker


@checker("patch:remove")
def check_remove_attribute(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Test PATCH remove operation on all attributes (simple, complex, and extensions).

    Creates a resource with initial values, then iterates over ALL possible URNs
    (base model, extensions, and sub-attributes) to test PATCH remove operations
    systematically. Uses a unified approach that handles all attribute types consistently.

    **Tested Behavior:**
    - Removing attribute values (simple, complex, and extension attributes)
    - Server accepts the PATCH request with correct URN paths for extensions
    - Response contains the resource with removed attributes (null/missing)

    **Status:**
    - :attr:`~scim2_tester.Status.SUCCESS`: Attribute successfully removed
    - :attr:`~scim2_tester.Status.ERROR`: Failed to remove attribute or attribute still exists
    - :attr:`~scim2_tester.Status.SKIPPED`: No removable attributes found or PATCH not supported

    .. pull-quote:: :rfc:`RFC 7644 Section 3.5.2.2 - Remove Operation <7644#section-3.5.2.2>`

       "The 'remove' operation removes the value at the target location specified
       by the required attribute 'path'. The operation performs the following
       functions, depending on the target location specified by 'path'."
    """
    if (
        context.client.service_provider_config
        and not context.client.service_provider_config.patch.supported
    ):
        return [
            check_result(
                context,
                status=Status.SKIPPED,
                reason="PATCH operations not supported by server",
                resource_type=model.__name__,
            )
        ]

    results = []
    all_paths = list(
        Path[model].iter_paths(
            required=[Required.false],
            mutability=[Mutability.read_write, Mutability.write_only],
            include_subattributes=False,
        )
    )

    if not all_paths:
        return [
            check_result(
                context,
                status=Status.SKIPPED,
                reason=f"No removable attributes found for {model.__name__}",
                resource_type=model.__name__,
            )
        ]

    full_resource = context.resource_manager.create_and_register(model, fill_all=True)

    for path in all_paths:
        urn = str(path)
        initial_value = path.get(full_resource)
        mutability = path.get_annotation(Mutability)
        if initial_value is None:
            continue

        remove_op = PatchOp[type(full_resource)](
            operations=[
                PatchOperation(
                    op=PatchOperation.Op.remove,
                    path=path,
                )
            ]
        )

        try:
            modify_result = context.client.modify(
                resource_model=type(full_resource),
                id=full_resource.id,
                patch_op=remove_op,
            )
        except SCIMClientError as exc:
            results.append(
                check_result(
                    context,
                    status=Status.ERROR,
                    reason=f"Failed to remove attribute '{urn}': {exc}",
                    resource_type=model.__name__,
                    data={
                        "urn": urn,
                        "error": exc,
                        "initial_value": initial_value,
                    },
                )
            )
            continue

        if modify_result is not None:
            if modify_actual_value := path.get(modify_result):
                if (
                    mutability != Mutability.write_only
                    and modify_actual_value is not None
                ):
                    results.append(
                        check_result(
                            context,
                            status=Status.ERROR,
                            reason=f"PATCH modify() did not remove attribute '{urn}'",
                            resource_type=model.__name__,
                            data={
                                "urn": urn,
                                "initial_value": initial_value,
                                "modify_actual": modify_actual_value,
                            },
                        )
                    )
                    continue

        try:
            updated_resource = context.client.query(
                type(full_resource),
                full_resource.id,
            )
        except SCIMClientError as exc:
            results.append(
                check_result(
                    context,
                    status=Status.ERROR,
                    reason=f"Failed to query resource after remove on '{urn}': {exc}",
                    resource_type=model.__name__,
                    data={
                        "urn": urn,
                        "error": exc,
                        "initial_value": initial_value,
                    },
                )
            )
            continue

        actual_value = path.get(updated_resource)
        if mutability == Mutability.write_only or actual_value is None:
            results.append(
                check_result(
                    context,
                    status=Status.SUCCESS,
                    reason=f"Successfully removed attribute '{urn}'",
                    resource_type=model.__name__,
                    data={
                        "urn": urn,
                        "initial_value": initial_value,
                    },
                )
            )
        else:
            results.append(
                check_result(
                    context,
                    status=Status.ERROR,
                    reason=f"Attribute '{urn}' was not removed",
                    resource_type=model.__name__,
                    data={
                        "urn": urn,
                        "initial_value": initial_value,
                        "actual_value": actual_value,
                    },
                )
            )

    return results
