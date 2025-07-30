"""Test automatic field filling functionality."""

import base64
from typing import Literal
from unittest.mock import patch

from scim2_models import Group
from scim2_models import User
from scim2_models.resources.user import X509Certificate

from scim2_tester.filling import fill_with_random_values
from scim2_tester.filling import generate_random_value
from scim2_tester.filling import model_from_ref_type
from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckContext


class MockClient:
    def __init__(self):
        self.resource_models = [User, Group]

    def get_resource_model(self, model_name):
        model_map = {"User": User, "Group": Group}
        return model_map.get(model_name)


def test_generate_random_value_bytes_field():
    """Validates random value generation for bytes fields."""
    config = CheckConfig()
    context = CheckContext(MockClient(), config)

    cert = X509Certificate(value=base64.b64encode(b"placeholder"))

    value = generate_random_value(context, cert, context.resource_manager, "value")

    assert isinstance(value, str)
    assert len(value) == 36  # UUID string length


def test_model_resolution_from_reference_type():
    """Ensures model resolution from reference type excludes specified models."""
    conf = CheckConfig()
    context = CheckContext(MockClient(), conf)

    ref_type = Literal["User"] | Literal["Group"]
    different_than = Group

    result = model_from_ref_type(context, ref_type, different_than)

    assert result == User


def test_fill_with_empty_field_list():
    """Confirms no fields are modified when empty field list provided."""
    conf = CheckConfig()
    context = CheckContext(MockClient(), conf)

    user = User(user_name="test")
    original_user_name = user.user_name

    with patch(
        "scim2_tester.filling.generate_random_value", return_value="mock_value"
    ) as mock_generate:
        result = fill_with_random_values(context, user, context.resource_manager, [])
        mock_generate.assert_not_called()

    assert result is user
    assert result.user_name == original_user_name


def test_fill_with_nonexistent_field():
    """Verifies nonexistent fields are ignored during filling process."""
    conf = CheckConfig()
    context = CheckContext(MockClient(), conf)

    user = User(user_name="test")

    with patch(
        "scim2_tester.filling.generate_random_value", return_value="mock_value"
    ) as mock_generate:
        result = fill_with_random_values(
            context, user, context.resource_manager, ["nonexistent_field"]
        )
        mock_generate.assert_not_called()

    assert result is user
