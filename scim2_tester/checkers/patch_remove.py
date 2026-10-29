"""PATCH remove operation checkers for SCIM compliance testing."""

from collections.abc import Callable
from typing import Any

from scim2_client import SCIMClientException
from scim2_models import Mutability
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import Path
from scim2_models import Required
from scim2_models import Resource
from scim2_models import SCIMException

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import check_result
from ..utils import checker
from ..utils import parametrize
from ._required_utils import check_required_attributes


def _is_unassigned(value: Any) -> bool:
    """Tell whether a value stands for an unassigned attribute.

    Per RFC 7643 §2.5, an empty array is equivalent to an unassigned attribute.
    """
    return value is None or value == []


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
    config = context.client.provider.config
    if config and config.patch and not config.patch.supported:
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
        parametrize(Path, model).iter_paths(
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
        binding = path.resolve()
        mutability = binding.get_annotation(Mutability) if binding else None
        if initial_value is None:
            continue

        remove_op = parametrize(PatchOp, type(full_resource))(
            operations=[
                PatchOperation(
                    op=PatchOperation.Op.remove,
                    path=path,
                )
            ]
        )

        try:
            modify_result = context.client.modify(
                target=type(full_resource),
                id=full_resource.id,
                patch_op=remove_op,
            )
        except (SCIMClientException, SCIMException) as exc:
            results.append(
                check_result(
                    context,
                    status=Status.ERROR,
                    reason=f"Failed to remove attribute '{urn}': {exc}",
                    resource_type=model.__name__,
                    attribute=urn,
                    data={
                        "urn": urn,
                        "error": exc,
                        "initial_value": initial_value,
                    },
                )
            )
            continue

        modify_actual_value = (
            path.get(modify_result) if modify_result is not None else None
        )
        if mutability != Mutability.write_only and not _is_unassigned(
            modify_actual_value
        ):
            results.append(
                check_result(
                    context,
                    status=Status.ERROR,
                    reason=f"PATCH modify() did not remove attribute '{urn}'",
                    resource_type=model.__name__,
                    attribute=urn,
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
        except (SCIMClientException, SCIMException) as exc:
            results.append(
                check_result(
                    context,
                    status=Status.ERROR,
                    reason=f"Failed to query resource after remove on '{urn}': {exc}",
                    resource_type=model.__name__,
                    attribute=urn,
                    data={
                        "urn": urn,
                        "error": exc,
                        "initial_value": initial_value,
                    },
                )
            )
            continue

        actual_value = path.get(updated_resource)
        if mutability == Mutability.write_only or _is_unassigned(actual_value):
            results.append(
                check_result(
                    context,
                    status=Status.SUCCESS,
                    reason=f"Successfully removed attribute '{urn}'",
                    resource_type=model.__name__,
                    attribute=urn,
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
                    attribute=urn,
                    data={
                        "urn": urn,
                        "initial_value": initial_value,
                        "actual_value": actual_value,
                    },
                )
            )

    return results


@checker("patch:remove")
def check_remove_required_attribute(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate that PATCH rejects the removal of a required attribute.

    For each required attribute, creates a resource, then sends a PATCH remove
    operation on this attribute. Returns one result per attribute.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: The server answers 400 ``mutability``
    - :attr:`~scim2_tester.Status.DEVIATION`: The server answers 400 with another
      ``scimType`` or without one, another 4xx status, or an error without a SCIM body
    - :attr:`~scim2_tester.Status.ERROR`: The server removes the attribute, or answers 5xx
    - :attr:`~scim2_tester.Status.SKIPPED`: The resource has no required attribute to
      check, or PATCH is not supported

    .. pull-quote:: :rfc:`RFC 7644 Section 3.5.2.2 - Remove Operation <7644#section-3.5.2.2>`

       "If an attribute is removed or becomes unassigned and is defined as a
       required attribute or a read-only attribute, the server SHALL return an
       HTTP response status code and a JSON detail error response as defined in
       Section 3.12, with a "scimType" error code of "mutability"."
    """
    config = context.client.provider.config
    if config and config.patch and not config.patch.supported:
        return [
            check_result(
                context,
                status=Status.SKIPPED,
                reason="PATCH operations not supported by server",
            )
        ]

    def request_for(path: Path[Any], endpoint: str) -> tuple[str, Callable[[], Any]]:
        resource = context.resource_manager.create_and_register(model)
        url = f"{endpoint}/{resource.id}"
        patch_op = {
            "schemas": [PatchOp.__schema__],
            "Operations": [{"op": "remove", "path": str(path)}],
        }

        def send() -> Any:
            return context.client.modify(
                model,
                resource.id,
                patch_op,
                check_request_payload=False,
                expected_status_codes=None,
                raise_scim_errors=False,
                url=url,
            )

        return f"PATCH {url} removing {path}", send

    return check_required_attributes(
        context, model, "mutability", Status.DEVIATION, request_for
    )
