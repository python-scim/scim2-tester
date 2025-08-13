"""PATCH replace operation checkers for SCIM compliance testing."""

from typing import Any

from scim2_client import SCIMClientError
from scim2_models import Mutability
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import Resource

from ..filling import generate_random_value
from ..urns import get_annotation_by_urn
from ..urns import get_value_by_urn
from ..urns import iter_all_urns
from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import checker
from ..utils import compare_field


@checker("patch:replace")
def check_replace_attribute(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Test PATCH replace operation on all attributes (simple, complex, and extensions).

    Creates a resource with initial values, then iterates over ALL possible URNs
    (base model, extensions, and sub-attributes) to test PATCH replace operations
    systematically. Uses a unified approach that handles all attribute types consistently.

    **Tested Behavior:**
    - Replacing existing attribute values (simple, complex, and extension attributes)
    - Server accepts the PATCH request with correct URN paths for extensions
    - Response contains the replaced attribute with correct new values

    **Status:**
    - :attr:`~scim2_tester.Status.SUCCESS`: Attribute successfully replaced
    - :attr:`~scim2_tester.Status.ERROR`: Failed to replace attribute
    - :attr:`~scim2_tester.Status.SKIPPED`: No replaceable attributes found

    .. pull-quote:: :rfc:`RFC 7644 Section 3.5.2.3 - Replace Operation <7644#section-3.5.2.3>`

       "The 'replace' operation replaces the value at the target location
       specified by the 'path'."
    """
    results = []
    all_urns = list(
        iter_all_urns(
            model,
            mutability=[Mutability.read_write, Mutability.write_only],
            # Not supported until filters are implemented in scim2_models
            include_subattributes=False,
        )
    )

    if not all_urns:
        return [
            CheckResult(
                status=Status.SKIPPED,
                reason=f"No replaceable attributes found for {model.__name__}",
                resource_type=model.__name__,
            )
        ]

    base_resource = context.resource_manager.create_and_register(model)

    for urn, source_model in all_urns:
        patch_value = generate_random_value(context, urn=urn, model=source_model)
        mutability = get_annotation_by_urn(Mutability, urn, source_model)

        patch_op = PatchOp[type(base_resource)](
            operations=[
                PatchOperation(
                    op=PatchOperation.Op.replace_,
                    path=urn,
                    value=patch_value,
                )
            ]
        )

        try:
            modify_result = context.client.modify(
                resource_model=type(base_resource),
                id=base_resource.id,
                patch_op=patch_op,
            )
        except SCIMClientError as exc:
            results.append(
                CheckResult(
                    status=Status.ERROR,
                    reason=f"Failed to replace attribute '{urn}': {exc}",
                    resource_type=model.__name__,
                    data={
                        "urn": urn,
                        "error": exc,
                        "patch_value": patch_value,
                    },
                )
            )
            continue

        if modify_result is not None:
            if modify_actual_value := get_value_by_urn(modify_result, urn):
                if not (
                    mutability == Mutability.write_only
                    or compare_field(patch_value, modify_actual_value)
                ):
                    results.append(
                        CheckResult(
                            status=Status.ERROR,
                            reason=f"PATCH modify() returned incorrect value for '{urn}'",
                            resource_type=model.__name__,
                            data={
                                "urn": urn,
                                "expected": patch_value,
                                "modify_actual": modify_actual_value,
                            },
                        )
                    )
                    continue

        try:
            updated_resource = context.client.query(
                type(base_resource),
                base_resource.id,
            )
        except SCIMClientError as exc:
            results.append(
                CheckResult(
                    status=Status.ERROR,
                    reason=f"Failed to query resource after replace on '{urn}': {exc}",
                    resource_type=model.__name__,
                    data={
                        "urn": urn,
                        "error": exc,
                        "patch_value": patch_value,
                    },
                )
            )
            continue

        actual_value = get_value_by_urn(updated_resource, urn)
        if mutability == Mutability.write_only or compare_field(
            patch_value, actual_value
        ):
            results.append(
                CheckResult(
                    status=Status.SUCCESS,
                    reason=f"Successfully replaced attribute '{urn}'",
                    resource_type=model.__name__,
                    data={
                        "urn": urn,
                        "value": patch_value,
                    },
                )
            )
        else:
            results.append(
                CheckResult(
                    status=Status.ERROR,
                    reason=f"Attribute '{urn}' was not replaced or has incorrect value",
                    resource_type=model.__name__,
                    data={
                        "urn": urn,
                        "expected": patch_value,
                        "actual": actual_value,
                    },
                )
            )

    return results
