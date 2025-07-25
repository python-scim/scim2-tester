import base64
import random
import uuid
from enum import Enum
from inspect import isclass
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any
from typing import get_args
from typing import get_origin

from scim2_models import ComplexAttribute
from scim2_models import Extension
from scim2_models import ExternalReference
from scim2_models import Meta
from scim2_models import Reference
from scim2_models import Resource
from scim2_models import URIReference
from scim2_models.utils import UNION_TYPES

from scim2_tester.utils import CheckConfig

if TYPE_CHECKING:
    from scim2_tester.utils import ResourceManager


def model_from_ref_type(
    conf: CheckConfig, ref_type: type, different_than: type[Resource]
) -> type[Resource]:
    """Return "User" from "Union[Literal['User'], Literal['Group']]"."""

    def model_from_ref_type_(ref_type):
        if get_origin(ref_type) in UNION_TYPES:
            return [
                model_from_ref_type_(sub_ref_type)
                for sub_ref_type in get_args(ref_type)
            ]

        model_name = get_args(ref_type)[0]
        model = conf.client.get_resource_model(model_name)
        return model

    models = model_from_ref_type_(ref_type)
    models = models if isinstance(models, list) else [models]
    acceptable_models = [model for model in models if model != different_than]
    return acceptable_models[0]


def fill_with_random_values(
    conf: CheckConfig,
    obj: Resource,
    resource_manager: "ResourceManager",
    field_names: list[str] | None = None,
) -> Resource | None:
    """Fill an object with random values generated according the attribute types.

    :param conf: The check configuration containing the SCIM client
    :param obj: The Resource object to fill with random values
    :param resource_manager: Resource manager for automatic cleanup
    :param field_names: Optional list of field names to fill (defaults to all)
    :returns: The filled object or None if the object ends up empty
    """
    for field_name in field_names or obj.__class__.model_fields.keys():
        field = obj.__class__.model_fields[field_name]
        if field.default:
            continue

        is_multiple = obj.get_field_multiplicity(field_name)
        field_type = obj.get_field_root_type(field_name)
        if get_origin(field_type) == Annotated:
            field_type = get_args(field_type)[0]

        value: Any
        if field_type is Meta:
            value = None

        elif field.examples:
            value = random.choice(field.examples)

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

        elif field_type is int:
            value = uuid.uuid4().int

        elif field_type is bool:
            value = random.choice([True, False])

        elif field_type is bytes:
            value = base64.b64encode(str(uuid.uuid4()).encode("utf-8"))

        elif get_origin(field_type) is Reference:
            ref_type = get_args(field_type)[0]
            if ref_type not in (ExternalReference, URIReference):
                model = model_from_ref_type(
                    conf, ref_type, different_than=obj.__class__
                )
                ref_obj = resource_manager.create_and_register(model)
                value = ref_obj.meta.location

            else:
                value = f"https://{str(uuid.uuid4())}.test"

        elif isclass(field_type) and issubclass(field_type, Enum):
            value = random.choice(list(field_type))

        elif isclass(field_type) and issubclass(field_type, ComplexAttribute):
            value = fill_with_random_values(conf, field_type(), resource_manager)

        elif isclass(field_type) and issubclass(field_type, Extension):
            value = fill_with_random_values(conf, field_type(), resource_manager)

        else:
            # Put emails so this will be accepted by EmailStr too
            value = str(uuid.uuid4())

        if is_multiple:
            setattr(obj, field_name, [value])
        else:
            setattr(obj, field_name, value)

    return obj
