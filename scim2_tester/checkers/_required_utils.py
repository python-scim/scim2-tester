"""Utility functions for the checks of the required attributes."""

from collections.abc import Callable
from typing import Any

from scim2_models import Mutability
from scim2_models import Path
from scim2_models import Required
from scim2_models import Resource

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import check_result
from ..utils import parametrize
from ..utils import resource_endpoint
from ._rejection_utils import rejection_result

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
        request, send = request_for(path, endpoint)
        results.append(
            rejection_result(
                context,
                request,
                send,
                scim_type,
                without_scim_type,
                attribute=str(path),
            )
        )
    return results
