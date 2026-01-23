"""Test automatic field filling functionality."""

from typing import Annotated
from typing import Union
from unittest.mock import patch

from scim2_models import Email
from scim2_models import EnterpriseUser
from scim2_models import Group
from scim2_models import Mutability
from scim2_models import PhoneNumber
from scim2_models import Reference
from scim2_models import Required
from scim2_models import User
from scim2_models.attributes import ComplexAttribute
from scim2_models.path import Path
from scim2_models.resources.resource import Resource
from scim2_models.resources.user import X509Certificate

from scim2_tester.filling import fill_with_random_values
from scim2_tester.filling import fix_primary_attributes
from scim2_tester.filling import generate_random_value
from scim2_tester.filling import get_model_from_ref_type
from scim2_tester.filling import get_random_example_value


def test_generate_random_value_bytes_field(testing_context):
    """Validates random value generation for bytes fields."""
    value = generate_random_value(testing_context, Path[X509Certificate]("value"))

    assert isinstance(value, str)


def test_model_resolution_from_reference_type(testing_context):
    """Ensures model resolution from reference type excludes specified models."""
    ref_type = Reference[Union["User", "Group"]]
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
        result = fill_with_random_values(
            testing_context, user, [Path[User]("nonexistent_urn")]
        )
        mock_generate.assert_called_once()

    assert result is user


def test_get_random_example_value():
    """Validates random value selection from pydantic field examples."""
    value = get_random_example_value(Path[Email]("type"))

    assert value in ["work", "home", "other"]


def test_get_random_example_value_no_examples():
    """Returns None when field has no examples."""
    value = get_random_example_value(Path[Email]("value"))

    assert value is None


def test_get_random_example_value_invalid_urn():
    """Returns None when URN is invalid."""
    value = get_random_example_value(Path[Email]("nonexistent"))

    assert value is None


def test_generate_random_value_with_examples(testing_context):
    """Uses examples when available."""
    value = generate_random_value(testing_context, Path[Email]("type"))

    assert value in ["work", "home", "other"]


def test_generate_random_value_phone_number(testing_context):
    """Generates phone numbers correctly."""
    value = generate_random_value(testing_context, Path[PhoneNumber]("value"))

    assert isinstance(value, str)
    assert len(value) == 10
    assert value.isdigit()


def test_generate_random_value_email(testing_context):
    """Generates emails correctly."""
    value = generate_random_value(testing_context, Path[Email]("value"))

    assert isinstance(value, str)
    assert "@" in value
    assert value.endswith(".com")


def test_generate_random_value_bool(testing_context):
    """Generates boolean values."""
    value = generate_random_value(testing_context, Path[User]("active"))

    assert isinstance(value, bool)


def test_generate_random_value_int(testing_context):
    """Generates integer values."""
    value = generate_random_value(testing_context, Path[X509Certificate]("value"))

    assert isinstance(value, str)


def test_generate_random_value_complex_attribute(testing_context):
    """Generates complex attribute values."""
    value = generate_random_value(testing_context, Path[User]("name"))

    assert value is not None


def test_generate_random_value_multiple_field(testing_context):
    """Generates list values for multiple fields."""
    value = generate_random_value(testing_context, Path[User]("emails"))

    assert isinstance(value, list)
    assert len(value)


def test_generate_random_value_reference_external(testing_context):
    """Generates external reference values."""
    value = generate_random_value(testing_context, Path[User]("profileUrl"))

    assert isinstance(value, str)
    assert value.startswith("https://")


def test_generate_random_value_default_string(testing_context):
    """Generates default string values."""
    value = generate_random_value(testing_context, Path[User]("title"))

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


def test_fill_with_random_values_emails_primary_constraint(testing_context):
    """Ensures fill_with_random_values maintains primary=True constraint for emails."""
    user = User(user_name="test")
    filled_user = fill_with_random_values(testing_context, user, [Path[User]("emails")])

    primary_count = sum(1 for email in filled_user.emails if email.primary)
    assert primary_count == 1


def test_fill_with_random_values_phone_numbers_primary_constraint(testing_context):
    """Ensures fill_with_random_values maintains primary=True constraint for phone numbers."""
    user = User(user_name="test")
    filled_user = fill_with_random_values(
        testing_context, user, [Path[User]("phoneNumbers")]
    )

    primary_count = sum(1 for phone in filled_user.phone_numbers if phone.primary)
    assert primary_count == 1


def test_sub_attributes_mutability_filter(testing_context):
    class TestComplexAttr(ComplexAttribute):
        writable_field: str | None = None
        readonly_field: Annotated[str | None, Mutability.read_only] = None
        immutable_field: Annotated[str | None, Mutability.immutable] = None

    class TestResource(Resource):
        __schema__: str = "urn:test:TestResource"
        test_attr: TestComplexAttr | None = None

    filled = fill_with_random_values(testing_context, TestResource())

    assert filled.test_attr is not None
    assert filled.test_attr.writable_field is not None
    assert filled.test_attr.readonly_field is None
    assert filled.test_attr.immutable_field is not None

    filled = fill_with_random_values(
        testing_context, TestResource(), mutability=[Mutability.read_write]
    )

    assert filled.test_attr is not None
    assert filled.test_attr.writable_field is not None
    assert filled.test_attr.readonly_field is None
    assert filled.test_attr.immutable_field is None


def test_get_model_from_ref_type_fallback_when_no_acceptable_models(testing_context):
    """Ensures fallback to first model when all models are excluded by different_than."""
    ref_type = Reference["User"]
    result = get_model_from_ref_type(
        testing_context, ref_type, different_than=User[EnterpriseUser]
    )

    assert result == User[EnterpriseUser]


def test_generate_random_value_required_filter(testing_context):
    """Tests required filter returns None when field is not in required list."""
    result = generate_random_value(
        testing_context, Path[User]("displayName"), required=[Required.true]
    )

    assert result is None

    result = generate_random_value(
        testing_context, Path[User]("userName"), required=[Required.true]
    )
    assert result
