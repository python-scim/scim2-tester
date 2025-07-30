import uuid
from typing import Any

from scim2_models import Error

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import checker


@checker("misc")
def random_url(context: CheckContext) -> CheckResult:
    """Check that a request to a random URL returns a 404 Error object."""
    probably_invalid_url = f"/{str(uuid.uuid4())}"
    response: Any = context.client.query(
        url=probably_invalid_url, raise_scim_errors=False
    )

    if not isinstance(response, Error):
        return CheckResult(
            status=Status.ERROR,
            reason=f"{probably_invalid_url} did not return an Error object",
            data=response,
        )

    if response.status != 404:
        return CheckResult(
            status=Status.ERROR,
            reason=f"{probably_invalid_url} did return an object, but the status code is {response.status}",
            data=response,
        )

    return CheckResult(
        status=Status.SUCCESS,
        reason=f"{probably_invalid_url} correctly returned a 404 error",
        data=response,
    )
