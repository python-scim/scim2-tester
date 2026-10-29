"""Utility functions for the checks of the required attributes."""

from collections.abc import Callable
from typing import Any

from scim2_client import SCIMClientException
from scim2_client import UnexpectedStatusCodeException
from scim2_models import Error
from scim2_models import Mutability
from scim2_models import Path
from scim2_models import Required
from scim2_models import Resource
from scim2_models import SCIMException

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import _exception_data
from ..utils import _exception_reason
from ..utils import check_result
from ..utils import parametrize

RequestFor = Callable[[Path[Any], str], tuple[str, Callable[[], Any]]]
"""Return the label of a request leaving out an attribute, and a function sending it."""


def required_attributes(model: type[Resource[Any]]) -> list[Path[Any]]:
    """Return the required attributes of a model that a client can write."""
    return list(
        parametrize(Path, model).iter_paths(
            required=[Required.true],
            mutability=[
                Mutability.read_write,
                Mutability.write_only,
                Mutability.immutable,
            ],
            include_subattributes=False,
        )
    )


def resource_endpoint(context: CheckContext, model: type[Resource[Any]]) -> str:
    """Return the endpoint of the resource type a model is served on."""
    provider = context.client.provider
    return next(
        str(resource_type.endpoint)
        for resource_type in provider.resource_types
        if provider.model_for(resource_type) is model
    )


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


def check_required_attributes(
    context: CheckContext,
    model: type[Resource[Any]],
    scim_type: str,
    without_scim_type: Status,
    request_for: RequestFor,
) -> list[CheckResult]:
    """Send a request leaving out each required attribute, and check the server rejects it."""
    paths = required_attributes(model)
    if not paths:
        return [
            check_result(
                context,
                status=Status.SKIPPED,
                reason=f"No required attribute to check for {model.__name__}",
            )
        ]

    endpoint = resource_endpoint(context, model)
    results = []
    for path in paths:
        attribute = str(path)
        request, send = request_for(path, endpoint)
        try:
            response = send()
        except UnexpectedStatusCodeException as exc:
            response = exc
        except (SCIMClientException, SCIMException) as exc:
            results.append(
                check_result(
                    context,
                    status=Status.ERROR,
                    reason=f"{request} failed: {_exception_reason(exc)}",
                    data=_exception_data(exc),
                    attribute=attribute,
                )
            )
            continue

        status, reason = rejection_status(response, scim_type, without_scim_type)
        data = (
            _exception_data(response) if isinstance(response, Exception) else response
        )
        results.append(
            check_result(
                context,
                status=status,
                reason=f"{request}: {reason}",
                data=data,
                attribute=attribute,
            )
        )
    return results
