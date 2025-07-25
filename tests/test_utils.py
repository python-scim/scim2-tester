import pytest

from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckContext
from scim2_tester.utils import CheckResult
from scim2_tester.utils import SCIMTesterError
from scim2_tester.utils import Status
from scim2_tester.utils import checker


def test_checker_decorator_with_tags():
    """Test the checker decorator with tags."""

    @checker("tag1", "tag2")
    def check_function(context: CheckContext) -> CheckResult:
        """Test check function."""
        return CheckResult(status=Status.SUCCESS, reason="Success")

    # Verify function has tags attribute
    assert hasattr(check_function, "tags")
    assert check_function.tags == {"tag1", "tag2"}

    # Test that result gets tags
    conf = CheckConfig(raise_exceptions=False)
    context = CheckContext(client=None, conf=conf)
    result = check_function(context)
    assert result.tags == {"tag1", "tag2"}
    assert result.title == "check_function"
    assert result.description == "Test check function."


def test_checker_decorator_without_tags():
    """Test the checker decorator without tags."""

    @checker
    def check_function(context: CheckContext) -> CheckResult:
        """Test check function."""
        return CheckResult(status=Status.SUCCESS, reason="Success")

    # Verify function has empty tags
    assert hasattr(check_function, "tags")
    assert check_function.tags == set()

    # Test that result gets empty tags
    conf = CheckConfig(raise_exceptions=False)
    context = CheckContext(client=None, conf=conf)
    result = check_function(context)
    assert result.tags == set()


def test_checker_decorator_with_list_results():
    """Test the checker decorator with list of results."""

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


def test_scim_tester_error():
    """Test SCIMTesterError exception."""
    conf = CheckConfig(raise_exceptions=False)
    error = SCIMTesterError("Test error", conf)
    assert str(error) == "Test error"
    assert error.conf == conf


def test_check_result_raises_exception_when_configured():
    """Test that checker decorator raises exception when configured."""
    from scim2_tester.utils import checker

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
    from scim2_tester.utils import checker

    @checker("test")
    def failing_check(context):
        # Simulate an exception that would create an ERROR result
        raise Exception("Test error")

    conf = CheckConfig(raise_exceptions=False)
    context = CheckContext(client=None, conf=conf)

    result = failing_check(context)
    assert result.status == Status.ERROR
    assert "Test error" in result.reason


def test_check_result_no_exception_on_success():
    """Test that successful checks don't raise exception even when configured."""
    from scim2_tester.utils import checker

    @checker("test")
    def successful_check(context):
        return CheckResult(status=Status.SUCCESS, reason="Success")

    conf = CheckConfig(raise_exceptions=True)
    context = CheckContext(client=None, conf=conf)

    result = successful_check(context)
    assert result.status == Status.SUCCESS
    assert result.reason == "Success"


def test_check_result_error_should_raise_when_configured():
    """Test that CheckResult with ERROR status should raise exception when configured."""
    from scim2_tester.utils import SCIMTesterError
    from scim2_tester.utils import checker

    @checker("test")
    def error_check(context):
        # Function returns an error result instead of raising exception
        return CheckResult(status=Status.ERROR, reason="Check failed")

    conf = CheckConfig(raise_exceptions=True)
    context = CheckContext(client=None, conf=conf)

    # This should now raise an exception
    with pytest.raises(SCIMTesterError) as exc_info:
        error_check(context)

    assert str(exc_info.value) == "Check failed"


def test_check_result_list_error_should_raise_when_configured():
    """Test that list of CheckResult with ERROR status should raise exception when configured."""
    from scim2_tester.utils import SCIMTesterError
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

    # This should raise an exception for the first ERROR in the list
    with pytest.raises(SCIMTesterError) as exc_info:
        error_check_list(context)

    assert str(exc_info.value) == "List check failed"


def test_check_result_multiple_errors_should_raise_exception_group():
    """Test that multiple CheckResult with ERROR status should raise ExceptionGroup when configured."""
    import sys

    from scim2_tester.utils import SCIMTesterError
    from scim2_tester.utils import checker

    # Import ExceptionGroup for compatibility
    if sys.version_info >= (3, 11):
        from builtins import ExceptionGroup
    else:
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
    import sys

    from scim2_tester.utils import checker

    # Import ExceptionGroup for compatibility
    if sys.version_info >= (3, 11):
        from builtins import ExceptionGroup
    else:
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

    # Verify each error is a SCIMTesterError with the right message
    error_messages = [str(e) for e in exception_group.exceptions]
    expected_messages = [
        "Authentication failed",
        "Invalid response format",
        "Missing required headers",
    ]
    assert error_messages == expected_messages


def test_check_result_default_values():
    """Test CheckResult default values."""
    result = CheckResult(status=Status.SUCCESS)
    assert result.status == Status.SUCCESS
    assert result.title is None
    assert result.description is None
    assert result.reason is None
    assert result.data is None
    assert result.tags == set()
    assert result.resource_type is None


def test_check_context():
    """Test CheckContext initialization and access."""
    from scim2_tester.utils import CheckContext

    conf = CheckConfig(raise_exceptions=False)
    context = CheckContext(client=None, conf=conf)

    assert context.client is None
    assert context.conf == conf
    assert context.resource_manager is not None
    assert context.resource_manager.context == context


def test_hierarchical_tag_matching():
    """Test hierarchical tag matching in decorator."""
    from scim2_tester.utils import checker

    @checker("crud:read")
    def test_func(context):
        from scim2_tester.utils import CheckResult
        from scim2_tester.utils import Status

        return CheckResult(status=Status.SUCCESS)

    # Test include tags matching
    conf_include = CheckConfig(include_tags={"crud"})
    context_include = CheckContext(client=None, conf=conf_include)
    result = test_func(context_include)  # Call with decorator signature
    assert result.status.name == "SUCCESS"

    # Test exclude tags matching
    conf_exclude = CheckConfig(exclude_tags={"crud"})
    context_exclude = CheckContext(client=None, conf=conf_exclude)
    result = test_func(context_exclude)  # Call with decorator signature
    assert result.status.name == "SKIPPED"
