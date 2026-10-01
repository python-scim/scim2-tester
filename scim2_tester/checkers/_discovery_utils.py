"""Utility functions for discovery endpoint testing."""

from typing import Protocol
from typing import cast

from scim2_client import SCIMClientException
from scim2_models import SCIMException

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import check_result


class _RawResponse(Protocol):
    status_code: int


class _RawClient(Protocol):
    def request(self, method: str, url: str) -> _RawResponse: ...


class _EngineClient(Protocol):
    """A SCIM client engine exposing the HTTP client it sends requests with."""

    client: _RawClient


def _test_discovery_endpoint_methods(
    context: CheckContext, endpoint: str
) -> list[CheckResult]:
    """Test that unsupported HTTP methods return 405 Method Not Allowed.

    Tests that POST, PUT, PATCH, and DELETE methods on the specified discovery
    endpoint correctly return HTTP 405 Method Not Allowed status, as only GET is supported.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: All unsupported methods return 405 status
    - :attr:`~scim2_tester.Status.ERROR`: One or more methods return unexpected status

    .. pull-quote:: :rfc:`RFC 7644 Section 4 - Discovery <7644#section-4>`

       Discovery endpoints only support GET method. Other HTTP methods
       should return appropriate error responses.
    """
    results = []
    methods = ["POST", "PUT", "PATCH", "DELETE"]

    for method in methods:
        try:
            response = cast("_EngineClient", context.client).client.request(
                method=method,
                url=endpoint,
            )
            if response.status_code == 405:
                results.append(
                    check_result(
                        context,
                        status=Status.SUCCESS,
                        reason=f"{method} {endpoint} correctly returned 405 Method Not Allowed",
                        data=response,
                    )
                )
            else:
                results.append(
                    check_result(
                        context,
                        status=Status.ERROR,
                        reason=f"{method} {endpoint} returned {response.status_code} instead of 405",
                        data=response,
                    )
                )
        except (SCIMClientException, SCIMException) as e:
            results.append(
                check_result(
                    context,
                    status=Status.ERROR,
                    reason=f"{method} {endpoint} failed: {str(e)}",
                )
            )

    return results
