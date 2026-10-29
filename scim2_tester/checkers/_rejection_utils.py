"""Utility functions for the checks of the requests a server should reject."""

from collections.abc import Callable
from typing import Any

from scim2_client import SCIMClientException
from scim2_client import UnexpectedStatusCodeException
from scim2_models import Error
from scim2_models import SCIMException

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import _exception_data
from ..utils import _exception_reason
from ..utils import check_result

INVALID_JSON = b'{"schemas": ['
"""A request body that is not valid JSON."""

INVALID_JSON_HEADERS = {"Content-Type": "application/scim+json"}
"""The headers of :data:`INVALID_JSON`, so the server reads it as SCIM."""


def rejection_status(
    response: Any, scim_type: str, without_scim_type: Status
) -> tuple[Status, str]:
    """Return the status of a server answering a request it should reject.

    The server should answer 400 with the given ``scimType``. Another error
    status or ``scimType`` is a deviation, as the server still rejects the
    request. A 5xx error or a success is an error.
    """
    if isinstance(response, UnexpectedStatusCodeException):
        status = Status.DEVIATION if 400 <= response.status_code < 500 else Status.ERROR
        return (
            status,
            f"the server answered {response.status_code} without a SCIM error",
        )

    if not isinstance(response, Error):
        return Status.ERROR, "the server accepted the request"

    if response.status is None or not 400 <= response.status < 500:
        return Status.ERROR, f"the server answered {response.status}"

    if response.status != 400:
        return Status.DEVIATION, f"the server answered {response.status} instead of 400"

    if response.scim_type == scim_type:
        return Status.SUCCESS, f"the server answered 400 {scim_type}"

    if response.scim_type is None:
        return without_scim_type, "the server answered 400 without a scimType"

    return (
        Status.DEVIATION,
        f"the server answered 400 {response.scim_type} instead of {scim_type}",
    )


def rejection_result(
    context: CheckContext,
    request: str,
    send: Callable[[], Any],
    scim_type: str,
    without_scim_type: Status,
    attribute: str | None = None,
) -> CheckResult:
    """Send a request the server should reject, and grade its answer."""
    try:
        response = send()
    except UnexpectedStatusCodeException as exc:
        response = exc
    except (SCIMClientException, SCIMException) as exc:
        return check_result(
            context,
            status=Status.ERROR,
            reason=f"{request} failed: {_exception_reason(exc)}",
            data=_exception_data(exc),
            attribute=attribute,
        )

    status, reason = rejection_status(response, scim_type, without_scim_type)
    data = _exception_data(response) if isinstance(response, Exception) else response
    return check_result(
        context,
        status=status,
        reason=f"{request}: {reason}",
        data=data,
        attribute=attribute,
    )
