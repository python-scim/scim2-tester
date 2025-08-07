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
from scim2_models import Resource
from scim2_models import URIReference
from scim2_models.utils import UNION_TYPES

from scim2_tester.utils import CheckContext

if TYPE_CHECKING:
    pass


def model_from_ref_type(
    context: CheckContext, ref_type: type, different_than: type[Resource[Any]]
) -> type[Resource[Any]]:
    """Return "User" from "Union[Literal['User'], Literal['Group']]"."""

    def model_from_ref_type_(ref_type: type) -> Any:
        if get_origin(ref_type) in UNION_TYPES:
            return [
                model_from_ref_type_(sub_ref_type)
                for sub_ref_type in get_args(ref_type)
            ]

        model_name = get_args(ref_type)[0]
        model = context.client.get_resource_model(model_name)
        return model

    models = model_from_ref_type_(ref_type)
    models = models if isinstance(models, list) else [models]
    acceptable_models = [model for model in models if model != different_than]
    return acceptable_models[0]


def generate_random_value(
    context: CheckContext,
    obj: Resource[Any],
    field_name: str,
    ref_objs: dict[str, Resource[Any]],
) -> Any:
    field_type = obj.get_field_root_type(field_name)

    value: Any
    if obj.get_field_annotation(field_name, Mutability) == Mutability.read_only:
        value = None

    # RFC7643 §4.1.2 provides the following indications, however
    # there is no way to guess the existence of such requirements
    # just by looking at the object schema.
    #     The value SHOULD be specified according to [RFC5321].
    elif field_name == "value" and "email" in obj.__class__.__name__.lower():
        value = f"{uuid.uuid4()}@{uuid.uuid4()}.com"

    # RFC7643 §4.1.2 provides the following indications, however
    # there is no way to guess the existence of such requirements
    # just by looking at the object schema.
    #     The value SHOULD be specified
    #     according to the format defined in [RFC3966], e.g.,
    #     'tel:+1-201-555-0123'.
    elif field_name == "value" and "phone" in obj.__class__.__name__.lower():
        value = "".join(str(random.choice(range(10))) for _ in range(10))

    elif field_name == "value" and obj.__class__.__name__.lower() in ref_objs:
        value = ref_objs[obj.__class__.__name__.lower()].id

    elif field_name == "type" and obj.__class__.__name__.lower() in ref_objs:
        value = ref_objs[obj.__class__.__name__.lower()].meta.resource_type

    elif (
        field_name == "display" or field_name == "display_name"
    ) and obj.__class__.__name__.lower() in ref_objs:
        value = ref_objs[obj.__class__.__name__.lower()].display_name

    elif field_type is int:
        value = uuid.uuid4().int

    elif field_type is bool:
        value = random.choice([True, False])

    elif get_origin(field_type) is Reference and get_args(field_type)[0] != Any:
        ref_type = get_args(field_type)[0]
        if ref_type not in (ExternalReference, URIReference):
            if obj.__class__.__name__.lower() in ref_objs:
                value = ref_objs[obj.__class__.__name__.lower()].meta.location

        else:
            value = f"https://{str(uuid.uuid4())}.test"

    elif isclass(field_type) and issubclass(field_type, Enum):
        value = random.choice(list(field_type))

    elif isclass(field_type) and issubclass(field_type, ComplexAttribute):
        value = fill_with_random_values(context, field_type())

    elif isclass(field_type) and issubclass(field_type, Extension):
        value = fill_with_random_values(context, field_type())

    else:
        # Put emails so this will be accepted by EmailStr too
        value = str(uuid.uuid4())
    return value


def create_ref_object(
    context: CheckContext,
    obj: Resource[Any],
    field_name: str,
) -> dict[str, Resource[Any]] | None:
    field_type = obj.get_field_root_type(field_name)
    if get_origin(field_type) is Reference and get_args(field_type)[0] != Any:
        ref_type = get_args(field_type)[0]
        if ref_type not in (ExternalReference, URIReference):
            model = model_from_ref_type(context, ref_type, different_than=obj.__class__)
            return context.resource_manager.create_and_register(model)

    return None


def fill_with_random_values(
    context: CheckContext,
    obj: Resource[Any],
    field_names: list[str] | None = None,
) -> Resource[Any] | None:
    """Fill an object with random values generated according the attribute types.

    :param context: The check context containing the SCIM client and configuration
    :param obj: The Resource object to fill with random values
    :param field_names: Optional list of field names to fill (defaults to all)
    :returns: The filled object or None if the object ends up empty
    """
    ref_objs = {}
    for field_name in (
        field_names if field_names is not None else obj.__class__.model_fields.keys()
    ):
        if field_name not in obj.__class__.model_fields:
            continue

        field = obj.__class__.model_fields[field_name]
        if field.default:
            continue

        ref_obj = create_ref_object(context, obj, field_name)
        if ref_obj is not None:
            ref_objs[obj.__class__.__name__.lower()] = ref_obj

    for field_name in (
        field_names if field_names is not None else obj.__class__.model_fields.keys()
    ):
        if field_name not in obj.__class__.model_fields:
            continue

        field = obj.__class__.model_fields[field_name]
        if field.default:
            continue

        value = generate_random_value(context, obj, field_name, ref_objs)

        is_multiple = obj.get_field_multiplicity(field_name)
        if is_multiple:
            setattr(obj, field_name, [value])
        else:
            setattr(obj, field_name, value)

    return obj
