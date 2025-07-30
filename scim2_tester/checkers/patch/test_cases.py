"""PATCH test case generation utilities."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from scim2_models import Mutability
from scim2_models import Required
from scim2_models import Resource
from scim2_models.base import BaseModel

from scim2_tester.filling import generate_random_value
from scim2_tester.utils import CheckContext


class PatchOp(str, Enum):
    ADD = "add"
    REMOVE = "remove"
    REPLACE = "replace"


class ExpectedResult(str, Enum):
    SUCCESS = "success"
    ERROR_MUTABILITY = "mutability"
    ERROR_REQUIRED = "required"
    ERROR_UNIQUENESS = "uniqueness"
    ERROR_NOT_FOUND = "notFound"
    # Allow multiple acceptable error types
    ERROR_MUTABILITY_OR_REQUIRED = "mutability_or_required"
    # For extension path removal
    ERROR_EXTENSION_REMOVAL = "extension_removal"


@dataclass
class PatchTestCase:
    """A single PATCH test case."""

    field_name: str
    operation: PatchOp
    value: Any
    path: str
    expected_result: ExpectedResult
    mutability: Mutability
    required: Required
    description: str
    is_extension_root: bool = False


def generate_patch_test_cases(
    context: CheckContext,
    resource_class: type[Resource[Any]],
    resource: Resource[Any],
) -> list[PatchTestCase]:
    """Generate all PATCH test cases for a resource type.

    :param context: The check context
    :param resource_class: The resource class to test
    :param resource: An existing resource instance to test against
    :returns: List of test cases to execute
    """
    test_cases = []

    for field_name in resource_class.model_fields:
        # Skip meta and schemas fields as they're handled differently
        if field_name in ("meta", "schemas"):
            continue

        mutability = resource_class.get_field_annotation(field_name, Mutability)
        required = resource_class.get_field_annotation(field_name, Required)
        is_multi_valued = resource_class.get_field_multiplicity(field_name)

        # Generate test cases for each operation
        test_cases.extend(
            _generate_add_cases(
                context,
                resource_class,
                resource,
                field_name,
                mutability,
                required,
                is_multi_valued,
            )
        )
        test_cases.extend(
            _generate_remove_cases(resource_class, field_name, mutability, required)
        )
        test_cases.extend(
            _generate_replace_cases(
                context,
                resource_class,
                resource,
                field_name,
                mutability,
                required,
                is_multi_valued,
            )
        )

    # Add extension root path test cases
    test_cases.extend(_generate_extension_root_cases(resource_class))

    return test_cases


def _generate_add_cases(
    context: CheckContext,
    resource_class: type[Resource[Any]],
    resource: Resource[Any],
    field_name: str,
    mutability: Mutability,
    required: Required,
    is_multi_valued: bool,
) -> list[PatchTestCase]:
    """Generate ADD operation test cases."""
    cases = []
    value = generate_random_value(
        context, resource, context.resource_manager, field_name
    )
    # For multi-valued fields, wrap in a list
    if is_multi_valued and not isinstance(value, list):
        value = [value]

    path = _get_field_path(resource_class, field_name)

    # ADD on readWrite - should succeed
    if mutability == Mutability.read_write:
        cases.append(
            PatchTestCase(
                field_name=field_name,
                operation=PatchOp.ADD,
                value=value,
                path=path,
                expected_result=ExpectedResult.SUCCESS,
                mutability=mutability,
                required=required,
                description=f"ADD on readWrite field '{field_name}' should succeed",
            )
        )

    # ADD on readOnly - should fail
    elif mutability == Mutability.read_only:
        cases.append(
            PatchTestCase(
                field_name=field_name,
                operation=PatchOp.ADD,
                value=value,
                path=path,
                expected_result=ExpectedResult.ERROR_MUTABILITY,
                mutability=mutability,
                required=required,
                description=f"ADD on readOnly field '{field_name}' should fail",
            )
        )

    # ADD on immutable
    elif mutability == Mutability.immutable:
        # If field has no value, ADD should succeed
        if getattr(resource, field_name) is None:
            cases.append(
                PatchTestCase(
                    field_name=field_name,
                    operation=PatchOp.ADD,
                    value=value,
                    path=path,
                    expected_result=ExpectedResult.SUCCESS,
                    mutability=mutability,
                    required=required,
                    description=f"ADD on immutable field '{field_name}' without value should succeed",
                )
            )
        # If field has value, ADD should fail
        else:
            cases.append(
                PatchTestCase(
                    field_name=field_name,
                    operation=PatchOp.ADD,
                    value=value,
                    path=path,
                    expected_result=ExpectedResult.ERROR_MUTABILITY,
                    mutability=mutability,
                    required=required,
                    description=f"ADD on immutable field '{field_name}' with existing value should fail",
                )
            )

    # ADD on writeOnly - should succeed
    elif mutability == Mutability.write_only:
        cases.append(
            PatchTestCase(
                field_name=field_name,
                operation=PatchOp.ADD,
                value=value,
                path=path,
                expected_result=ExpectedResult.SUCCESS,
                mutability=mutability,
                required=required,
                description=f"ADD on writeOnly field '{field_name}' should succeed",
            )
        )

    return cases


def _generate_remove_cases(
    resource_class: type[Resource[Any]],
    field_name: str,
    mutability: Mutability,
    required: Required,
) -> list[PatchTestCase]:
    """Generate REMOVE operation test cases."""
    cases = []
    path = _get_field_path(resource_class, field_name)

    # REMOVE on readWrite
    if mutability == Mutability.read_write:
        if required == Required.true:
            # Cannot remove required field - RFC 7644 Section 3.5.2.2 vs general required logic
            # Both mutability and invalidValue errors are acceptable
            cases.append(
                PatchTestCase(
                    field_name=field_name,
                    operation=PatchOp.REMOVE,
                    value=None,
                    path=path,
                    expected_result=ExpectedResult.ERROR_MUTABILITY_OR_REQUIRED,
                    mutability=mutability,
                    required=required,
                    description=f"REMOVE on required field '{field_name}' should fail",
                )
            )
        else:
            # Can remove non-required field
            cases.append(
                PatchTestCase(
                    field_name=field_name,
                    operation=PatchOp.REMOVE,
                    value=None,
                    path=path,
                    expected_result=ExpectedResult.SUCCESS,
                    mutability=mutability,
                    required=required,
                    description=f"REMOVE on non-required readWrite field '{field_name}' should succeed",
                )
            )

    # REMOVE on readOnly - should fail
    elif mutability == Mutability.read_only:
        cases.append(
            PatchTestCase(
                field_name=field_name,
                operation=PatchOp.REMOVE,
                value=None,
                path=path,
                expected_result=ExpectedResult.ERROR_MUTABILITY,
                mutability=mutability,
                required=required,
                description=f"REMOVE on readOnly field '{field_name}' should fail",
            )
        )

    # REMOVE on immutable - should fail
    elif mutability == Mutability.immutable:
        cases.append(
            PatchTestCase(
                field_name=field_name,
                operation=PatchOp.REMOVE,
                value=None,
                path=path,
                expected_result=ExpectedResult.ERROR_MUTABILITY,
                mutability=mutability,
                required=required,
                description=f"REMOVE on immutable field '{field_name}' should fail",
            )
        )

    # REMOVE on writeOnly
    elif mutability == Mutability.write_only:
        if required == Required.true:
            cases.append(
                PatchTestCase(
                    field_name=field_name,
                    operation=PatchOp.REMOVE,
                    value=None,
                    path=path,
                    expected_result=ExpectedResult.ERROR_MUTABILITY_OR_REQUIRED,
                    mutability=mutability,
                    required=required,
                    description=f"REMOVE on required writeOnly field '{field_name}' should fail",
                )
            )
        else:
            cases.append(
                PatchTestCase(
                    field_name=field_name,
                    operation=PatchOp.REMOVE,
                    value=None,
                    path=path,
                    expected_result=ExpectedResult.SUCCESS,
                    mutability=mutability,
                    required=required,
                    description=f"REMOVE on non-required writeOnly field '{field_name}' should succeed",
                )
            )

    return cases


def _generate_replace_cases(
    context: CheckContext,
    resource_class: type[Resource[Any]],
    resource: Resource[Any],
    field_name: str,
    mutability: Mutability,
    required: Required,
    is_multi_valued: bool,
) -> list[PatchTestCase]:
    """Generate REPLACE operation test cases."""
    cases = []
    value = generate_random_value(
        context, resource, context.resource_manager, field_name
    )
    # For multi-valued fields, wrap in a list
    if is_multi_valued and not isinstance(value, list):
        value = [value]

    path = _get_field_path(resource_class, field_name)

    # REPLACE on readWrite - should succeed
    if mutability == Mutability.read_write:
        cases.append(
            PatchTestCase(
                field_name=field_name,
                operation=PatchOp.REPLACE,
                value=value,
                path=path,
                expected_result=ExpectedResult.SUCCESS,
                mutability=mutability,
                required=required,
                description=f"REPLACE on readWrite field '{field_name}' should succeed",
            )
        )

        # Test replacing with null on required field
        if required == Required.true:
            cases.append(
                PatchTestCase(
                    field_name=field_name,
                    operation=PatchOp.REPLACE,
                    value=None,
                    path=path,
                    expected_result=ExpectedResult.ERROR_MUTABILITY_OR_REQUIRED,
                    mutability=mutability,
                    required=required,
                    description=f"REPLACE with null on required field '{field_name}' should fail",
                )
            )

    # REPLACE on readOnly - should fail
    elif mutability == Mutability.read_only:
        cases.append(
            PatchTestCase(
                field_name=field_name,
                operation=PatchOp.REPLACE,
                value=value,
                path=path,
                expected_result=ExpectedResult.ERROR_MUTABILITY,
                mutability=mutability,
                required=required,
                description=f"REPLACE on readOnly field '{field_name}' should fail",
            )
        )

    # REPLACE on immutable - should fail
    elif mutability == Mutability.immutable:
        cases.append(
            PatchTestCase(
                field_name=field_name,
                operation=PatchOp.REPLACE,
                value=value,
                path=path,
                expected_result=ExpectedResult.ERROR_MUTABILITY,
                mutability=mutability,
                required=required,
                description=f"REPLACE on immutable field '{field_name}' should fail",
            )
        )

    # REPLACE on writeOnly - should succeed
    elif mutability == Mutability.write_only:
        cases.append(
            PatchTestCase(
                field_name=field_name,
                operation=PatchOp.REPLACE,
                value=value,
                path=path,
                expected_result=ExpectedResult.SUCCESS,
                mutability=mutability,
                required=required,
                description=f"REPLACE on writeOnly field '{field_name}' should succeed",
            )
        )

    return cases


def _get_field_path(resource_class: type[BaseModel], field_name: str) -> str:
    """Get the SCIM path for a field."""
    field_info = resource_class.model_fields[field_name]
    return field_info.serialization_alias or field_name


def _generate_extension_root_cases(
    resource_class: type[Resource[Any]],
) -> list[PatchTestCase]:
    """Generate test cases for extension root path removal.

    Tests REMOVE operations on root extension schema URNs like:
    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"

    :param resource_class: The resource class to test
    :returns: List of extension root test cases
    """
    cases = []

    # Get extension models for this resource class
    if hasattr(resource_class, "get_extension_models"):
        extension_models = resource_class.get_extension_models()
        if extension_models:
            for extension_class in extension_models.values():
                # Get the extension schema URN
                if (
                    hasattr(extension_class, "model_fields")
                    and "schemas" in extension_class.model_fields
                ):
                    schemas_field = extension_class.model_fields["schemas"]
                    if schemas_field.default:
                        extension_urn = schemas_field.default[0]

                        # Test REMOVE operation on extension root path
                        cases.append(
                            PatchTestCase(
                                field_name="extension_root",
                                operation=PatchOp.REMOVE,
                                value=None,
                                path=extension_urn,
                                expected_result=ExpectedResult.ERROR_EXTENSION_REMOVAL,
                                mutability=Mutability.read_write,  # Extensions are typically read_write
                                required=Required.false,  # Extensions are typically optional
                                description=f"REMOVE on extension root path '{extension_urn}' - server should accept (DEVIATION if refused)",
                                is_extension_root=True,
                            )
                        )

    return cases
