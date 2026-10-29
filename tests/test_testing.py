"""Tests of the pytest suite checking a SCIM server."""

import pytest

COMPLIANT_SERVER = """
import pytest
from scim2_client.engines.wsgi import WSGISCIMClient

from scim2_tester.testing import ScimServerContract


class TestServer(ScimServerContract):
    @pytest.fixture
    def scim_client(self, scim2_server_app):
        return WSGISCIMClient(scim2_server_app)
"""

FAKE_SERVER = """
import pytest

import scim2_tester.testing
from scim2_tester import CheckResult
from scim2_tester import Status
from scim2_tester.testing import ScimServerContract

CALLS = []
RESULTS = [{results}]


def fake_iter_check_server(client, **kwargs):
    CALLS.append(kwargs)
    return iter(RESULTS)


@pytest.fixture(autouse=True)
def fake(monkeypatch):
    monkeypatch.setattr(scim2_tester.testing, "iter_check_server", fake_iter_check_server)


class TestServer(ScimServerContract):
    expected_results = {expected}

    @pytest.fixture
    def scim_client(self):
        return None
"""


def fake_server(*statuses, expected="{}"):
    """Return a test module whose server returns a result per status."""
    results = ", ".join(
        f'CheckResult(status=Status.{status}, title="a_check", reason="the reason")'
        for status in statuses
    )
    return FAKE_SERVER.format(results=results, expected=expected)


def test_a_compliant_server_passes(pytester):
    """A server following the RFCs passes the suite."""
    pytester.makepyfile(COMPLIANT_SERVER)

    result = pytester.runpytest("-v")

    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(["*= 1 passed, * subtests passed in *"])
    result.stdout.no_fnmatch_line("*SUBFAILED*")


@pytest.mark.parametrize("status", ["SUCCESS", "COMPLIANT", "ACCEPTABLE"])
def test_successful_results_pass(pytester, status):
    """The successful, compliant and acceptable results pass."""
    pytester.makepyfile(fake_server(status))

    result = pytester.runpytest("-v")

    result.stdout.fnmatch_lines(["*= 1 passed, 1 subtests passed in *"])


def test_skipped_results_are_skipped(pytester):
    """The skipped results are reported as skipped subtests, with their reason."""
    pytester.makepyfile(fake_server("SKIPPED"))

    result = pytester.runpytest("-v", "-rs")

    result.stdout.fnmatch_lines(
        [
            "SUBSKIPPED[[]a_check[]] *: (None, 'a_check', None) the reason",
            "*= 1 passed, 1 skipped in *",
        ]
    )


@pytest.mark.parametrize("status", ["ERROR", "CRITICAL"])
def test_failing_results_fail(pytester, status):
    """The errors and critical results fail, with their status and reason."""
    pytester.makepyfile(fake_server(status))

    result = pytester.runpytest("-v")

    result.assert_outcomes(failed=2)
    result.stdout.fnmatch_lines(
        [
            "_* TestServer.test_check_server [[]a_check[]] _*",
            f"(None, 'a_check', None) {status}: the reason",
        ]
    )


SERVER_RAISING = """
import pytest

import scim2_tester.testing
from scim2_tester import CheckResult
from scim2_tester import Status
from scim2_tester.testing import ScimServerContract


def delete_resource():
    raise RuntimeError("the storage is down")


def fake_iter_check_server(client, **kwargs):
    try:
        delete_resource()
    except RuntimeError as exc:
        yield CheckResult(status=Status.ERROR, title="a_check", reason=str(exc), data=exc)


@pytest.fixture(autouse=True)
def fake(monkeypatch):
    monkeypatch.setattr(scim2_tester.testing, "iter_check_server", fake_iter_check_server)


class TestServer(ScimServerContract):
    expected_results = {expected}

    @pytest.fixture
    def scim_client(self):
        return None
"""


def test_failures_on_an_exception_show_its_traceback(pytester):
    """A check failing on an exception shows the traceback down to the code that raised it."""
    pytester.makepyfile(SERVER_RAISING.format(expected="{}"))

    result = pytester.runpytest("-v")

    result.assert_outcomes(failed=2)
    result.stdout.fnmatch_lines(
        [
            "    def delete_resource():",
            '>       raise RuntimeError("the storage is down")',
            "E       RuntimeError: the storage is down",
            "The above exception was the direct cause of the following exception:",
            "E * Failed: (None, 'a_check', None) ERROR: the storage is down",
        ]
    )
    result.stdout.no_fnmatch_line("*def _fail(*")


def test_an_expected_result_with_another_status_shows_the_traceback(pytester):
    """An expected failure with another status shows the traceback of the exception."""
    pytester.makepyfile(
        SERVER_RAISING.format(expected='{(None, "a_check", None): Status.DEVIATION}')
    )

    result = pytester.runpytest("-v")

    result.assert_outcomes(failed=2)
    result.stdout.fnmatch_lines(
        [
            "E       RuntimeError: the storage is down",
            "E * Failed: (None, 'a_check', None) Expected DEVIATION, "
            "got ERROR: the storage is down",
        ]
    )


def test_deviations_pass_with_a_warning(pytester):
    """The deviations pass, and emit a ScimDeviationWarning."""
    pytester.makepyfile(fake_server("DEVIATION"))

    result = pytester.runpytest("-v")

    result.stdout.fnmatch_lines(
        [
            "*ScimDeviationWarning: (None, 'a_check', None) the reason",
            "*= 1 passed, 1 warning, 1 subtests passed in *",
        ]
    )


def test_deviations_fail_when_their_warning_is_an_error(pytester):
    """The deviations fail when the ScimDeviationWarning is turned into an error."""
    pytester.makepyfile(fake_server("DEVIATION"))

    result = pytester.runpytest(
        "-v", "-W", "error::scim2_tester.testing.ScimDeviationWarning"
    )

    result.assert_outcomes(failed=2)


def test_the_class_attributes_select_the_checks(pytester):
    """The class attributes are given to iter_check_server to select the checks."""
    pytester.makepyfile(
        fake_server("SUCCESS")
        + """

class TestSelectedServer(TestServer):
    include_tags = {"crud"}
    exclude_tags = {"crud:delete"}
    resource_types = ["User"]
    seed = 1234


def test_calls():
    selected = {key: value for key, value in CALLS[1].items()}
    assert selected == {
        "include_tags": {"crud"},
        "exclude_tags": {"crud:delete"},
        "resource_types": ["User"],
        "seed": 1234,
    }
"""
    )

    result = pytester.runpytest("-v")

    result.assert_outcomes(passed=3)


def test_subtests_tell_the_resource_type_and_the_attribute(pytester):
    """A subtest tells the resource type and the attribute of its result."""
    pytester.makepyfile(
        fake_server("ERROR").replace(
            'reason="the reason"',
            'reason="the reason", resource_type="User", attribute="nickName"',
        )
    )

    result = pytester.runpytest("-v")

    result.stdout.fnmatch_lines(
        ["*SUBFAILED[[]a_check[]] (resource_type='User', attribute='nickName')*"]
    )


def test_a_random_seed_is_printed_without_a_seed(pytester):
    """Without a seed, the test draws one, gives it to iter_check_server and prints it."""
    pytester.makepyfile(
        fake_server("ERROR")
        + """

def test_seed():
    assert isinstance(CALLS[0]["seed"], int)
"""
    )

    result = pytester.runpytest("-v", "-p", "no:randomly")

    result.stdout.fnmatch_lines(["scim2-tester seed: *"])
    result.assert_outcomes(failed=2, passed=1)


def test_the_seed_is_printed_when_the_test_fails(pytester):
    """The seed of a failed run is printed, to replay it."""
    pytester.makepyfile(fake_server("ERROR") + "\n\nTestServer.seed = 1234\n")

    result = pytester.runpytest("-v")

    result.stdout.fnmatch_lines(["scim2-tester seed: 1234"])


def test_the_failures_are_printed_as_expected_results(pytester):
    """The failures are printed in the format of expected_results, with the known reasons."""
    pytester.makepyfile(
        fake_server(
            "ERROR",
            expected='{(None, "other_check", None): (Status.ERROR, "server#1")}',
        ).replace(
            "RESULTS = [",
            'RESULTS = [CheckResult(status=Status.ERROR, title="other_check"), '
            'CheckResult(status=Status.DEVIATION, title="third_check"), '
            'CheckResult(status=Status.SUCCESS, title="passing_check"), ',
        )
    )

    result = pytester.runpytest("-v")

    result.stdout.fnmatch_lines(
        [
            "Failures, in the format of expected_results:",
            "{",
            "    (None, 'a_check', None): Status.ERROR,",
            "    (None, 'other_check', None): (Status.ERROR, 'server#1'),",
            "    (None, 'third_check', None): Status.DEVIATION,",
            "}",
        ]
    )
    result.stdout.no_fnmatch_line("*(None, 'passing_check', None)*")


def test_a_run_without_failure_prints_no_expected_results(pytester):
    """A run without failure prints the seed, and no expected results."""
    pytester.makepyfile(fake_server("SUCCESS") + "\n\nTestServer.seed = 1234\n")

    result = pytester.runpytest("-v", "-s")

    result.stdout.fnmatch_lines(["*scim2-tester seed: 1234*"])
    result.stdout.no_fnmatch_line("*Failures, in the format of expected_results*")


@pytest.mark.parametrize("status", ["DEVIATION", "ERROR", "CRITICAL"])
def test_an_expected_result_is_an_expected_failure(pytester, status):
    """A result with its expected status is an expected failure, without warning."""
    pytester.makepyfile(
        fake_server(
            status, expected=f'{{(None, "a_check", None): (Status.{status}, "s#1")}}'
        )
    )

    result = pytester.runpytest("-v", "-rx")

    result.stdout.fnmatch_lines(
        [
            f"SUBXFAIL[[]a_check[]] *(None, 'a_check', None) {status}: s#1",
            "*= 1 passed, 1 xfailed in *",
        ]
    )


def test_an_expected_result_applies_to_all_the_results_with_its_key(pytester):
    """The results that have the same key are all compared to the expected status."""
    pytester.makepyfile(
        fake_server(
            "ERROR",
            "ERROR",
            expected='{(None, "a_check", None): (Status.ERROR, "s#1")}',
        )
    )

    result = pytester.runpytest("-v")

    result.stdout.fnmatch_lines(["*= 1 passed, 2 xfailed in *"])


@pytest.mark.parametrize("status", ["SUCCESS", "COMPLIANT", "ACCEPTABLE"])
def test_an_expected_result_that_now_passes_fails(pytester, status):
    """An expected failure that now passes fails, to be removed from the expected results."""
    pytester.makepyfile(
        fake_server(status, expected='{(None, "a_check", None): (Status.ERROR, "s#1")}')
    )

    result = pytester.runpytest("-v")

    result.assert_outcomes(failed=2)
    result.stdout.fnmatch_lines(
        [
            "(None, 'a_check', None) Expected ERROR (s#1), but the check now passes. "
            "Remove it from expected_results."
        ]
    )


@pytest.mark.parametrize("status", ["DEVIATION", "CRITICAL", "SKIPPED"])
def test_an_expected_result_with_another_status_fails(pytester, status):
    """An expected failure with another status fails."""
    pytester.makepyfile(
        fake_server(status, expected='{(None, "a_check", None): (Status.ERROR, "s#1")}')
    )

    result = pytester.runpytest("-v")

    result.assert_outcomes(failed=2)
    result.stdout.fnmatch_lines(
        [f"(None, 'a_check', None) Expected ERROR (s#1), got {status}: the reason"]
    )


def test_an_expected_result_without_result_fails(pytester):
    """An expected result that the checks do not return fails the test."""
    pytester.makepyfile(
        fake_server(
            "SUCCESS",
            expected='{("User", "renamed_check", "nickName"): (Status.ERROR, "s#1")}',
        )
    )

    result = pytester.runpytest("-v")

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            "The checks returned no result for these expected results:",
            "    ('User', 'renamed_check', 'nickName')",
        ]
    )


def test_the_printed_failures_are_sorted_by_key(pytester):
    """The printed failures are sorted by key, the keys without a value first."""
    pytester.makepyfile(
        fake_server("ERROR").replace(
            "RESULTS = [",
            'RESULTS = [CheckResult(status=Status.ERROR, title="b_check", '
            'resource_type="User"), '
            'CheckResult(status=Status.ERROR, title="a_check", resource_type="Group"), ',
        )
    )

    result = pytester.runpytest("-v")

    result.stdout.fnmatch_lines(
        [
            "{",
            "    (None, 'a_check', None): Status.ERROR,",
            "    ('Group', 'a_check', None): Status.ERROR,",
            "    ('User', 'b_check', None): Status.ERROR,",
            "}",
        ]
    )


def test_a_key_with_failing_and_passing_results_cannot_be_expected(pytester):
    """A key whose results have different statuses fails the test, and is not printed."""
    pytester.makepyfile(fake_server("SUCCESS", "ERROR"))

    result = pytester.runpytest("-v")

    result.stdout.fnmatch_lines(
        [
            "These keys have results with different statuses, "
            "and cannot be listed in expected_results:",
            "    (None, 'a_check', None)",
        ]
    )
    result.stdout.no_fnmatch_line("*Failures, in the format of expected_results*")


def test_a_key_with_passing_results_of_different_statuses_can_be_mixed(pytester):
    """A key whose results all pass, with different statuses, does not fail the test."""
    pytester.makepyfile(fake_server("SUCCESS", "COMPLIANT", "SKIPPED"))

    result = pytester.runpytest("-v")

    result.assert_outcomes(passed=1, skipped=1)


def test_the_failure_messages_tell_the_key_in_junit_reports(pytester):
    """The JUnit XML report, which does not name the subtests, tells the key of each failure."""
    pytester.makepyfile(
        fake_server("ERROR").replace(
            'reason="the reason"',
            'reason="the reason", resource_type="User", attribute="nickName"',
        )
    )

    pytester.runpytest("--junitxml=report.xml")

    report = (pytester.path / "report.xml").read_text()
    assert "('User', 'a_check', 'nickName') ERROR: the reason" in report


def test_an_expected_status_without_reason_is_an_expected_failure(pytester):
    """An expected result can be a status alone, without a reason."""
    pytester.makepyfile(
        fake_server("ERROR", expected='{(None, "a_check", None): Status.ERROR}')
    )

    result = pytester.runpytest("-v", "-rx")

    result.stdout.fnmatch_lines(
        [
            "SUBXFAIL[[]a_check[]] *(None, 'a_check', None) ERROR",
            "*= 1 passed, 1 xfailed in *",
        ]
    )


def test_an_expected_status_without_reason_tells_the_expected_status(pytester):
    """A result with another status than an expected status without reason fails."""
    pytester.makepyfile(
        fake_server("DEVIATION", expected='{(None, "a_check", None): Status.ERROR}')
    )

    result = pytester.runpytest("-v")

    result.assert_outcomes(failed=2)
    result.stdout.fnmatch_lines(
        ["(None, 'a_check', None) Expected ERROR, got DEVIATION: the reason"]
    )


def test_an_expected_status_without_reason_that_now_passes_fails(pytester):
    """An expected status without reason that now passes fails, to be removed."""
    pytester.makepyfile(
        fake_server("SUCCESS", expected='{(None, "a_check", None): Status.ERROR}')
    )

    result = pytester.runpytest("-v")

    result.stdout.fnmatch_lines(
        [
            "(None, 'a_check', None) Expected ERROR, but the check now passes. "
            "Remove it from expected_results."
        ]
    )


def test_each_result_is_reported_as_soon_as_its_check_ends(pytester):
    """A result is reported as a subtest before the next checks run."""
    pytester.makeconftest(
        """
SUBTEST_REPORTS = []


def pytest_runtest_logreport(report):
    if type(report).__name__ == "SubtestReport" and report.when == "call":
        SUBTEST_REPORTS.append(report)
"""
    )
    pytester.makepyfile(
        """
import pytest

import scim2_tester.testing
from conftest import SUBTEST_REPORTS
from scim2_tester import CheckResult
from scim2_tester import Status
from scim2_tester.testing import ScimServerContract

REPORTED_BEFORE_THE_SECOND_CHECK = []


def fake_iter_check_server(client, **kwargs):
    yield CheckResult(status=Status.SUCCESS, title="first_check")
    REPORTED_BEFORE_THE_SECOND_CHECK.append(len(SUBTEST_REPORTS))
    yield CheckResult(status=Status.SUCCESS, title="second_check")


@pytest.fixture(autouse=True)
def fake(monkeypatch):
    monkeypatch.setattr(scim2_tester.testing, "iter_check_server", fake_iter_check_server)


class TestServer(ScimServerContract):
    @pytest.fixture
    def scim_client(self):
        return None


def test_reports():
    assert REPORTED_BEFORE_THE_SECOND_CHECK == [1]
"""
    )

    result = pytester.runpytest("-v", "-p", "no:randomly")

    result.assert_outcomes(passed=2)
