from enum import Enum
from unittest.mock import Mock

from pydantic import Field
from scim2_models import ComplexAttribute
from scim2_models import Reference
from scim2_models import Resource

from scim2_tester.filling import fill_with_random_values
from scim2_tester.utils import CheckConfig
from scim2_tester.utils import should_test_patch


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


def test_should_test_patch_when_supported():
    """Test should_test_patch returns True when patch is supported.

    As per RFC7644 §4, ServiceProviderConfig indicates server capabilities.
    """
    mock_client = Mock()
    mock_patch_config = Mock()
    mock_patch_config.supported = True
    mock_spc = Mock()
    mock_spc.patch = mock_patch_config
    mock_client.service_provider_config = mock_spc

    conf = CheckConfig(client=mock_client)

    assert should_test_patch(conf) is True


def test_should_test_patch_when_not_supported():
    """Test should_test_patch returns False when patch is not supported.

    RFC7644 §4 allows servers to indicate PATCH is not supported via patch.supported=false.
    """
    mock_client = Mock()
    mock_patch_config = Mock()
    mock_patch_config.supported = False
    mock_spc = Mock()
    mock_spc.patch = mock_patch_config
    mock_client.service_provider_config = mock_spc

    conf = CheckConfig(client=mock_client)

    assert should_test_patch(conf) is False


def test_should_test_patch_when_no_config():
    """Test should_test_patch returns False when no ServiceProviderConfig."""
    mock_client = Mock()
    mock_client.service_provider_config = None

    conf = CheckConfig(client=mock_client)

    assert should_test_patch(conf) is False


def test_should_test_patch_when_no_patch_config():
    """Test should_test_patch returns False when patch config is None."""
    mock_client = Mock()
    mock_spc = Mock()
    mock_spc.patch = None
    mock_client.service_provider_config = mock_spc

    conf = CheckConfig(client=mock_client)

    assert should_test_patch(conf) is False
