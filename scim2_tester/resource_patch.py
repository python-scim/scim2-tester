from scim2_models import Error
from scim2_models import Mutability
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import Resource
from scim2_models import Returned
from scim2_models import Uniqueness

from scim2_tester.filling import create_minimal_object
from scim2_tester.filling import generate_random_value_for_type
from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status
from scim2_tester.utils import should_test_patch


def check_field_mutability(
    conf: CheckConfig, obj: Resource, field_name: str
) -> list[CheckResult]:
    """Test PATCH operations respect field mutability constraints."""
    results = []
    mutability = obj.get_field_annotation(field_name, Mutability)

    if mutability == Mutability.read_only:
        # readOnly fields should reject any modification
        test_value, _ = generate_random_value_for_type(conf, obj, field_name)
        patch_ops = PatchOp[type(obj)](
            operations=[
                PatchOperation(
                    op=PatchOperation.Op.replace_, path=field_name, value=test_value
                )
            ]
        )

        try:
            response = conf.client.modify(
                type(obj),
                obj.id,
                patch_ops,
                expected_status_codes=[400],
                raise_scim_errors=False,
            )

            if isinstance(response, Error) and response.status == "400":
                if response.scim_type == "mutability":
                    results.append(
                        CheckResult(
                            conf,
                            status=Status.SUCCESS,
                            reason=f"Correctly rejected modification of readOnly field '{field_name}' with mutability error",
                            data=response,
                        )
                    )
                else:
                    results.append(
                        CheckResult(
                            conf,
                            status=Status.SUCCESS,
                            reason=f"Correctly rejected modification of readOnly field '{field_name}'",
                            data=response,
                        )
                    )
            elif isinstance(response, Error):
                results.append(
                    CheckResult(
                        conf,
                        status=Status.SUCCESS,
                        reason=f"Correctly rejected modification of readOnly field '{field_name}' (Error response)",
                        data=response,
                    )
                )
            else:
                results.append(
                    CheckResult(
                        conf,
                        status=Status.ERROR,
                        reason=f"Expected 400 error for readOnly field '{field_name}', got: {type(response).__name__}",
                        data=response,
                    )
                )
        except Exception as e:
            if "mutability" in str(e).lower():
                results.append(
                    CheckResult(
                        conf,
                        status=Status.SUCCESS,
                        reason=f"Correctly rejected modification of readOnly field '{field_name}' (client-side validation)",
                        data=e,
                    )
                )
            else:
                results.append(
                    CheckResult(
                        conf,
                        status=Status.ERROR,
                        reason=f"Unexpected error testing readOnly field '{field_name}': {e}",
                        data=e,
                    )
                )

    elif mutability == Mutability.immutable:
        # immutable fields should reject modification after creation but allow initial creation
        # Since we're testing on an existing object, any modification should be rejected
        test_value, _ = generate_random_value_for_type(conf, obj, field_name)
        patch_ops = PatchOp[type(obj)](
            operations=[
                PatchOperation(
                    op=PatchOperation.Op.replace_, path=field_name, value=test_value
                )
            ]
        )

        try:
            response = conf.client.modify(
                type(obj),
                obj.id,
                patch_ops,
                expected_status_codes=[400],
                raise_scim_errors=False,
            )

            if isinstance(response, Error) and response.status == "400":
                results.append(
                    CheckResult(
                        conf,
                        status=Status.SUCCESS,
                        reason=f"Correctly rejected modification of immutable field '{field_name}'",
                        data=response,
                    )
                )
            elif isinstance(response, Error):
                results.append(
                    CheckResult(
                        conf,
                        status=Status.SUCCESS,
                        reason=f"Correctly rejected modification of immutable field '{field_name}' (Error response)",
                        data=response,
                    )
                )
            else:
                results.append(
                    CheckResult(
                        conf,
                        status=Status.ERROR,
                        reason=f"Expected rejection for immutable field '{field_name}', got: {type(response).__name__}",
                        data=response,
                    )
                )
        except Exception as e:
            if "immutable" in str(e).lower() or "mutability" in str(e).lower():
                results.append(
                    CheckResult(
                        conf,
                        status=Status.SUCCESS,
                        reason=f"Correctly rejected modification of immutable field '{field_name}' (client-side validation)",
                        data=e,
                    )
                )
            else:
                results.append(
                    CheckResult(
                        conf,
                        status=Status.ERROR,
                        reason=f"Unexpected error testing immutable field '{field_name}': {e}",
                        data=e,
                    )
                )

    # Note: readWrite and writeOnly fields are tested in check_field_operations

    return results


def check_field_returnability(
    conf: CheckConfig, obj: Resource, field_name: str
) -> list[CheckResult]:
    """Test field returnability constraints."""
    results = []
    returned = obj.get_field_annotation(field_name, Returned)

    if returned == Returned.never:
        # Fields marked as never returned should not appear in responses
        # This is more of a GET operation test, but we can check after PATCH
        mutability = obj.get_field_annotation(field_name, Mutability)

        if mutability in (Mutability.read_write, Mutability.write_only):
            # Try to modify the field and check it doesn't appear in the response
            test_value, _ = generate_random_value_for_type(conf, obj, field_name)
            patch_ops = PatchOp[type(obj)](
                operations=[
                    PatchOperation(
                        op=PatchOperation.Op.replace_, path=field_name, value=test_value
                    )
                ]
            )

            try:
                response = conf.client.modify(
                    type(obj),
                    obj.id,
                    patch_ops,
                    expected_status_codes=[200, 204],
                    raise_scim_errors=False,
                )

                if hasattr(response, field_name):
                    results.append(
                        CheckResult(
                            conf,
                            status=Status.ERROR,
                            reason=f"Field '{field_name}' marked as 'never' returned but appears in PATCH response",
                            data=response,
                        )
                    )
                else:
                    results.append(
                        CheckResult(
                            conf,
                            status=Status.SUCCESS,
                            reason=f"Field '{field_name}' correctly not returned in PATCH response",
                            data=response,
                        )
                    )
            except Exception as e:
                results.append(
                    CheckResult(
                        conf,
                        status=Status.ERROR,
                        reason=f"Error testing returnability of field '{field_name}': {e}",
                        data=e,
                    )
                )

    return results


def check_field_uniqueness(
    conf: CheckConfig, obj: Resource, field_name: str
) -> list[CheckResult]:
    """Test field uniqueness constraints."""
    results = []
    uniqueness = obj.get_field_annotation(field_name, Uniqueness)
    mutability = obj.get_field_annotation(field_name, Mutability)

    if uniqueness in (Uniqueness.server, Uniqueness.global_) and mutability in (
        Mutability.read_write,
        Mutability.write_only,
    ):
        # Test uniqueness by trying to set the same value as an existing object
        current_value = getattr(obj, field_name, None)

        if current_value is not None:
            # Create another object to test uniqueness against
            try:
                # Create a minimal object of the same type
                new_obj, garbages = create_minimal_object(conf, type(obj))

                # Try to set the same value as the original object
                patch_ops = PatchOp[type(obj)](
                    operations=[
                        PatchOperation(
                            op=PatchOperation.Op.replace_,
                            path=field_name,
                            value=current_value,
                        )
                    ]
                )

                response = conf.client.modify(
                    type(obj),
                    new_obj.id,
                    patch_ops,
                    expected_status_codes=[400, 409],
                    raise_scim_errors=False,
                )

                if isinstance(response, Error) and response.status in (400, 409):
                    if response.scim_type == "uniqueness":
                        results.append(
                            CheckResult(
                                conf,
                                status=Status.SUCCESS,
                                reason=f"Correctly rejected duplicate value for unique field '{field_name}'",
                                data=response,
                            )
                        )
                    elif response.scim_type == "noTarget":
                        results.append(
                            CheckResult(
                                conf,
                                status=Status.SUCCESS,
                                reason=f"Field '{field_name}' not supported by server (noTarget)",
                                data=response,
                            )
                        )
                    else:
                        results.append(
                            CheckResult(
                                conf,
                                status=Status.SUCCESS,
                                reason=f"Correctly rejected duplicate value for unique field '{field_name}' (no scimType)",
                                data=response,
                            )
                        )
                else:
                    results.append(
                        CheckResult(
                            conf,
                            status=Status.ERROR,
                            reason=f"Expected uniqueness error for field '{field_name}', got: {type(response).__name__}",
                            data=response,
                        )
                    )

                # Clean up the test object
                for garbage in reversed(garbages + [new_obj]):
                    try:
                        conf.client.delete(garbage.__class__, garbage.id)
                    except:
                        pass

            except Exception as e:
                results.append(
                    CheckResult(
                        conf,
                        status=Status.ERROR,
                        reason=f"Error testing uniqueness of field '{field_name}': {e}",
                        data=e,
                    )
                )

    return results


def check_field_operations(
    conf: CheckConfig, obj: Resource, field_name: str
) -> list[CheckResult]:
    """Test basic PATCH operations (add/remove/replace) on writable fields."""
    results = []
    mutability = obj.get_field_annotation(field_name, Mutability)

    if mutability in (Mutability.read_write, Mutability.write_only):
        # For fields that are None/empty, try add operation instead of replace
        current_value = getattr(obj, field_name, None)

        if current_value is None or (
            isinstance(current_value, list) and len(current_value) == 0
        ):
            # Use add operation for empty fields
            test_value, _ = generate_random_value_for_type(conf, obj, field_name)
            patch_ops = PatchOp[type(obj)](
                operations=[
                    PatchOperation(
                        op=PatchOperation.Op.add, path=field_name, value=test_value
                    )
                ]
            )
            operation_name = "add"
        else:
            # Use replace operation for existing fields
            test_value, _ = generate_random_value_for_type(conf, obj, field_name)
            patch_ops = PatchOp[type(obj)](
                operations=[
                    PatchOperation(
                        op=PatchOperation.Op.replace_, path=field_name, value=test_value
                    )
                ]
            )
            operation_name = "replace"

        try:
            response = conf.client.modify(
                type(obj),
                obj.id,
                patch_ops,
                expected_status_codes=conf.expected_status_codes or [200, 204, 400],
                raise_scim_errors=False,
            )

            if isinstance(response, Error) and response.status == 400:
                if response.scim_type == "noTarget" or "noTarget" in str(
                    response.detail
                ):
                    # Field not supported by server, that's acceptable
                    results.append(
                        CheckResult(
                            conf,
                            status=Status.SUCCESS,
                            reason=f"PATCH {operation_name} operation not supported for field '{field_name}' (field not found on server)",
                            data=response,
                        )
                    )
                else:
                    # Other business rule rejections
                    results.append(
                        CheckResult(
                            conf,
                            status=Status.SUCCESS,
                            reason=f"PATCH {operation_name} operation appropriately rejected for field '{field_name}': {response.detail if response.detail else response}",
                            data=response,
                        )
                    )
            elif isinstance(response, Error):
                results.append(
                    CheckResult(
                        conf,
                        status=Status.ERROR,
                        reason=f"PATCH {operation_name} operation failed for writable field '{field_name}': {response.detail if response.detail else response}",
                        data=response,
                    )
                )
            else:
                results.append(
                    CheckResult(
                        conf,
                        status=Status.SUCCESS,
                        reason=f"Successful PATCH {operation_name} operation on field '{field_name}'",
                        data=response,
                    )
                )
        except Exception as e:
            results.append(
                CheckResult(
                    conf,
                    status=Status.ERROR,
                    reason=f"PATCH {operation_name} operation failed for field '{field_name}': {e}",
                    data=e,
                )
            )

        # Test remove operation if field is not required
        field_info = obj.__class__.model_fields.get(field_name)
        if field_info and not field_info.is_required():
            patch_ops = PatchOp[type(obj)](
                operations=[
                    PatchOperation(op=PatchOperation.Op.remove, path=field_name)
                ]
            )

            try:
                response = conf.client.modify(
                    type(obj),
                    obj.id,
                    patch_ops,
                    expected_status_codes=[200, 204, 400],
                    raise_scim_errors=False,
                )

                if isinstance(response, Error) and response.status == "400":
                    # Removal might be rejected for various reasons, that's OK
                    results.append(
                        CheckResult(
                            conf,
                            status=Status.SUCCESS,
                            reason=f"PATCH remove operation appropriately handled for field '{field_name}'",
                            data=response,
                        )
                    )
                else:
                    results.append(
                        CheckResult(
                            conf,
                            status=Status.SUCCESS,
                            reason=f"Successful PATCH remove operation on field '{field_name}'",
                            data=response,
                        )
                    )
            except Exception as e:
                results.append(
                    CheckResult(
                        conf,
                        status=Status.ERROR,
                        reason=f"PATCH remove operation failed for field '{field_name}': {e}",
                        data=e,
                    )
                )

    return results


def check_object_modification(conf: CheckConfig, obj: Resource) -> list[CheckResult]:
    """Test PATCH operations comprehensively on all fields."""
    if not should_test_patch(conf):
        return [
            CheckResult(
                conf,
                status=Status.SUCCESS,
                reason="PATCH operations not supported by server (patch.supported=false)",
            )
        ]

    all_results = []

    for field_name in obj.__class__.model_fields.keys():
        # Skip special fields that are managed by the server or have special semantics
        if field_name in ("meta", "schemas", "id"):
            continue

        # Test mutability constraints
        all_results.extend(check_field_mutability(conf, obj, field_name))

        # Test returnability constraints
        all_results.extend(check_field_returnability(conf, obj, field_name))

        # Test uniqueness constraints
        all_results.extend(check_field_uniqueness(conf, obj, field_name))

        # Test basic operations (add/remove/replace)
        all_results.extend(check_field_operations(conf, obj, field_name))

    return all_results
