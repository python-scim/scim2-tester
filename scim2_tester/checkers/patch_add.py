"""PATCH add operation checkers for SCIM compliance testing."""

from typing import Any

from scim2_client import SCIMClientError
from scim2_models import Mutability
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import Required
from scim2_models import Resource
from scim2_models.path import Path

from ..filling import generate_random_value
from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import check_result
from ..utils import checker
from ..utils import fields_equality


@checker("patch:add")
def check_add_attribute(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Test PATCH add operation on all attributes (simple, complex, and extensions).

    Creates a minimal resource, then iterates over ALL possible URNs (base model,
    extensions, and sub-attributes) to test PATCH add operations systematically.
    Uses a unified approach that handles all attribute types consistently.

    **Tested Behavior:**
    - Adding new attribute values (simple, complex, and extension attributes)
    - Server accepts the PATCH request with correct URN paths for extensions
    - Response contains the added attribute with correct values

    **Status:**
    - :attr:`~scim2_tester.Status.SUCCESS`: Attribute successfully added
    - :attr:`~scim2_tester.Status.ERROR`: Failed to add attribute
    - :attr:`~scim2_tester.Status.SKIPPED`: No addable attributes found or PATCH not supported

    .. pull-quote:: :rfc:`RFC 7644 Section 3.5.2.1 - Add Operation <7644#section-3.5.2.1>`

       "The 'add' operation is used to add a new attribute and/or values to
       an existing resource."
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
            mutability=[
                Mutability.read_write,
                Mutability.write_only,
                Mutability.immutable,
            ],
            include_subattributes=False,
        )
    )

    if not all_paths:
        return [
            check_result(
                context,
                status=Status.SKIPPED,
                reason=f"No addable attributes found for {model.__name__}",
                resource_type=model.__name__,
            )
        ]

    base_resource = context.resource_manager.create_and_register(model)

    for path in all_paths:
        urn = str(path)
        patch_value = generate_random_value(context, path=path)
        mutability = path.get_annotation(Mutability)

        patch_op = PatchOp[type(base_resource)](
            operations=[
                PatchOperation(
                    op=PatchOperation.Op.add,
                    path=path,
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
                check_result(
                    context,
                    status=Status.ERROR,
                    reason=f"Failed to add attribute '{urn}': {exc}",
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
            modify_actual_value = path.get(modify_result)
            if mutability != Mutability.write_only and not fields_equality(
                patch_value, modify_actual_value
            ):
                results.append(
                    check_result(
                        context,
                        status=Status.ERROR,
                        reason=(
                            f"PATCH modify() returned unexpected value for '{urn}'.\n"
                            f"Patched value: {patch_value}\n"
                            f"Returned value: {modify_actual_value}"
                        ),
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
                check_result(
                    context,
                    status=Status.ERROR,
                    reason=f"Failed to query resource after add on '{urn}': {exc}",
                    resource_type=model.__name__,
                    data={
                        "urn": urn,
                        "error": exc,
                        "patch_value": patch_value,
                    },
                )
            )
            continue

        actual_value = path.get(updated_resource)

        if mutability == Mutability.write_only or fields_equality(
            patch_value, actual_value
        ):
            results.append(
                check_result(
                    context,
                    status=Status.SUCCESS,
                    reason=f"Successfully added attribute '{urn}'",
                    resource_type=model.__name__,
                    data={
                        "urn": urn,
                        "value": patch_value,
                    },
                )
            )
        else:
            results.append(
                check_result(
                    context,
                    status=Status.ERROR,
                    reason=(
                        f"Attribute '{urn}' was not added or has unexpected value\n"
                        f"Patched value: {patch_value}\n"
                        f"Returned value: {actual_value}"
                    ),
                    resource_type=model.__name__,
                    data={
                        "urn": urn,
                        "expected": patch_value,
                        "actual": actual_value,
                    },
                )
            )

    return results
