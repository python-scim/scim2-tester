"""PATCH operation checkers."""

import json
from typing import Any

from scim2_client import SCIMClientError
from scim2_models import Context
from scim2_models import Required
from scim2_models import Resource

from scim2_tester.utils import CheckContext
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status
from scim2_tester.utils import checker

from .test_cases import ExpectedResult
from .test_cases import PatchOp
from .test_cases import PatchTestCase
from .test_cases import generate_patch_test_cases


def _execute_patch_test_case(
    context: CheckContext,
    resource: Resource[Any],
    test_case: PatchTestCase,
) -> CheckResult:
    """Execute a single PATCH test case.

    :param context: The check context
    :param resource: The resource to patch
    :param test_case: The test case to execute
    :returns: The check result
    """
    # Build the PATCH operation as dict to bypass all client-side validation
    operation: dict[str, Any] = {
        "op": test_case.operation.value,
        "path": test_case.path,
    }
    if test_case.value is not None:
        # Convert Pydantic models to JSON-serializable format
        if hasattr(test_case.value, "model_dump_json"):
            # Use model_dump_json to handle all serialization including bytes to base64
            try:
                json_str = test_case.value.model_dump_json(
                    scim_ctx=Context.RESOURCE_PATCH_REQUEST
                )
                operation["value"] = json.loads(json_str)
            except TypeError:
                json_str = test_case.value.model_dump_json()
                operation["value"] = json.loads(json_str)
        elif (
            isinstance(test_case.value, list)
            and test_case.value
            and hasattr(test_case.value[0], "model_dump_json")
        ):
            try:
                operation["value"] = [
                    json.loads(
                        v.model_dump_json(scim_ctx=Context.RESOURCE_PATCH_REQUEST)
                    )
                    for v in test_case.value
                ]
            except TypeError:
                operation["value"] = [
                    json.loads(v.model_dump_json()) for v in test_case.value
                ]
        else:
            operation["value"] = test_case.value

    # Create patch payload directly as dict (no PatchOp object creation)
    patch_dict = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [operation],
    }

    try:
        # Execute the PATCH with dict payload to bypass validation
        context.client.modify(
            type(resource), resource.id, patch_dict, check_request_payload=False
        )

        # Check if we expected an error
        if test_case.expected_result != ExpectedResult.SUCCESS:
            # Special handling for extension root path removal
            if (
                test_case.is_extension_root
                and test_case.expected_result == ExpectedResult.ERROR_EXTENSION_REMOVAL
            ):
                # Server accepted extension root path deletion - this is the expected behavior
                return CheckResult(
                    status=Status.SUCCESS,
                    reason=f"Server correctly accepts root extension path deletion '{test_case.path}' - follows extensibility principles",
                    data={
                        "field": test_case.field_name,
                        "operation": test_case.operation.value,
                        "extension_path": test_case.path,
                    },
                )

            # Server accepted invalid operation - applies robustness principle but deviates from RFC
            return CheckResult(
                status=Status.DEVIATION,
                reason=f"{test_case.description} - Expected error but operation succeeded (server applies robustness principle)",
                data={
                    "field": test_case.field_name,
                    "operation": test_case.operation.value,
                    "expected": test_case.expected_result.value,
                    "got": "success",
                },
            )

        # Verify the operation succeeded as expected - RFC compliant behavior
        return CheckResult(
            status=Status.SUCCESS,
            reason=test_case.description,
            data={
                "field": test_case.field_name,
                "operation": test_case.operation.value,
            },
        )

    except SCIMClientError as e:
        # Check if error was expected
        if test_case.expected_result == ExpectedResult.SUCCESS:
            # Valid operation failed - violates RFC requirement
            return CheckResult(
                status=Status.ERROR,
                reason=f"{test_case.description} - Unexpected error: {str(e)}",
                data={
                    "field": test_case.field_name,
                    "operation": test_case.operation.value,
                    "expected": "success",
                    "got": str(e),
                    "response": e.source,
                },
            )

        # Special handling for extension root path removal
        if (
            test_case.is_extension_root
            and test_case.expected_result == ExpectedResult.ERROR_EXTENSION_REMOVAL
        ):
            # Server refused extension root path deletion - this is a DEVIATION
            return CheckResult(
                status=Status.DEVIATION,
                reason=f"Server refused root extension path deletion '{test_case.path}' - deviates from extensibility principles",
                data={
                    "field": test_case.field_name,
                    "operation": test_case.operation.value,
                    "extension_path": test_case.path,
                    "error": str(e),
                    "response": e.source,
                },
            )

        # Verify it's the right type of error
        error_type = _get_error_type(e)
        if not _is_expected_error_type(error_type, test_case.expected_result):
            # Server rejected operation but with wrong error type - still compliant behavior
            return CheckResult(
                status=Status.ACCEPTABLE,
                reason=f"{test_case.description} - Wrong error type but operation correctly rejected",
                data={
                    "field": test_case.field_name,
                    "operation": test_case.operation.value,
                    "expected_error": test_case.expected_result.value,
                    "got_error": error_type.value,
                    "response": e.source,
                },
            )

        # Error was expected and correct - RFC compliant behavior
        return CheckResult(
            status=Status.SUCCESS,
            reason=test_case.description,
            data={
                "field": test_case.field_name,
                "operation": test_case.operation.value,
                "expected_error": test_case.expected_result.value,
            },
        )


def _is_expected_error_type(actual: ExpectedResult, expected: ExpectedResult) -> bool:
    """Check if the actual error type matches the expected error type(s)."""
    if actual == expected:
        return True

    # Handle combined error types
    if expected == ExpectedResult.ERROR_MUTABILITY_OR_REQUIRED:
        return actual in (
            ExpectedResult.ERROR_MUTABILITY,
            ExpectedResult.ERROR_REQUIRED,
        )

    # Handle extension removal - can match various error types
    if expected == ExpectedResult.ERROR_EXTENSION_REMOVAL:
        return actual in (
            ExpectedResult.ERROR_EXTENSION_REMOVAL,
            ExpectedResult.ERROR_NOT_FOUND,
            ExpectedResult.ERROR_MUTABILITY,
        )

    return False


def _get_error_type(error: SCIMClientError) -> ExpectedResult:
    """Determine the error type from a SCIMClientError."""
    # Analyze the error response to determine type
    if hasattr(error, "source") and isinstance(error.source, dict):
        scim_type = error.source.get("scimType", "")
        detail = error.source.get("detail", "").lower()

        if (
            "mutability" in scim_type.lower()
            or "immutable" in detail
            or "read-only" in detail
            or "readOnly" in detail
        ):
            return ExpectedResult.ERROR_MUTABILITY
        elif "invalidvalue" in scim_type.lower() and "required" in detail:
            return ExpectedResult.ERROR_REQUIRED
        elif "uniqueness" in detail or "duplicate" in detail:
            return ExpectedResult.ERROR_UNIQUENESS
        elif "notfound" in scim_type.lower() or "not found" in detail:
            return ExpectedResult.ERROR_NOT_FOUND
        elif (
            "extension" in detail
            or "schema" in detail
            or "noTarget" in scim_type.lower()
        ):
            return ExpectedResult.ERROR_EXTENSION_REMOVAL

    # Default to generic error
    return ExpectedResult.ERROR_MUTABILITY


@checker("crud:patch", "constraints:mutability")
def check_patch_mutability(
    context: CheckContext, model: type[Resource[Any]] | None = None
) -> list[CheckResult]:
    """Test PATCH operations against mutability constraints.

    This checker comprehensively tests mutability rules for readOnly, writeOnly,
    readWrite, and immutable fields. It validates that operations succeed when
    allowed by the field's mutability setting and fail when violating constraints.

    Tests include ADD/REPLACE/REMOVE operations on all mutability types to ensure
    proper enforcement of SCIM mutability semantics.

    - :attr:`~scim2_tester.Status.SUCCESS`: PATCH operation correctly handled according to mutability rules
    - :attr:`~scim2_tester.Status.DEVIATION`: Server accepts invalid operation but applies robustness principle
    - :attr:`~scim2_tester.Status.ACCEPTABLE`: Server rejects operation with wrong error type but still enforces constraints
    - :attr:`~scim2_tester.Status.ERROR`: Valid operation failed unexpectedly or constraint violation not detected

    .. pull-quote:: :rfc:`RFC 7644 Section 3.5.2 - Modifying with PATCH <7644#section-3.5.2>`

       "Each attribute's mutability and required characteristics limit the
       attribute's modification. For example, a readOnly attribute cannot be
       modified, and a required attribute cannot be removed."
    """
    results = []

    # If model is provided directly, use it (called from check_resource_type)
    if model:
        resource_classes = [model]
    else:
        # Otherwise, test each configured resource type (called directly)
        resource_classes = []
        for resource_type in context.conf.resource_types or []:
            resource_class = context.client.get_resource_model(resource_type)
            if resource_class:
                resource_classes.append(resource_class)

    for resource_class in resource_classes:
        # Create a test resource
        test_resource = context.resource_manager.create_and_register(resource_class)

        # Generate and execute ALL mutability-related test cases
        test_cases = generate_patch_test_cases(context, resource_class, test_resource)

        # Filter cases related to mutability constraints
        mutability_cases = [
            tc
            for tc in test_cases
            if tc.expected_result
            in (
                ExpectedResult.ERROR_MUTABILITY,
                ExpectedResult.ERROR_MUTABILITY_OR_REQUIRED,
                ExpectedResult.SUCCESS,
            )
        ]

        # Execute each test case
        for test_case in mutability_cases:
            result = _execute_patch_test_case(context, test_resource, test_case)
            result.resource_type = getattr(resource_class, "__name__", "Unknown")
            results.append(result)

    return results


@checker("crud:patch", "constraints:required")
def check_patch_required(
    context: CheckContext, model: type[Resource[Any]] | None = None
) -> list[CheckResult]:
    """Test PATCH operations against required field constraints.

    This checker validates that required fields cannot be removed or set to null
    values via PATCH operations, while non-required fields can be safely removed.

    Tests include ADD, REPLACE, and REMOVE operations on both required and
    optional fields to ensure proper enforcement of field requirement constraints.

    - :attr:`~scim2_tester.Status.SUCCESS`: PATCH operation correctly handled according to required field rules
    - :attr:`~scim2_tester.Status.DEVIATION`: Server accepts invalid operation but applies robustness principle
    - :attr:`~scim2_tester.Status.ACCEPTABLE`: Server rejects operation with wrong error type but still enforces constraints
    - :attr:`~scim2_tester.Status.ERROR`: Valid operation failed unexpectedly or constraint violation not detected

    .. pull-quote:: :rfc:`RFC 7644 Section 3.5.2 - Modifying with PATCH <7644#section-3.5.2>`

       "A required attribute cannot be removed."
    """
    results = []

    # If model is provided directly, use it (called from check_resource_type)
    if model:
        resource_classes = [model]
    else:
        # Otherwise, test each configured resource type (called directly)
        resource_classes = []
        for resource_type in context.conf.resource_types or []:
            resource_class = context.client.get_resource_model(resource_type)
            if resource_class:
                resource_classes.append(resource_class)

    for resource_class in resource_classes:
        # Create a test resource
        test_resource = context.resource_manager.create_and_register(resource_class)

        # Generate and execute ALL required-related test cases
        test_cases = generate_patch_test_cases(context, resource_class, test_resource)

        # Filter cases related to required constraints
        required_cases = [
            tc
            for tc in test_cases
            if tc.expected_result
            in (
                ExpectedResult.ERROR_REQUIRED,
                ExpectedResult.ERROR_MUTABILITY_OR_REQUIRED,
            )
            or (tc.operation == PatchOp.REMOVE and tc.required == Required.false)
            or (
                tc.operation in (PatchOp.ADD, PatchOp.REPLACE)
                and tc.required == Required.true
                and tc.value is not None
            )
        ]

        # Execute each test case
        for test_case in required_cases:
            result = _execute_patch_test_case(context, test_resource, test_case)
            result.resource_type = getattr(resource_class, "__name__", "Unknown")
            results.append(result)

    return results


@checker("crud:patch", "constraints:uniqueness")
def check_patch_uniqueness(
    context: CheckContext, model: type[Resource[Any]] | None = None
) -> list[CheckResult]:
    """Test PATCH operations against uniqueness constraints.

    This checker validates that unique fields like userName and externalId
    cannot be set to duplicate values across resources of the same type.

    Tests attempt to create duplicate values for fields that typically have
    uniqueness constraints to ensure proper server-side validation. Note that
    uniqueness enforcement is a server implementation choice rather than a
    strict RFC requirement.

    - :attr:`~scim2_tester.Status.COMPLIANT`: Server correctly enforces uniqueness constraints (recommended behavior)
    - :attr:`~scim2_tester.Status.ACCEPTABLE`: Server rejects duplicate with different error type but still enforces uniqueness
    - :attr:`~scim2_tester.Status.DEVIATION`: Server allows duplicate values (applies robustness principle)

    .. pull-quote:: :rfc:`RFC 7643 Section 4.1.1 - userName <7643#section-4.1.1>`

       "A service provider's unique identifier for the user, typically used by
       the user to directly authenticate to the service provider."
    """
    results = []

    # If model is provided directly, use it (called from check_resource_type)
    if model:
        resource_classes = [model]
    else:
        # Otherwise, test each configured resource type (called directly)
        resource_classes = []
        for resource_type in context.conf.resource_types or []:
            resource_class = context.client.get_resource_model(resource_type)
            if resource_class:
                resource_classes.append(resource_class)

    for resource_class in resource_classes:
        # Focus on fields that typically have uniqueness constraints
        unique_fields = []
        class_name = getattr(resource_class, "__name__", "Unknown")
        if class_name == "User" and "user_name" in resource_class.model_fields:
            unique_fields.append("user_name")
        if "external_id" in resource_class.model_fields:
            unique_fields.append("external_id")

        if not unique_fields:
            continue

        # Create two test resources
        resource1 = context.resource_manager.create_and_register(resource_class)
        resource2 = context.resource_manager.create_and_register(resource_class)

        # Test uniqueness by trying to set resource2's unique fields to resource1's values
        for field_name in unique_fields:
            field_info = resource_class.model_fields[field_name]
            path = field_info.serialization_alias or field_name
            value1 = getattr(resource1, field_name)

            if value1 is None:
                continue

            # Try to set resource2's field to the same value
            operation = {"op": "replace", "path": path, "value": value1}

            # Create patch payload directly as dict to bypass all client-side validation
            patch_dict = {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "Operations": [operation],
            }

            try:
                context.client.modify(
                    type(resource2),
                    resource2.id,
                    patch_dict,
                    check_request_payload=False,
                )

                # If it succeeded, uniqueness is not enforced - deviation from best practices
                result = CheckResult(
                    status=Status.DEVIATION,
                    reason=f"Field '{field_name}' allowed duplicate value - uniqueness not enforced (server may apply robustness principle)",
                    data={
                        "field": field_name,
                        "duplicate_value": value1,
                        "resource_type": class_name,
                    },
                )

            except SCIMClientError as e:
                # Expected error - uniqueness is enforced
                error_type = _get_error_type(e)
                if error_type == ExpectedResult.ERROR_UNIQUENESS:
                    result = CheckResult(
                        status=Status.COMPLIANT,
                        reason=f"Field '{field_name}' correctly enforces uniqueness (follows RFC recommendations)",
                        data={"field": field_name, "resource_type": class_name},
                    )
                else:
                    result = CheckResult(
                        status=Status.ACCEPTABLE,
                        reason=f"Field '{field_name}' rejected duplicate but with different error type (still enforces uniqueness)",
                        data={
                            "field": field_name,
                            "expected_error": "uniqueness",
                            "got_error": error_type.value,
                            "resource_type": class_name,
                            "response": e.source,
                        },
                    )

            result.resource_type = class_name
            results.append(result)

    return results


@checker("crud:patch", "extensions")
def check_patch_extensions(
    context: CheckContext, model: type[Resource[Any]] | None = None
) -> list[CheckResult]:
    """Test PATCH operations on extension root paths.

    This checker validates server handling of REMOVE operations on root extension
    schema paths such as enterprise extension URNs.

    Tests ensure that servers properly handle extension root path deletions
    according to SCIM extensibility principles, where such operations should
    typically be accepted to maintain schema flexibility.

    - :attr:`~scim2_tester.Status.SUCCESS`: Server accepts extension root path deletion (follows extensibility principles)
    - :attr:`~scim2_tester.Status.DEVIATION`: Server refuses extension root path deletion (deviates from extensibility principles)

    .. pull-quote:: :rfc:`RFC 7644 Section 3.5.2.2 - Removing Attributes and Values <7644#section-3.5.2.2>`

       "Each PATCH operation represents a single action to be applied to the
       same SCIM resource specified by the request URI."
    """
    results = []

    # If model is provided directly, use it (called from check_resource_type)
    if model:
        resource_classes = [model]
    else:
        # Otherwise, test each configured resource type (called directly)
        resource_classes = []
        for resource_type in context.conf.resource_types or []:
            resource_class = context.client.get_resource_model(resource_type)
            if resource_class:
                resource_classes.append(resource_class)

    for resource_class in resource_classes:
        # Create a test resource
        test_resource = context.resource_manager.create_and_register(resource_class)

        # Generate extension root path test cases
        test_cases = generate_patch_test_cases(context, resource_class, test_resource)

        # Filter only extension root cases
        extension_cases = [tc for tc in test_cases if tc.is_extension_root]

        # Execute each extension test case
        for test_case in extension_cases:
            result = _execute_patch_test_case(context, test_resource, test_case)
            result.resource_type = getattr(resource_class, "__name__", "Unknown")
            results.append(result)

    return results
