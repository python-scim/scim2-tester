import uuid
from typing import Any

from scim2_client import UnexpectedStatusCodeException
from scim2_models import Error

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import check_result
from ..utils import checker


@checker("misc")
def random_url(context: CheckContext) -> list[CheckResult]:
    """Validate server error handling for non-existent endpoints.

    Tests that the server properly returns a :class:`~scim2_models.Error` object with HTTP 404 status
    when accessing invalid or non-existent URLs, ensuring compliance with SCIM
    error handling requirements.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Server returns valid :class:`~scim2_models.Error` object with 404 status
    - :attr:`~scim2_tester.Status.ERROR`: Server returns non-:class:`~scim2_models.Error` object or incorrect status code

    .. pull-quote:: :rfc:`RFC 7644 Section 3.12 - Error Response Handling <7644#section-3.12>`

       "In addition to returning an HTTP response code, implementers MUST return
       the errors in the body of the response in a JSON format"
    """
    probably_invalid_url = f"/{str(uuid.uuid4())}"
    try:
        response: Any = context.client.query(
            url=probably_invalid_url, raise_scim_errors=False
        )
    except UnexpectedStatusCodeException as exc:
        return [
            check_result(
                context,
                status=Status.ERROR,
                reason=f"{probably_invalid_url} did not return an Error object: {exc}",
                data=exc,
            )
        ]

    if not isinstance(response, Error):
        return [
            check_result(
                context,
                status=Status.ERROR,
                reason=f"{probably_invalid_url} did not return an Error object",
                data=response,
            )
        ]

    if response.status != 404:
        return [
            check_result(
                context,
                status=Status.ERROR,
                reason=f"{probably_invalid_url} did return an object, but the status code is {response.status}",
                data=response,
            )
        ]

    return [
        check_result(
            context,
            status=Status.SUCCESS,
            reason=f"{probably_invalid_url} correctly returned a 404 error",
            data=response,
        )
    ]
