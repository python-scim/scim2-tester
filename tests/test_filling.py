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


def test_generate_random_value_bytes_field(testing_context):
    """Validates random value generation for bytes fields."""
    cert = X509Certificate(value=base64.b64encode(b"placeholder"))

    value = generate_random_value(testing_context, cert, "value")

    assert isinstance(value, str)
    assert len(value) == 36  # UUID string length


def test_model_resolution_from_reference_type(testing_context):
    """Ensures model resolution from reference type excludes specified models."""
    from scim2_models import EnterpriseUser

    ref_type = Literal["User"] | Literal["Group"]
    different_than = Group

    result = model_from_ref_type(testing_context, ref_type, different_than)

    # The result should be User[EnterpriseUser] from the testing context
    assert result == User[EnterpriseUser]
    assert result != Group


def test_fill_with_empty_field_list(testing_context):
    """Confirms no fields are modified when empty field list provided."""
    user = User(user_name="test")
    original_user_name = user.user_name

    with patch(
        "scim2_tester.filling.generate_random_value", return_value="mock_value"
    ) as mock_generate:
        result = fill_with_random_values(testing_context, user, [])
        mock_generate.assert_not_called()

    assert result is user
    assert result.user_name == original_user_name


def test_fill_with_nonexistent_field(testing_context):
    """Verifies nonexistent fields are ignored during filling process."""
    user = User(user_name="test")

    with patch(
        "scim2_tester.filling.generate_random_value", return_value="mock_value"
    ) as mock_generate:
        result = fill_with_random_values(testing_context, user, ["nonexistent_field"])
        mock_generate.assert_not_called()

    assert result is user
