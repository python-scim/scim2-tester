import sys
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from scim2_client import SCIMClientError
from scim2_models import User

from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckContext
from scim2_tester.utils import CheckResult
from scim2_tester.utils import ResourceManager
from scim2_tester.utils import SCIMTesterError
from scim2_tester.utils import Status
from scim2_tester.utils import _matches_hierarchical_tags
from scim2_tester.utils import checker
from scim2_tester.utils import get_registered_tags


def test_checker_decorator_with_tags():
    """Validates checker decorator properly assigns tags to functions."""

    @checker("tag1", "tag2")
    def check_function(context: CheckContext) -> list[CheckResult]:
        """Test check function."""
        return [CheckResult(status=Status.SUCCESS, reason="Success")]

    # Verify function has tags attribute
    assert hasattr(check_function, "tags")
    assert check_function.tags == {"tag1", "tag2"}

    conf = CheckConfig(raise_exceptions=False)
    context = CheckContext(client=None, conf=conf)
    result = check_function(context)
    assert result[0].tags == {"tag1", "tag2"}
    assert result[0].title == "check_function"
    assert result[0].description == "Test check function."


def test_checker_decorator_without_tags():
    """Ensures checker decorator works without explicit tags."""

    @checker
    def check_function(context: CheckContext) -> list[CheckResult]:
        """Test check function."""
        return [CheckResult(status=Status.SUCCESS, reason="Success")]

    # Verify function has empty tags
    assert hasattr(check_function, "tags")
    assert check_function.tags == set()

    conf = CheckConfig(raise_exceptions=False)
    context = CheckContext(client=None, conf=conf)
    result = check_function(context)
    assert result[0].tags == set()


def test_checker_decorator_with_list_results():
    """Confirms tags are applied to all results in list returns."""

    @checker("tag1")
    def check_function(context: CheckContext) -> list[CheckResult]:
        """Test check function."""
        return [
            CheckResult(status=Status.SUCCESS, reason="Success 1"),
            CheckResult(status=Status.SUCCESS, reason="Success 2"),
        ]

    conf = CheckConfig(raise_exceptions=False)
    context = CheckContext(client=None, conf=conf)
    results = check_function(context)

    # All results should have tags
    assert all(r.tags == {"tag1"} for r in results)
    assert all(r.title == "check_function" for r in results)
    assert all(r.description == "Test check function." for r in results)


def test_check_result_raises_exception_when_configured():
    """Test that checker decorator raises exception when configured."""
    """Test that checker decorator raises exception when configured."""

    @checker("test")
    def failing_check(context):
        # Simulate an exception that would create an ERROR result
        raise Exception("Test error")

    conf = CheckConfig(raise_exceptions=True)
    context = CheckContext(client=None, conf=conf)

    with pytest.raises(Exception) as exc_info:
        failing_check(context)

    assert str(exc_info.value) == "Test error"


def test_check_result_no_exception_when_not_configured():
    """Test that checker decorator doesn't raise exception when not configured."""
    """Test that checker decorator doesn't raise exception when not configured."""
    from scim2_tester.utils import checker

    @checker("test")
    def failing_check(context):
        # Simulate an exception that would create an ERROR result
        raise Exception("Test error")

    conf = CheckConfig(raise_exceptions=False)
    context = CheckContext(client=None, conf=conf)

    result = failing_check(context)
    assert result[0].status == Status.ERROR
    assert "Test error" in result[0].reason


def test_check_result_no_exception_on_success():
    """Test that successful checks don't raise exception even when configured."""
    """Test that successful checks don't raise exception even when configured."""
    from scim2_tester.utils import checker

    @checker("test")
    def successful_check(context):
        return [CheckResult(status=Status.SUCCESS, reason="Success")]

    conf = CheckConfig(raise_exceptions=True)
    context = CheckContext(client=None, conf=conf)

    result = successful_check(context)
    assert result[0].status == Status.SUCCESS
    assert result[0].reason == "Success"


def test_check_result_error_should_raise_when_configured():
    """Test that CheckResult with ERROR status should raise exception when configured."""
    """Test that CheckResult with ERROR status should raise exception when configured."""
    from scim2_tester.utils import checker

    @checker("test")
    def error_check(context):
        # Function returns an error result instead of raising exception
        return [CheckResult(status=Status.ERROR, reason="Check failed")]

    conf = CheckConfig(raise_exceptions=True)
    context = CheckContext(client=None, conf=conf)

    # This should now raise an exception
    with pytest.raises(SCIMTesterError) as exc_info:
        error_check(context)

    assert str(exc_info.value) == "Check failed"


def test_check_result_list_error_should_raise_when_configured():
    """Test that list of CheckResult with ERROR status should raise exception when configured."""
    """Test that list of CheckResult with ERROR status should raise exception when configured."""
    from scim2_tester.utils import checker

    @checker("test")
    def error_check_list(context):
        # Function returns a list with one error result
        return [
            CheckResult(status=Status.SUCCESS, reason="Success"),
            CheckResult(status=Status.ERROR, reason="List check failed"),
        ]

    conf = CheckConfig(raise_exceptions=True)
    context = CheckContext(client=None, conf=conf)

    with pytest.raises(SCIMTesterError):
        error_check_list(context)


def test_check_result_multiple_errors_should_raise_exception_group():
    """Test that multiple CheckResult with ERROR status should raise ExceptionGroup when configured."""
    """Test that multiple CheckResult with ERROR status should raise ExceptionGroup when configured."""
    from scim2_tester.utils import checker

    # Import ExceptionGroup for compatibility
    if sys.version_info >= (3, 11):
        from builtins import ExceptionGroup
    else:  # pragma: no cover
        from exceptiongroup import ExceptionGroup

    @checker("test")
    def multiple_error_check(context):
        # Function returns a list with multiple error results
        return [
            CheckResult(status=Status.ERROR, reason="First check failed"),
            CheckResult(status=Status.SUCCESS, reason="Success"),
            CheckResult(status=Status.ERROR, reason="Second check failed"),
        ]

    conf = CheckConfig(raise_exceptions=True)
    context = CheckContext(client=None, conf=conf)

    # This should raise an ExceptionGroup for multiple errors
    with pytest.raises(ExceptionGroup) as exc_info:
        multiple_error_check(context)

    # Verify the ExceptionGroup contains the expected errors
    assert "Multiple check failures" in str(exc_info.value)
    assert len(exc_info.value.exceptions) == 2
    assert all(isinstance(e, SCIMTesterError) for e in exc_info.value.exceptions)
    assert str(exc_info.value.exceptions[0]) == "First check failed"
    assert str(exc_info.value.exceptions[1]) == "Second check failed"


def test_exception_group_usage_example():
    """Demonstrate how to handle ExceptionGroup in practice."""
    """Demonstrate how to handle ExceptionGroup in practice."""
    from scim2_tester.utils import checker

    # Import ExceptionGroup for compatibility
    if sys.version_info >= (3, 11):
        from builtins import ExceptionGroup
    else:  # pragma: no cover
        from exceptiongroup import ExceptionGroup

    @checker("integration-test")
    def complex_check(context):
        # Simulate a complex check that validates multiple things
        return [
            CheckResult(status=Status.SUCCESS, reason="Schema validation passed"),
            CheckResult(status=Status.ERROR, reason="Authentication failed"),
            CheckResult(status=Status.SUCCESS, reason="Rate limiting works"),
            CheckResult(status=Status.ERROR, reason="Invalid response format"),
            CheckResult(status=Status.ERROR, reason="Missing required headers"),
        ]

    conf = CheckConfig(raise_exceptions=True)
    context = CheckContext(client=None, conf=conf)

    # Verify we can catch and handle multiple errors at once
    with pytest.raises(ExceptionGroup) as exc_info:
        complex_check(context)

    # Verify structure
    exception_group = exc_info.value
    assert "Multiple check failures" in str(exception_group)
    assert len(exception_group.exceptions) == 3  # Three errors

    error_messages = [str(e) for e in exception_group.exceptions]
    expected_messages = [
        "Authentication failed",
        "Invalid response format",
        "Missing required headers",
    ]
    assert error_messages == expected_messages


def test_hierarchical_tag_matching():
    """Test hierarchical tag matching in decorator."""
    """Test hierarchical tag matching in decorator."""
    from scim2_tester.utils import checker

    @checker("crud:read")
    def test_func(context):
        from scim2_tester.utils import CheckResult
        from scim2_tester.utils import Status

        return [CheckResult(status=Status.SUCCESS)]

    conf_include = CheckConfig(include_tags={"crud"})
    context_include = CheckContext(client=None, conf=conf_include)
    result = test_func(context_include)  # Call with decorator signature
    assert result[0].status.name == "SUCCESS"

    conf_exclude = CheckConfig(exclude_tags={"crud"})
    context_exclude = CheckContext(client=None, conf=conf_exclude)
    result = test_func(context_exclude)  # Call with decorator signature
    assert result[0].status.name == "SKIPPED"


def test_get_registered_tags():
    """Test get_registered_tags function returns a copy of registered tags."""

    @checker("test_tag1", "test_tag2")
    def dummy_check(context):
        pass

    tags = get_registered_tags()
    assert isinstance(tags, set)
    assert "test_tag1" in tags
    assert "test_tag2" in tags


def test_hierarchical_tag_exact_match():
    """Test exact tag matching without hierarchy."""
    func_tags = {"crud:read", "schemas"}
    filter_tags = {"crud:read"}

    assert _matches_hierarchical_tags(func_tags, filter_tags) is True


def test_hierarchical_tag_no_match():
    """Test when tags don't match."""
    func_tags = {"crud:read", "schemas"}
    filter_tags = {"auth", "other"}

    assert _matches_hierarchical_tags(func_tags, filter_tags) is False


def test_scim_client_error_handling():
    """Test SCIMClientError handling in checker decorator."""

    @checker("test")
    def scim_error_check(context):
        raise SCIMClientError("SCIM error", source={"detail": "test data"})

    conf = CheckConfig(raise_exceptions=False)
    context = CheckContext(client=None, conf=conf)

    result = scim_error_check(context)
    assert result[0].status == Status.ERROR
    assert "SCIM error" in result[0].reason
    assert result[0].data == {"detail": "test data"}


def test_resource_manager_create_and_cleanup():
    """Test ResourceManager create_and_register and cleanup."""
    mock_client = Mock()
    mock_created_user = User(id="123", user_name="test_user")
    mock_client.create.return_value = mock_created_user
    mock_client.delete.return_value = None

    conf = CheckConfig()
    context = CheckContext(client=mock_client, conf=conf)
    resource_manager = ResourceManager(context)

    with patch("scim2_tester.filling.fill_with_random_values") as mock_fill:
        mock_fill.return_value = User(user_name="test_user")
        created = resource_manager.create_and_register(User)

    assert created == mock_created_user
    assert len(resource_manager.resources) == 1
    assert resource_manager.resources[0] == mock_created_user

    # Test cleanup
    resource_manager.cleanup()
    mock_client.delete.assert_called_once_with(User, "123")


def test_resource_manager_cleanup_with_errors():
    """Test ResourceManager cleanup ignores errors."""
    mock_client = Mock()
    mock_created_user = User(id="123", user_name="test_user")
    mock_client.delete.side_effect = Exception("Delete failed")

    conf = CheckConfig()
    context = CheckContext(client=mock_client, conf=conf)
    resource_manager = ResourceManager(context)

    resource_manager.resources.append(mock_created_user)

    resource_manager.cleanup()
    mock_client.delete.assert_called_once_with(User, "123")


def test_resource_manager_cleanup_no_id():
    """Test ResourceManager cleanup skips resources without ID."""
    mock_client = Mock()

    conf = CheckConfig()
    context = CheckContext(client=mock_client, conf=conf)
    resource_manager = ResourceManager(context)

    resource_no_id = User(user_name="test_user")
    resource_manager.resources.append(resource_no_id)

    resource_manager.cleanup()
    mock_client.delete.assert_not_called()


def test_resource_manager_create_failure():
    """Test ResourceManager create_and_register handles non-Resource response."""
    mock_client = Mock()
    mock_client.create.return_value = {"error": "Creation failed"}

    conf = CheckConfig()
    context = CheckContext(client=mock_client, conf=conf)
    resource_manager = ResourceManager(context)

    with patch("scim2_tester.filling.fill_with_random_values") as mock_fill:
        mock_fill.return_value = User(user_name="test_user")
        with pytest.raises(ValueError) as exc_info:
            resource_manager.create_and_register(User)

    assert "Failed to create resource" in str(exc_info.value)


def test_checker_skip_with_include_tags():
    """Test checker skips execution when include_tags don't match."""

    @checker("crud:write")
    def write_check(context):
        return [CheckResult(status=Status.SUCCESS)]

    conf = CheckConfig(include_tags={"crud:read", "schemas"})
    context = CheckContext(client=None, conf=conf)

    result = write_check(context)
    assert len(result) == 1
    assert result[0].status == Status.SKIPPED
    assert result[0].reason == "Skipped due to tag filtering"
    assert result[0].title == "write_check"
