"""Utility functions for discovery endpoint testing."""

from scim2_client import SCIMClientException
from scim2_models import SCIMException

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import check_result


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
    405 Method Not Allowed for each one.
    """
    results = []
    methods = ["POST", "PUT", "PATCH", "DELETE"]

    for method in methods:
        try:
            response = context.client.request(method, endpoint)
        except (SCIMClientException, SCIMException) as e:
            results.append(
                check_result(
                    context,
                    status=Status.ERROR,
                    reason=f"{method} {endpoint} failed: {str(e)}",
                )
            )
            continue

        status = _method_status(response.status_code)
        reason = (
            f"{method} {endpoint} correctly returned 405 Method Not Allowed"
            if status == Status.SUCCESS
            else f"{method} {endpoint} returned {response.status_code} instead of 405"
        )
        results.append(
            check_result(context, status=status, reason=reason, data=response)
        )

    return results
