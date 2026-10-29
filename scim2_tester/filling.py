import base64
from enum import Enum
from inspect import isclass
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeGuard
from typing import TypeVar

from pydantic import BaseModel
from scim2_models import ComplexAttribute
from scim2_models import Extension
from scim2_models import Mutability
from scim2_models import Path
from scim2_models import Reference
from scim2_models import Required
from scim2_models import Resource

from scim2_tester.utils import parametrize

if TYPE_CHECKING:
    from scim2_tester.utils import CheckContext

ModelT = TypeVar("ModelT", bound=BaseModel)


def get_random_example_value(context: "CheckContext", path: Path[Any]) -> Any | None:
    """Get a random value from pydantic field examples if available."""
    binding = path.resolve()
    if binding is None or binding.target_model is None:
        return None

    field_info = binding.target_model.model_fields.get(binding.target_field_name)
    if not field_info or not hasattr(field_info, "examples") or not field_info.examples:
        return None

    return context.random.choice(field_info.examples)


def get_model_from_ref_type(
    context: "CheckContext",
    ref_type: type[Reference[Any]],
    different_than: type[BaseModel] | None,
) -> type[Resource[Any]]:
    """Return the Resource model referenced by a Reference type."""
    ref_names = ref_type.__reference_types__
    models = [
        model
        for ref_name in ref_names
        if (model := context.client.get_resource_model(ref_name)) is not None
    ]
    if not models:
        raise ValueError(f"No resource model is known for the references {ref_names}")

    acceptable_models = [model for model in models if model != different_than]

    if not acceptable_models:
        return models[0]

    return acceptable_models[0]


def _references_resources(field_type: Any) -> TypeGuard[type[Reference[Any]]]:
    """Tell whether a type is a reference to SCIM resources."""
    if not (isclass(field_type) and issubclass(field_type, Reference)):
        return False

    ref_types = field_type.__reference_types__
    return bool(ref_types) and "external" not in ref_types and "uri" not in ref_types


def _create_referenced_resource(
    context: "CheckContext",
    ref_type: type[Reference[Any]],
    different_than: type[BaseModel] | None,
) -> str | None:
    """Create a resource that a reference type can point to, and return its location."""
    ref_model = get_model_from_ref_type(
        context, ref_type, different_than=different_than
    )
    ref_obj = context.resource_manager.create_and_register(ref_model)
    return ref_obj.meta.location if ref_obj.meta else None


def generate_random_value(
    context: "CheckContext",
    path: Path[Any],
    mutability: list[Mutability] | None = None,
    required: list[Required] | None = None,
) -> Any:
    """Generate a random value for the given path."""
    binding = path.resolve()

    if mutability is not None and (
        binding is None or binding.get_annotation(Mutability) not in mutability
    ):
        return None

    if required is not None and (
        binding is None or binding.get_annotation(Required) not in required
    ):
        return None

    # A path naming a bare extension URN designates a model rather than an
    # attribute, so nothing resolves and the model it names answers for it.
    field_type = binding.target_type if binding else None
    model = binding.target_model if binding else path.model
    field_name = binding.target_field_name if binding else None

    is_email = str(path).endswith("emails.value") or (
        field_name == "value" and model and "email" in model.__name__.lower()
    )
    is_phone = str(path).endswith("phoneNumbers.value") or (
        field_name == "value" and model and "phone" in model.__name__.lower()
    )

    value: Any

    if example_value := get_random_example_value(context, path):
        value = example_value

    # RFC7643 §4.1.2 provides the following indications, however
    # there is no way to guess the existence of such requirements
    # just by looking at the object schema.
    #     The value SHOULD be specified according to [RFC5321].
    elif is_email:
        value = f"{context.random_uuid()}@{context.random_uuid()}.com"

    # RFC7643 §4.1.2 provides the following indications, however
    # there is no way to guess the existence of such requirements
    # just by looking at the object schema.
    #     The value SHOULD be specified
    #     according to the format defined in [RFC3966], e.g.,
    #     'tel:+1-201-555-0123'.
    elif is_phone:  # pragma: no cover
        value = "".join(str(context.random.choice(range(10))) for _ in range(10))

    elif field_type is int:
        value = context.random.randint(0, 2**31 - 1)

    elif field_type is bool:
        value = context.random.choice([True, False])

    elif _references_resources(field_type):
        value = _create_referenced_resource(context, field_type, different_than=model)

    elif isclass(field_type) and issubclass(field_type, Reference):
        value = f"https://{context.random_uuid()}.test"

    elif isclass(field_type) and issubclass(field_type, Enum):
        value = context.random.choice(list(field_type))

    elif isclass(field_type) and issubclass(field_type, ComplexAttribute):
        value = fill_with_random_values(
            context, field_type(), mutability=mutability, required=required
        )

    elif field_type is None and isclass(model) and issubclass(model, Extension):
        value = fill_with_random_values(
            context, model(), mutability=mutability, required=required
        )

    elif field_type is bytes:
        value = base64.b64encode(context.random_uuid().bytes).decode("ascii")

    else:
        value = str(context.random_uuid())

    if binding and binding.target_is_multivalued:
        value = [value]

    return value


def fill_with_random_values(
    context: "CheckContext",
    obj: ModelT,
    paths: list[Path[Any]] | None = None,
    mutability: list[Mutability] | None = None,
    required: list[Required] | None = None,
) -> ModelT:
    """Fill an object with random values generated according the attribute types.

    :param context: The check context containing the SCIM client and configuration
    :param obj: The object to fill with random values
    :param paths: Optional list of Paths to fill
    :param mutability: Optional list of mutability constraints to filter fields
    :param required: Optional list of required constraints to filter fields
    :returns: The filled object
    """
    mutability = mutability or [
        Mutability.read_write,
        Mutability.write_only,
        Mutability.immutable,
    ]
    if paths is None:
        paths = list(
            parametrize(Path, type(obj)).iter_paths(
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

    fix_primary_attributes(context, obj)
    fix_reference_values(context, obj)

    return obj


def fix_reference_values(context: "CheckContext", obj: BaseModel) -> None:
    """Recursively fix ref/value/type consistency on an object and its children.

    Walks the object tree. For any object with a ``ref`` attribute, ``value``
    is set to the last segment of the ``ref`` URL, and ``type`` is set to the
    resource type of the referenced resource when it is one of the ``type`` examples.
    """
    _fix_ref_value(context, obj)
    for field_name in type(obj).model_fields:
        child = getattr(obj, field_name, None)
        if child is None:
            continue

        if isinstance(child, list):
            for item in child:
                _fix_ref_value(context, item)
                if isinstance(item, BaseModel):
                    fix_reference_values(context, item)
        elif isinstance(child, BaseModel):
            _fix_ref_value(context, child)
            fix_reference_values(context, child)


def _fix_ref_value(context: "CheckContext", obj: Any) -> None:
    """Make ``value`` and ``type`` match the resource that ``ref`` points to.

    When ``value`` is set without ``ref``, and ``ref`` can point to a resource,
    such a resource is created first, so ``value`` points to a real resource.
    """
    if getattr(obj, "value", None) and hasattr(obj, "ref") and not obj.ref:
        binding = parametrize(Path, type(obj))("ref").resolve()
        ref_type = binding.target_type if binding else None
        if _references_resources(ref_type):
            obj.ref = _create_referenced_resource(
                context, ref_type, different_than=type(obj)
            )

    ref = getattr(obj, "ref", None)
    if not ref:
        return

    if hasattr(obj, "value"):
        obj.value = ref.rsplit("/", 1)[-1]

    type_field = type(obj).model_fields.get("type")
    if type_field is None or not type_field.examples:
        return

    resource_type = _referenced_resource_type(context, ref)
    if resource_type in type_field.examples:
        obj.type = resource_type


def _referenced_resource_type(context: "CheckContext", ref: str) -> str | None:
    """Return the resource type of the created resource located at ``ref``."""
    for resource in context.resource_manager.resources:
        if resource.meta and resource.meta.location == ref:
            return resource.meta.resource_type
    return None


def fix_primary_attributes(context: "CheckContext", obj: BaseModel) -> None:
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

        primary_index = context.random.randint(0, len(attr_value) - 1)
        for i, item in enumerate(attr_value):
            item.primary = i == primary_index
