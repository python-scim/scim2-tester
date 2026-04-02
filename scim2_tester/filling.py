import base64
import random
import uuid
from enum import Enum
from inspect import isclass
from typing import TYPE_CHECKING
from typing import Any

from pydantic import Base64Bytes
from pydantic import BaseModel
from scim2_models import ComplexAttribute
from scim2_models import Extension
from scim2_models import Mutability
from scim2_models import Reference
from scim2_models import Required
from scim2_models import Resource
from scim2_models.path import Path

if TYPE_CHECKING:
    from scim2_tester.utils import CheckContext


def get_random_example_value(path: Path[Any]) -> Any | None:
    """Get a random value from pydantic field examples if available."""
    if path.model is None or path.field_name is None:
        return None

    field_info = path.model.model_fields.get(path.field_name)
    if not field_info or not hasattr(field_info, "examples") or not field_info.examples:
        return None

    return random.choice(field_info.examples)


def get_model_from_ref_type(
    context: "CheckContext",
    ref_type: type[Reference],
    different_than: type[Resource[Any]] | None,
) -> type[Resource[Any]]:
    """Return the Resource model referenced by a Reference type."""
    ref_names = ref_type.__reference_types__
    models = [context.client.get_resource_model(ref_name) for ref_name in ref_names]
    acceptable_models = [model for model in models if model != different_than]

    if not acceptable_models:
        return models[0]

    return acceptable_models[0]


def generate_random_value(
    context: "CheckContext",
    path: Path[Any],
    mutability: list[Mutability] | None = None,
    required: list[Required] | None = None,
) -> Any:
    """Generate a random value for the given path."""
    if mutability is not None:
        field_mutability = path.get_annotation(Mutability)
        if field_mutability not in mutability:
            return None

    if required is not None:
        field_required = path.get_annotation(Required)
        if field_required not in required:
            return None

    field_type = path.field_type
    model = path.model

    is_email = str(path).endswith("emails.value") or (
        path.field_name == "value" and model and "email" in model.__name__.lower()
    )
    is_phone = str(path).endswith("phoneNumbers.value") or (
        path.field_name == "value" and model and "phone" in model.__name__.lower()
    )

    value: Any

    if example_value := get_random_example_value(path):
        value = example_value

    # RFC7643 §4.1.2 provides the following indications, however
    # there is no way to guess the existence of such requirements
    # just by looking at the object schema.
    #     The value SHOULD be specified according to [RFC5321].
    elif is_email:
        value = f"{uuid.uuid4()}@{uuid.uuid4()}.com"

    # RFC7643 §4.1.2 provides the following indications, however
    # there is no way to guess the existence of such requirements
    # just by looking at the object schema.
    #     The value SHOULD be specified
    #     according to the format defined in [RFC3966], e.g.,
    #     'tel:+1-201-555-0123'.
    elif is_phone:  # pragma: no cover
        value = "".join(str(random.choice(range(10))) for _ in range(10))

    elif field_type is int:
        value = random.randint(0, 2**31 - 1)

    elif field_type is bool:
        value = random.choice([True, False])

    elif isclass(field_type) and issubclass(field_type, Reference):
        ref_types = field_type.__reference_types__
        if not ref_types or "external" in ref_types or "uri" in ref_types:
            value = f"https://{str(uuid.uuid4())}.test"
        else:
            ref_model = get_model_from_ref_type(
                context, field_type, different_than=model
            )
            ref_obj = context.resource_manager.create_and_register(ref_model)
            value = ref_obj.meta.location if ref_obj.meta else None

    elif isclass(field_type) and issubclass(field_type, Enum):
        value = random.choice(list(field_type))

    elif isclass(field_type) and issubclass(field_type, ComplexAttribute):
        value = fill_with_random_values(
            context, field_type(), mutability=mutability, required=required
        )  # type: ignore[arg-type]

    elif field_type is None and isclass(model) and issubclass(model, Extension):
        value = fill_with_random_values(
            context, model(), mutability=mutability, required=required
        )  # type: ignore[arg-type]

    elif field_type is Base64Bytes:
        value = base64.b64encode(uuid.uuid4().bytes).decode("ascii")

    else:
        value = str(uuid.uuid4())

    if path.is_multivalued:
        value = [value]

    return value


def fill_with_random_values(
    context: "CheckContext",
    obj: Resource[Any],
    paths: list[Path[Any]] | None = None,
    mutability: list[Mutability] | None = None,
    required: list[Required] | None = None,
) -> Resource[Any] | None:
    """Fill an object with random values generated according the attribute types.

    :param context: The check context containing the SCIM client and configuration
    :param obj: The Resource object to fill with random values
    :param paths: Optional list of Paths to fill
    :param mutability: Optional list of mutability constraints to filter fields
    :param required: Optional list of required constraints to filter fields
    :returns: The filled object or None if the object ends up empty
    """
    mutability = mutability or [
        Mutability.read_write,
        Mutability.write_only,
        Mutability.immutable,
    ]
    if paths is None:
        paths = list(
            Path[type(obj)].iter_paths(
                mutability=mutability,
                required=required,
            )
        )

    for path in paths:
        value = generate_random_value(
            context, path=path, mutability=mutability, required=required
        )
        if value is not None:
            path.set(obj, value, strict=False)

    fix_primary_attributes(obj)
    fix_reference_values(obj)

    return obj


def fix_reference_values(obj: BaseModel) -> None:
    """Recursively fix ref/value consistency on an object and its children.

    Walks the object tree and ensures that for any object with both
    ``ref`` and ``value`` attributes, ``value`` matches the last segment
    of the ``ref`` URL.
    """
    _fix_ref_value(obj)
    for field_name in type(obj).model_fields:
        child = getattr(obj, field_name, None)
        if child is None:
            continue

        if isinstance(child, list):
            for item in child:
                _fix_ref_value(item)
                if isinstance(item, BaseModel):
                    fix_reference_values(item)
        elif isinstance(child, BaseModel):
            _fix_ref_value(child)
            fix_reference_values(child)


def _fix_ref_value(obj: Any) -> None:
    """Set ``value`` to the last segment of ``ref`` if both attributes exist."""
    if hasattr(obj, "ref") and hasattr(obj, "value") and getattr(obj, "ref", None):
        obj.value = obj.ref.rsplit("/", 1)[-1]


def fix_primary_attributes(obj: Resource[Any]) -> None:
    """Fix primary attributes to respect RFC 7643 constraints.

    Ensures that for multi-valued attributes with 'primary' sub-attributes:
    - If the list has one item, sets primary=True
    - If the list has multiple items, exactly one has primary=True and others primary=False
    - If the list is empty, does nothing

    According to RFC 7643 §2.4: The primary attribute value "true" MUST appear no more than once.
    """
    for field_name in type(obj).model_fields:
        attr_value = getattr(obj, field_name, None)
        if not attr_value or not isinstance(attr_value, list) or len(attr_value) == 0:
            continue

        first_item = attr_value[0]
        if not hasattr(first_item, "primary"):
            continue

        primary_index = random.randint(0, len(attr_value) - 1)
        for i, item in enumerate(attr_value):
            item.primary = i == primary_index
