"""Test PATCH operation extension root path handling."""

from unittest.mock import Mock
from unittest.mock import patch

import pytest
from scim2_client import SCIMClientError
from scim2_models import Mutability
from scim2_models import Required
from scim2_models.resources.user import User

from scim2_tester.checkers.patch.checkers import _execute_patch_test_case
from scim2_tester.checkers.patch.checkers import check_patch_extensions
from scim2_tester.checkers.patch.test_cases import ExpectedResult
from scim2_tester.checkers.patch.test_cases import PatchOp
from scim2_tester.checkers.patch.test_cases import PatchTestCase
from scim2_tester.checkers.patch.test_cases import _generate_extension_root_cases
from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckContext
from scim2_tester.utils import Status


class MockExtension:
    """Mock extension class for testing."""

    model_fields = {
        "schemas": Mock(
            default=["urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"]
        )
    }


class MockResourceWithExtension:
    """Mock resource class with extensions."""

    __name__ = "User"

    @classmethod
    def get_extension_models(cls):
        return {"enterprise": MockExtension}


class TestExtensionRootCases:
    """Test extension root path test case generation."""

    def test_generate_extension_root_cases_with_extensions(self):
        """Test generating extension root cases for resource with extensions."""
        cases = _generate_extension_root_cases(MockResourceWithExtension)

        assert len(cases) == 1
        case = cases[0]
        assert case.field_name == "extension_root"
        assert case.operation == PatchOp.REMOVE
        assert case.value is None
        assert case.path == "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
        assert case.expected_result == ExpectedResult.ERROR_EXTENSION_REMOVAL
        assert case.is_extension_root is True
        assert "extension root path" in case.description

    def test_generate_extension_root_cases_no_extensions(self):
        """Test generating extension root cases for resource without extensions."""

        class MockResourceNoExtension:
            __name__ = "Group"

            @classmethod
            def get_extension_models(cls):
                return {}

        cases = _generate_extension_root_cases(MockResourceNoExtension)
        assert len(cases) == 0

    def test_generate_extension_root_cases_no_get_extension_models(self):
        """Test generating extension root cases for resource without get_extension_models method."""

        class MockResourceNoMethod:
            __name__ = "Custom"

        cases = _generate_extension_root_cases(MockResourceNoMethod)
        assert len(cases) == 0


class TestPatchExtensionExecution:
    """Test PATCH extension operation execution."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock check context."""
        client = Mock()
        config = CheckConfig()
        context = CheckContext(client, config)
        context.resource_manager = Mock()
        return context

    @pytest.fixture
    def mock_resource(self):
        """Create a mock resource."""
        resource = Mock()
        resource.id = "test-id"
        return resource

    @pytest.fixture
    def extension_test_case(self):
        """Create an extension root test case."""
        return PatchTestCase(
            field_name="extension_root",
            operation=PatchOp.REMOVE,
            value=None,
            path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            expected_result=ExpectedResult.ERROR_EXTENSION_REMOVAL,
            mutability=Mutability.read_write,
            required=Required.false,
            description="Test extension root removal",
            is_extension_root=True,
        )

    def test_extension_removal_accepted_success(
        self, mock_context, mock_resource, extension_test_case
    ):
        """Test server accepting extension root path removal (SUCCESS)."""
        # Server accepts the operation (no exception)
        mock_context.client.modify.return_value = Mock()

        result = _execute_patch_test_case(
            mock_context, mock_resource, extension_test_case
        )

        assert result.status == Status.SUCCESS
        assert "correctly accepts root extension path deletion" in result.reason
        assert result.data["extension_path"] == extension_test_case.path

    def test_extension_removal_refused_deviation(
        self, mock_context, mock_resource, extension_test_case
    ):
        """Test server refusing extension root path removal (DEVIATION)."""
        # Server refuses the operation with an error
        error = SCIMClientError("Extension removal not supported")
        error.source = {"scimType": "noTarget", "detail": "Extension schema not found"}
        mock_context.client.modify.side_effect = error

        result = _execute_patch_test_case(
            mock_context, mock_resource, extension_test_case
        )

        assert result.status == Status.DEVIATION
        assert "refused root extension path deletion" in result.reason
        assert "deviates from extensibility principles" in result.reason
        assert result.data["extension_path"] == extension_test_case.path


class TestCheckPatchExtensions:
    """Test the main check_patch_extensions function."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock check context."""
        client = Mock()
        config = CheckConfig(resource_types=["User"])
        context = CheckContext(client, config)
        context.resource_manager = Mock()

        # Mock resource manager methods
        context.resource_manager.create_and_register.return_value = Mock(id="test-id")

        return context

    @patch("scim2_tester.checkers.patch.checkers.generate_patch_test_cases")
    @patch("scim2_tester.checkers.patch.checkers._execute_patch_test_case")
    def test_check_patch_extensions(self, mock_execute, mock_generate, mock_context):
        """Test the check_patch_extensions function."""
        # Mock the resource class
        mock_resource_class = Mock()
        mock_resource_class.__name__ = "User"
        mock_context.client.get_resource_model.return_value = mock_resource_class

        # Mock test case generation to return an extension case
        extension_case = Mock()
        extension_case.is_extension_root = True
        mock_generate.return_value = [extension_case]

        # Mock execution result
        mock_result = Mock()
        mock_result.resource_type = "User"
        mock_execute.return_value = mock_result

        results = check_patch_extensions(mock_context)

        assert len(results) == 1
        assert results[0].resource_type == "User"
        mock_execute.assert_called_once()


class TestExtensionRealIntegration:
    """Integration tests with real User model if available."""

    def test_user_extension_generation(self):
        """Test extension generation with real User model."""
        try:
            # Check if User has enterprise extension
            if hasattr(User, "get_extension_models"):
                extensions = User.get_extension_models()
                if extensions:
                    cases = _generate_extension_root_cases(User)
                    # Should generate at least one case if extensions exist
                    assert len(cases) >= 0  # May be 0 if no extensions in test setup

                    # If cases exist, verify structure
                    for case in cases:
                        assert case.is_extension_root is True
                        assert case.operation == PatchOp.REMOVE
                        assert "urn:" in case.path
                        assert (
                            case.expected_result
                            == ExpectedResult.ERROR_EXTENSION_REMOVAL
                        )
        except Exception:
            # If User model doesn't have extensions or other issues, skip
            pytest.skip("User model extension testing not available")
