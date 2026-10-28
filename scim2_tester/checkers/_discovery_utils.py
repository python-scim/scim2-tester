"""Utility functions for discovery endpoint testing."""

from typing import Any

from scim2_client import SCIMClientException
from scim2_models import SCIMException

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import check_result

_SEVERITY = [Status.SUCCESS, Status.DEVIATION, Status.ERROR]


def _method_status(status_code: int) -> Status:
    """Return the status of a discovery endpoint answering a method other than GET."""
    if status_code == 405:
        return Status.SUCCESS

    if 400 <= status_code < 500 or status_code == 501:
        return Status.DEVIATION

    return Status.ERROR


def _test_discovery_endpoint_methods(
    context: CheckContext, endpoint: str
) -> list[CheckResult]:
    """Test that a discovery endpoint refuses the methods other than GET.

    Sends POST, PUT, PATCH and DELETE requests to the endpoint, and expects
    405 Method Not Allowed for each one. The result has the status of the worst
    answer, and its reason lists the methods that did not answer 405.
    """
    methods = ["POST", "PUT", "PATCH", "DELETE"]
    statuses = []
    problems = []
    responses: dict[str, Any] = {}

    for method in methods:
        try:
            response = context.client.request(method, endpoint)
        except (SCIMClientException, SCIMException) as e:
            statuses.append(Status.ERROR)
            problems.append(f"{method} {endpoint} failed: {e}")
            continue

        responses[method] = response
        status = _method_status(response.status_code)
        statuses.append(status)
        if status != Status.SUCCESS:
            problems.append(
                f"{method} {endpoint} returned {response.status_code} instead of 405"
            )

    reason = (
        "; ".join(problems)
        if problems
        else f"{', '.join(methods)} {endpoint} correctly returned 405 Method Not Allowed"
    )
    return [
        check_result(
            context,
            status=max(statuses, key=_SEVERITY.index),
            reason=reason,
            data=responses,
        )
    ]
