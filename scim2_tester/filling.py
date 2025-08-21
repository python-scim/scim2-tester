import base64
import random
import uuid
from enum import Enum
from inspect import isclass
from typing import TYPE_CHECKING
from typing import Any
from typing import get_args
from typing import get_origin

from scim2_models import ComplexAttribute
from scim2_models import Extension
from scim2_models import ExternalReference
from scim2_models import Mutability
from scim2_models import Reference
from scim2_models import Required
from scim2_models import Resource
from scim2_models import URIReference
from scim2_models.utils import UNION_TYPES
from scim2_models.utils import Base64Bytes
from scim2_models.utils import _find_field_name

from scim2_tester.urns import get_annotation_by_urn
from scim2_tester.urns import get_attribute_type_by_urn
from scim2_tester.urns import get_multiplicity_by_urn
from scim2_tester.urns import get_target_model_by_urn
from scim2_tester.urns import iter_all_urns
from scim2_tester.urns import set_value_by_urn

if TYPE_CHECKING:
    from scim2_tester.utils import CheckContext


def get_random_example_value(model: type[Resource], urn: str) -> Any | None:
    """Get a random value from pydantic field examples if available."""
    target_info = get_target_model_by_urn(model, urn)
    if not target_info:
        return None

    target_model, target_field_name = target_info
    field_info = target_model.model_fields.get(target_field_name)
    if not field_info or not hasattr(field_info, "examples") or not field_info.examples:
        return None

    return random.choice(field_info.examples)


def get_model_from_ref_type(
    context: "CheckContext", ref_type: type, different_than: type[Resource[Any]] | None
) -> type[Resource[Any]]:
    """Return "User" from "Union[Literal['User'], Literal['Group']]"."""

    def get_model_from_ref_type_(ref_type: type) -> Any:
        if get_origin(ref_type) in UNION_TYPES:
            return [
                get_model_from_ref_type_(sub_ref_type)
                for sub_ref_type in get_args(ref_type)
            ]

        model_name = get_args(ref_type)[0]
        model = context.client.get_resource_model(model_name)
        return model

    models = get_model_from_ref_type_(ref_type)
    models = models if isinstance(models, list) else [models]
    acceptable_models = [model for model in models if model != different_than]

    if not acceptable_models:
        return models[0]

    return acceptable_models[0]


def generate_random_value(
    context: "CheckContext",
    urn: str,
    model: type[Resource],
    mutability: list[Mutability] | None = None,
    required: list[Required] | None = None,
) -> Any:
    if mutability is not None:
        field_mutability = get_annotation_by_urn(Mutability, urn, model)
        if field_mutability not in mutability:
            return None

    if required is not None:
        field_required = get_annotation_by_urn(Required, urn, model)
        if field_required not in required:
            return None

    field_name = _find_field_name(model, urn)
    field_type = get_attribute_type_by_urn(model, urn)
    is_multiple = get_multiplicity_by_urn(model, urn)

    is_email = urn and (
        urn.endswith("emails.value")
        or (field_name == "value" and "email" in model.__name__.lower())
    )
    is_phone = urn and (
        urn.endswith("phoneNumbers.value")
        or (field_name == "value" and "phone" in model.__name__.lower())
    )

    value: Any

    if example_value := get_random_example_value(model, urn):
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
        value = uuid.uuid4().int

    elif field_type is bool:
        value = random.choice([True, False])

    elif get_origin(field_type) is Reference and get_args(field_type)[0] != Any:
        ref_type = get_args(field_type)[0]
        if ref_type not in (ExternalReference, URIReference):
            model = get_model_from_ref_type(context, ref_type, different_than=model)
            ref_obj = context.resource_manager.create_and_register(model)
            value = ref_obj.meta.location if ref_obj.meta else None

        else:
            value = f"https://{str(uuid.uuid4())}.test"

    elif isclass(field_type) and issubclass(field_type, Enum):
        value = random.choice(list(field_type))

    elif isclass(field_type) and issubclass(field_type, ComplexAttribute):
        value = fill_with_random_values(
            context, field_type(), mutability=mutability, required=required
        )  # type: ignore[arg-type]

    elif isclass(field_type) and issubclass(field_type, Extension):
        value = fill_with_random_values(
            context, field_type(), mutability=mutability, required=required
        )  # type: ignore[arg-type]

    elif field_type is Base64Bytes:
        value = base64.b64encode(uuid.uuid4().bytes).decode("ascii")

    else:
        value = str(uuid.uuid4())

    if is_multiple:
        value = [value]

    return fix_reference_values_in_value(value)


def fill_with_random_values(
    context: "CheckContext",
    obj: Resource[Any],
    urns: list[str] | None = None,
    mutability: list[Mutability] | None = None,
    required: list[Required] | None = None,
) -> Resource[Any] | None:
    """Fill an object with random values generated according the attribute types.

    :param context: The check context containing the SCIM client and configuration
    :param obj: The Resource object to fill with random values
    :param urns: Optional list of URNs to fill (for backward compatibility)
    :param mutability: Optional list of mutability constraints to filter fields
    :param required: Optional list of required constraints to filter fields
    :returns: The filled object or None if the object ends up empty
    """
    mutability = mutability or [
        Mutability.read_write,
        Mutability.write_only,
        Mutability.immutable,
    ]
    if urns is None:
        urns = [
            urn
            for urn, _ in iter_all_urns(
                type(obj),
                mutability=mutability,
                required=required,
            )
        ]

    for urn in urns:
        value = generate_random_value(
            context, urn=urn, model=type(obj), mutability=mutability, required=required
        )
        if value is not None:
            set_value_by_urn(obj, urn, value)

    fix_primary_attributes(obj)

    return obj


def fix_reference_values_in_value(value: Any) -> Any:
    """Fix reference values in any value to extract IDs from reference URLs.

    For SCIM reference fields, correctly sets the value field to match
    the ID extracted from the reference URL. Works with both single values
    and lists containing reference objects.
    """
    if isinstance(value, list):
        for item in value:
            if (
                hasattr(item, "ref")
                and hasattr(item, "value")
                and getattr(item, "ref", None)
            ):
                item.value = item.ref.rsplit("/", 1)[-1]
    elif (
        hasattr(value, "ref")
        and hasattr(value, "value")
        and getattr(value, "ref", None)
    ):
        value.value = value.ref.rsplit("/", 1)[-1]

    return value


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
