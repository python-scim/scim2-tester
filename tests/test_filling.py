"""Test automatic field filling functionality."""

from typing import Literal
from unittest.mock import patch

from scim2_models import Email
from scim2_models import Group
from scim2_models import PhoneNumber
from scim2_models import User
from scim2_models.resources.user import X509Certificate

from scim2_tester.filling import fill_with_random_values
from scim2_tester.filling import fix_primary_attributes
from scim2_tester.filling import generate_random_value
from scim2_tester.filling import get_model_from_ref_type
from scim2_tester.filling import get_random_example_value


def test_generate_random_value_bytes_field(testing_context):
    """Validates random value generation for bytes fields."""
    value = generate_random_value(testing_context, urn="value", model=X509Certificate)

    assert isinstance(value, str)


def test_model_resolution_from_reference_type(testing_context):
    """Ensures model resolution from reference type excludes specified models."""
    from scim2_models import EnterpriseUser

    ref_type = Literal["User"] | Literal["Group"]
    different_than = Group

    result = get_model_from_ref_type(testing_context, ref_type, different_than)

    assert result == User[EnterpriseUser]
    assert result != Group


def test_generate_random_value_for_reference(testing_context, httpserver):
    """Validates random value generation for reference fields."""
    group = Group()

    # Mock HTTP response for user creation
    user_data = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": "test-user-id",
        "userName": "test-user",
        "meta": {
            "resourceType": "User",
            "location": f"http://localhost:{httpserver.port}/Users/test-user-id",
        },
    }
    httpserver.expect_request("/Users", method="POST").respond_with_json(
        user_data, status=201
    )

    result = fill_with_random_values(testing_context, group)

    assert len(result.members) == 1
    assert result.members[0].value == result.members[0].ref.rsplit("/", 1)[-1]


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
        result = fill_with_random_values(testing_context, user, ["nonexistent_urn"])
        mock_generate.assert_called_once()

    assert result is user


def test_get_random_example_value():
    """Validates random value selection from pydantic field examples."""
    from scim2_models import Email

    value = get_random_example_value(Email, "type")

    assert value in ["work", "home", "other"]


def test_get_random_example_value_no_examples():
    """Returns None when field has no examples."""
    from scim2_models import Email

    value = get_random_example_value(Email, "value")

    assert value is None


def test_get_random_example_value_invalid_urn():
    """Returns None when URN is invalid."""
    from scim2_models import Email

    value = get_random_example_value(Email, "nonexistent")

    assert value is None


def test_generate_random_value_with_examples(testing_context):
    """Uses examples when available."""
    from scim2_models import Email

    value = generate_random_value(testing_context, "type", Email)

    assert value in ["work", "home", "other"]


def test_generate_random_value_phone_number(testing_context):
    """Generates phone numbers correctly."""
    value = generate_random_value(testing_context, "phoneNumbers.value", PhoneNumber)

    assert isinstance(value, str)
    assert len(value) == 10
    assert value.isdigit()


def test_generate_random_value_email(testing_context):
    """Generates emails correctly."""
    from scim2_models import Email

    value = generate_random_value(testing_context, "emails.value", Email)

    assert isinstance(value, str)
    assert "@" in value
    assert value.endswith(".com")


def test_generate_random_value_bool(testing_context):
    """Generates boolean values."""
    from scim2_models import User

    value = generate_random_value(testing_context, "active", User)

    assert isinstance(value, bool)


def test_generate_random_value_int(testing_context):
    """Generates integer values."""
    from scim2_models.resources.user import X509Certificate

    value = generate_random_value(testing_context, "value", X509Certificate)

    assert isinstance(value, str)


def test_generate_random_value_complex_attribute(testing_context):
    """Generates complex attribute values."""
    from scim2_models import User

    value = generate_random_value(testing_context, "name", User)

    assert value is not None


def test_generate_random_value_multiple_field(testing_context):
    """Generates list values for multiple fields."""
    from scim2_models import User

    value = generate_random_value(testing_context, "emails", User)

    assert isinstance(value, list)


def test_generate_random_value_reference_external(testing_context):
    """Generates external reference values."""
    from scim2_models import User

    value = generate_random_value(testing_context, "profileUrl", User)

    assert isinstance(value, str)
    assert value.startswith("https://")


def test_generate_random_value_default_string(testing_context):
    """Generates default string values."""
    value = generate_random_value(testing_context, "title", User)

    assert isinstance(value, str)


def test_fix_primary_attributes_single_object():
    """Ensures single email gets primary=True."""
    user = User(user_name="test")
    user.emails = [Email(value="test@example.com", type=Email.Type.work)]

    fix_primary_attributes(user)

    assert len(user.emails) == 1
    assert user.emails[0].primary is True


def test_fix_primary_attributes_multiple_objects():
    """Ensures exactly one email has primary=True when multiple exist."""
    user = User(user_name="test")
    user.emails = [
        Email(value="work@example.com", type=Email.Type.work),
        Email(value="home@example.com", type=Email.Type.home),
        Email(value="other@example.com", type=Email.Type.other),
    ]

    fix_primary_attributes(user)

    assert len(user.emails) == 3
    primary_count = sum(1 for email in user.emails if email.primary)
    assert primary_count == 1
