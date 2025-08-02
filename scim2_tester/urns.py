from collections.abc import Iterator
from inspect import isclass
from typing import Any

from scim2_models import BaseModel
from scim2_models import ComplexAttribute
from scim2_models import Extension
from scim2_models import Mutability
from scim2_models import Required
from scim2_models import Resource
from scim2_models.utils import _find_field_name
from scim2_models.utils import _to_camel


def iter_urns(
    model: type[Resource[Any] | Extension],
    required: list[Required] | None = None,
    mutability: list[Mutability] | None = None,
    include_subattributes: bool = True,
) -> Iterator[str]:
    """Iterate over URNs for attributes matching the specified criteria."""
    for field_name in model.model_fields:
        if field_name in ("meta", "id", "schemas"):
            continue

        # Check required filter
        if required is not None:
            field_required = model.get_field_annotation(field_name, Required)
            if field_required not in required:
                continue

        # Check mutability filter
        if mutability is not None:  # pragma: no cover
            field_mutability = model.get_field_annotation(field_name, Mutability)
            if field_mutability not in mutability:
                continue

        field_type = model.get_field_root_type(field_name)

        if issubclass(field_type, Extension):
            urn = field_type.model_fields["schemas"].default[0]
        elif issubclass(model, Extension):
            urn = model().get_attribute_urn(field_name)
        else:
            urn = _to_camel(field_name)

        yield urn

        is_complex = isclass(field_type) and issubclass(field_type, ComplexAttribute)
        if include_subattributes and is_complex:
            for sub_field_name in field_type.model_fields:
                sub_urn = f"{urn}.{_to_camel(sub_field_name)}"
                yield sub_urn


def iter_all_urns(
    model: type[Resource[Any]],
    required: list[Required] | None = None,
    mutability: list[Mutability] | None = None,
    include_subattributes: bool = True,
) -> Iterator[tuple[str, type[Resource[Any] | Extension]]]:
    """Iterate over ALL URNs from base model and all its extensions."""
    base_urns = iter_urns(
        model,
        required=required,
        mutability=mutability,
        include_subattributes=include_subattributes,
    )

    for urn in base_urns:
        yield (urn, model)

    if isclass(model) and issubclass(model, Resource):
        for extension_model in model.get_extension_models().values():
            ext_urns = iter_urns(
                extension_model,
                required=required,
                mutability=mutability,
                include_subattributes=include_subattributes,
            )

            for urn in ext_urns:
                yield (urn, extension_model)


def get_target_model_by_urn(
    model: type[BaseModel], urn: str
) -> tuple[type[BaseModel], str] | None:
    if ":" in urn and isclass(model) and issubclass(model, Resource | Extension):
        model_schema = model.model_fields["schemas"].default[0]

        if urn.startswith(model_schema):
            urn = urn.removeprefix(model_schema)
            urn = urn.removeprefix(":")

        elif issubclass(model, Resource):
            for (
                extension_schema,
                extension_model,
            ) in model.get_extension_models().items():
                if urn == extension_schema:
                    urn = extension_model.__name__
                elif urn.startswith(extension_schema):
                    model = extension_model
                    urn = urn.removeprefix(extension_schema)
                    urn = urn.removeprefix(":")

    if "." in urn:
        parts = urn.split(".")
        current_model = model

        for part in parts[:-1]:
            field_name = _find_field_name(current_model, part)
            if field_name is None:
                return None
            field_type = current_model.get_field_root_type(field_name)
            current_model = field_type

        last_part = parts[-1]
        field_name = _find_field_name(current_model, last_part)
        return current_model, field_name

    field_name = _find_field_name(model, urn)
    if field_name is None:
        return None
    return model, field_name


def get_attribute_type_by_urn(
    model: type[Resource[Any] | Extension], urn: str
) -> type | None:
    """Get the field type for a given URN path."""
    if target := get_target_model_by_urn(model, urn):
        model, field_name = target
        return model.get_field_root_type(field_name)

    return None


def get_annotation_by_urn(
    annotation_type: type, urn: str, model: type[Resource[Any] | Extension]
) -> Any:
    """Get annotation value for a given URN path."""
    if target := get_target_model_by_urn(model, urn):
        model, field_name = target
        return model.get_field_annotation(field_name, annotation_type)

    return None


def get_multiplicity_by_urn(
    model: type[Resource[Any] | Extension],
    urn: str,
) -> bool | None:
    if target := get_target_model_by_urn(model, urn):
        model, field_name = target
        return model.get_field_multiplicity(field_name)

    return None


def get_value_by_urn(obj: BaseModel, urn: str) -> Any:
    """Get value from resource using URN path."""
    if ":" in urn:
        model_schema = type(obj).model_fields["schemas"].default[0]

        if isinstance(obj, Resource | Extension) and urn.startswith(model_schema):
            urn = urn.removeprefix(model_schema)
            urn = urn.removeprefix(":")

        elif isinstance(obj, Resource):
            for (
                extension_schema,
                extension_model,
            ) in obj.get_extension_models().items():
                if urn == extension_schema:
                    urn = extension_model.__name__
                elif urn.startswith(extension_schema):
                    urn = urn.removeprefix(extension_schema)
                    urn = urn.removeprefix(":")
                    extension_obj = obj[extension_model]
                    if extension_obj is None:
                        return None
                    return get_value_by_urn(extension_obj, urn)

    if "." in urn:
        parts = urn.split(".")
        current_obj = obj

        for part in parts[:-1]:
            field_name = _find_field_name(type(current_obj), part)
            if field_name is None:
                return None

            sub_obj = getattr(current_obj, field_name)
            if sub_obj is None:
                return None
            current_obj = sub_obj

        last_part = parts[-1]
        field_name = _find_field_name(type(current_obj), last_part)
        if field_name is None:
            return None

        return getattr(current_obj, field_name)

    field_name = _find_field_name(type(obj), urn)
    if field_name is None:
        return None

    return getattr(obj, field_name)


def set_value_by_urn(obj: Resource[Any], urn: str, value: Any) -> None:
    if ":" in urn:
        model_schema = type(obj).model_fields["schemas"].default[0]

        if isinstance(obj, Resource | Extension) and urn.startswith(model_schema):
            urn = urn.removeprefix(model_schema).removeprefix(":")

        elif isinstance(obj, Resource):
            for extension_schema, extension_model in obj.get_extension_models().items():
                if urn == extension_schema:
                    obj[extension_model] = value
                    return
                elif urn.startswith(extension_schema):
                    sub_urn = urn.removeprefix(extension_schema).removeprefix(":")
                    if obj[extension_model] is None:
                        obj[extension_model] = extension_model()
                    return set_value_by_urn(obj[extension_model], sub_urn, value)

    if "." in urn:
        parts = urn.split(".")
        current_obj = obj

        for part in parts[:-1]:
            field_name = _find_field_name(type(current_obj), part)
            if field_name is None:
                return
            sub_obj = getattr(current_obj, field_name)
            if sub_obj is None:
                field_type = type(current_obj).get_field_root_type(field_name)
                sub_obj = field_type()
                setattr(current_obj, field_name, sub_obj)
            elif isinstance(sub_obj, list):
                # Cannot navigate into multi-valued attributes
                return
            current_obj = sub_obj

        last_part = parts[-1]
        field_name = _find_field_name(type(current_obj), last_part)
        setattr(current_obj, field_name, value)

    else:
        field_name = _find_field_name(type(obj), urn)
        if field_name:
            # Handle multivalued fields by wrapping single values in lists
            if (
                obj.get_field_multiplicity(field_name)
                and not isinstance(value, list)
                and value is not None
            ):
                value = [value]
            setattr(obj, field_name, value)
