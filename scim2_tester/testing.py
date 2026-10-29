"""A test suite checking that a SCIM server follows the RFCs.

Subclass :class:`ScimServerContract` in the tests of a server, and give it a
``scim_client`` fixture returning a client of the server::

    import pytest
    from scim2_client.engines.wsgi import WSGISCIMClient
    from scim2_tester.testing import ScimServerContract


    class TestMyServer(ScimServerContract):
        @pytest.fixture
        def scim_client(self):
            return WSGISCIMClient(create_app(), base_url="http://localhost/scim/v2")

The suite needs the ``testing`` extra, which installs pytest.
"""

import secrets
import warnings

import pytest
from scim2_client import BaseSyncSCIMClient

from scim2_tester.checker import check_server
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status

ResultKey = tuple[str | None, str | None, str | None]
"""The key of a result: its resource type, its title and its attribute."""

PASSING_STATUSES = (Status.SUCCESS, Status.COMPLIANT, Status.ACCEPTABLE)
FAILING_STATUSES = (Status.DEVIATION, Status.ERROR, Status.CRITICAL)


class ScimDeviationWarning(UserWarning):
    """A server behavior that deviates from a recommendation of the RFCs.

    It is emitted for the :attr:`~scim2_tester.Status.DEVIATION` results. Turn it
    into an error to make such results fail::

        [tool.pytest.ini_options]
        filterwarnings = ["error::scim2_tester.testing.ScimDeviationWarning"]
    """


class ScimServerContract:
    """The checks of :func:`~scim2_tester.check_server`, as a pytest test.

    The test runs the checks once, and reports each result as a subtest:

    - :attr:`~scim2_tester.Status.SUCCESS`, :attr:`~scim2_tester.Status.COMPLIANT`
      and :attr:`~scim2_tester.Status.ACCEPTABLE` results pass;
    - :attr:`~scim2_tester.Status.SKIPPED` results are skipped;
    - :attr:`~scim2_tester.Status.DEVIATION` results pass, with a
      :class:`ScimDeviationWarning`;
    - :attr:`~scim2_tester.Status.ERROR` and :attr:`~scim2_tester.Status.CRITICAL`
      results fail.

    The results listed in :attr:`expected_results` are expected failures instead.

    The seed of the generated values, and the failures in the format of
    :attr:`expected_results`, are printed in the output of the test.
    """

    include_tags: set[str] | None = None
    """Execute only checks with at least one of these tags."""

    exclude_tags: set[str] | None = None
    """Skip checks with any of these tags."""

    resource_types: list[str] | None = None
    """Check only these resource types, for instance ``["User", "Group"]``."""

    seed: int | None = None
    """The seed of the generated values.

    Without a seed, each run sends new values. Set the seed printed by a failed run
    to replay it.
    """

    expected_results: dict[ResultKey, tuple[Status, str]] = {}
    """The known failures of the server, with their status and a reason.

    The key of a result is its :attr:`~scim2_tester.CheckResult.resource_type`, its
    :attr:`~scim2_tester.CheckResult.title` and its
    :attr:`~scim2_tester.CheckResult.attribute`. The reason is free text, printed
    in the report, such as a ticket URL or an explanation::

        expected_results = {
            ("User", "check_add_attribute", "nickName"): (
                Status.ERROR,
                "https://github.com/example/scim-server/issues/123",
            ),
            (None, "schemas_endpoint_methods", None): (
                Status.DEVIATION,
                "The server answers 404 to unknown methods",
            ),
        }

    A result with the expected status is an expected failure. A result with
    another status fails, including a result that now passes. An expected result
    that the checks do not return fails the test.

    A key applies to all the results that have it. When these results have
    different statuses and one of them fails, the key cannot be expected, and
    the test fails.
    """

    def test_check_server(
        self, scim_client: BaseSyncSCIMClient, subtests: pytest.Subtests
    ) -> None:
        """The server passes the checks of scim2-tester."""
        seed = secrets.randbelow(2**32) if self.seed is None else self.seed
        results = check_server(
            scim_client,
            include_tags=self.include_tags,
            exclude_tags=self.exclude_tags,
            resource_types=self.resource_types,
            seed=seed,
        )
        statuses = _statuses_by_key(results)
        ambiguous = sorted(
            (
                key
                for key, key_statuses in statuses.items()
                if len(key_statuses) > 1 and key_statuses & set(FAILING_STATUSES)
            ),
            key=_sort_key,
        )

        print(f"scim2-tester seed: {seed}")
        if failures := _failures(results, self.expected_results, ambiguous):
            print(f"Failures, in the format of expected_results:\n{failures}")

        for result in results:
            expected = self.expected_results.get(result_key(result))
            with subtests.test(result.title, **_subtest_parameters(result)):
                _report(result, expected)

        problems = []
        missing = [key for key in self.expected_results if key not in statuses]
        if missing:
            problems.append(
                "The checks returned no result for these expected results:\n"
                + "\n".join(f"    {key!r}" for key in missing)
            )
        if ambiguous:
            problems.append(
                "These keys have results with different statuses, "
                "and cannot be listed in expected_results:\n"
                + "\n".join(f"    {key!r}" for key in ambiguous)
            )
        if problems:
            pytest.fail("\n".join(problems), pytrace=False)


def result_key(result: CheckResult) -> ResultKey:
    """Return the key of a result in :attr:`ScimServerContract.expected_results`."""
    return (result.resource_type, result.title, result.attribute)


def _sort_key(key: ResultKey) -> tuple[tuple[bool, str], ...]:
    """Sort the keys by their values, the keys without a value first."""
    return tuple((value is not None, value or "") for value in key)


def _statuses_by_key(results: list[CheckResult]) -> dict[ResultKey, set[Status]]:
    """Return the statuses of the results of each key."""
    statuses: dict[ResultKey, set[Status]] = {}
    for result in results:
        statuses.setdefault(result_key(result), set()).add(result.status)
    return statuses


def _subtest_parameters(result: CheckResult) -> dict[str, str]:
    """Return the parameters telling apart the results of a same check."""
    parameters = {"resource_type": result.resource_type, "attribute": result.attribute}
    return {key: value for key, value in parameters.items() if value is not None}


def _failures(
    results: list[CheckResult],
    expected_results: dict[ResultKey, tuple[Status, str]],
    ambiguous: list[ResultKey],
) -> str:
    """Return the failures of a run, in the format of the expected results, if any."""
    lines = {}
    for result in results:
        key = result_key(result)
        if result.status not in FAILING_STATUSES or key in ambiguous:
            continue
        reason = expected_results.get(key, (result.status, "TODO"))[1]
        lines[key] = f"    {key!r}: (Status.{result.status.name}, {reason!r}),"

    if not lines:
        return ""

    return (
        "{\n" + "".join(f"{lines[key]}\n" for key in sorted(lines, key=_sort_key)) + "}"
    )


def _report(result: CheckResult, expected: tuple[Status, str] | None) -> None:
    """Report a result as the outcome of the current subtest.

    The messages start with the key of the result, as some reports, such as
    JUnit XML, do not tell the subtests apart.
    """
    key = result_key(result)
    reason = result.reason or ""
    if expected is not None:
        _report_expected(result, *expected)

    if result.status == Status.SKIPPED:
        pytest.skip(f"{key!r} {reason}")

    if result.status == Status.DEVIATION:
        warnings.warn(f"{key!r} {reason}", ScimDeviationWarning, stacklevel=1)

    if result.status in (Status.ERROR, Status.CRITICAL):
        pytest.fail(f"{key!r} {result.status.name}: {reason}", pytrace=False)


def _report_expected(result: CheckResult, status: Status, expected_reason: str) -> None:
    """Report a result listed in the expected results."""
    key = result_key(result)
    if result.status == status:
        pytest.xfail(f"{key!r} {status.name}: {expected_reason}")

    if result.status in PASSING_STATUSES:
        pytest.fail(
            f"{key!r} Expected {status.name} ({expected_reason}), but the check now "
            "passes. Remove it from expected_results.",
            pytrace=False,
        )

    pytest.fail(
        f"{key!r} Expected {status.name} ({expected_reason}), "
        f"got {result.status.name}: {result.reason or ''}",
        pytrace=False,
    )
