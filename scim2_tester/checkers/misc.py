import uuid
from typing import Any

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

       "When returning HTTP error status codes other than a '401' 'Unauthorized',
       '403' 'Forbidden', or '404' 'Not Found', the server SHOULD return
       a SCIM error response."

       For 404 responses specifically, servers SHOULD return proper :class:`~scim2_models.Error`
       objects to maintain consistent error handling across all endpoints.
    """
    probably_invalid_url = f"/{str(uuid.uuid4())}"
    response: Any = context.client.query(
        url=probably_invalid_url, raise_scim_errors=False
    )

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
