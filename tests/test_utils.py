import pytest

from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckResult
from scim2_tester.utils import SCIMTesterError
from scim2_tester.utils import Status
from scim2_tester.utils import checker


def test_checker_decorator_with_tags():
    """Test the checker decorator with tags."""

    @checker("tag1", "tag2")
    def check_function(conf: CheckConfig) -> CheckResult:
        """Test check function."""
        return CheckResult(conf, status=Status.SUCCESS, reason="Success")

    # Verify function has tags attribute
    assert hasattr(check_function, "tags")
    assert check_function.tags == {"tag1", "tag2"}

    # Test that result gets tags
    conf = CheckConfig(client=None, raise_exceptions=False)
    result = check_function(conf)
    assert result.tags == {"tag1", "tag2"}
    assert result.title == "check_function"
    assert result.description == "Test check function."


def test_checker_decorator_without_tags():
    """Test the checker decorator without tags."""

    @checker
    def check_function(conf: CheckConfig) -> CheckResult:
        """Test check function."""
        return CheckResult(conf, status=Status.SUCCESS, reason="Success")

    # Verify function has empty tags
    assert hasattr(check_function, "tags")
    assert check_function.tags == set()

    # Test that result gets empty tags
    conf = CheckConfig(client=None, raise_exceptions=False)
    result = check_function(conf)
    assert result.tags == set()


def test_checker_decorator_with_list_results():
    """Test the checker decorator with list of results."""

    @checker("tag1")
    def check_function(conf: CheckConfig) -> list[CheckResult]:
        """Test check function."""
        return [
            CheckResult(conf, status=Status.SUCCESS, reason="Success 1"),
            CheckResult(conf, status=Status.SUCCESS, reason="Success 2"),
        ]

    conf = CheckConfig(client=None, raise_exceptions=False)
    results = check_function(conf)

    # All results should have tags
    assert all(r.tags == {"tag1"} for r in results)
    assert all(r.title == "check_function" for r in results)
    assert all(r.description == "Test check function." for r in results)


def test_scim_tester_error():
    """Test SCIMTesterError exception."""
    conf = CheckConfig(client=None, raise_exceptions=False)
    error = SCIMTesterError("Test error", conf)
    assert str(error) == "Test error"
    assert error.conf == conf


def test_check_result_raises_exception_when_configured():
    """Test that CheckResult raises exception when configured."""
    conf = CheckConfig(client=None, raise_exceptions=True)

    with pytest.raises(SCIMTesterError) as exc_info:
        CheckResult(conf, status=Status.ERROR, reason="Test error")

    assert str(exc_info.value) == "Test error"


def test_check_result_no_exception_when_not_configured():
    """Test that CheckResult doesn't raise exception when not configured."""
    conf = CheckConfig(client=None, raise_exceptions=False)
    result = CheckResult(conf, status=Status.ERROR, reason="Test error")
    assert result.status == Status.ERROR
    assert result.reason == "Test error"


def test_check_result_no_exception_on_success():
    """Test that CheckResult doesn't raise exception on success."""
    conf = CheckConfig(client=None, raise_exceptions=True)
    result = CheckResult(conf, status=Status.SUCCESS, reason="Success")
    assert result.status == Status.SUCCESS
    assert result.reason == "Success"


def test_check_result_default_values():
    """Test CheckResult default values."""
    conf = CheckConfig(client=None, raise_exceptions=False)
    result = CheckResult(conf, status=Status.SUCCESS)

    assert result.conf == conf
    assert result.status == Status.SUCCESS
    assert result.title is None
    assert result.description is None
    assert result.reason is None
    assert result.data is None
    assert result.tags == set()
    assert result.resource_type is None
