from enum import Enum

from pydantic import Field
from scim2_models import ComplexAttribute
from scim2_models import Reference
from scim2_models import Resource

from scim2_tester.resource import fill_with_random_values


class Complex(ComplexAttribute):
    str_unique: str | None = None
    str_multiple: list[str] | None = None


class CustomModel(Resource):
    schemas: list[str] = ["org:test:CustomModel"]

    class Type(str, Enum):
        foo = "foo"
        bar = "bar"

    str_unique: str | None = None
    str_multiple: list[str] | None = None

    int_unique: int | None = None
    int_multiple: list[int] | None = None

    bool_unique: bool | None = None
    bool_multiple: list[bool] | None = None

    reference_unique: Reference | None = None
    reference_multiple: list[Reference] | None = None

    email_unique: Reference | None = None
    email_multiple: list[Reference] | None = None

    enum_unique: Type | None = None
    enum_multiple: list[Type] | None = None

    complex_unique: Complex | None = None
    complex_multiple: list[Complex] | None = None

    example_unique: str | None = Field(None, examples=["foo", "bar"])
    example_multiple: list[str] | None = Field(None, examples=["foo", "bar"])


def test_random_values():
    """Check that 'fill_with_random_values' produce valid objects."""
    obj = CustomModel()
    fill_with_random_values(None, obj)
    for field_name in obj.__class__.model_fields:
        if field_name == "meta":
            continue

        assert getattr(obj, field_name) is not None

    assert obj.example_unique in ["foo", "bar"]
    assert all(val in ["foo", "bar"] for val in obj.example_multiple)
