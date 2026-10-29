from collections.abc import Callable
from typing import Any

from scim2_client import SCIMClientException
from scim2_models import Mutability
from scim2_models import NotImplementedException
from scim2_models import Path
from scim2_models import Resource
from scim2_models import ResponseParameters
from scim2_models import Returned
from scim2_models import SCIMException
from scim2_models import SearchRequest

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import _exception_data
from ..utils import _exception_reason
from ..utils import check_result
from ..utils import checker
from ..utils import parametrize

ATTRIBUTES = "attributes"
EXCLUDED_ATTRIBUTES = "excludedAttributes"

Fetch = Callable[
    [
        CheckContext,
        type[Resource[Any]],
        str | None,
        ResponseParameters[Any] | None,
    ],
    Any,
]
"""Return a resource from an endpoint, or :data:`None` if it is not in the response."""


def _is_assigned(value: Any) -> bool:
    """Tell whether a value is assigned. Per RFC 7643 §2.5, an empty array is not."""
    return value is not None and value != []


def _candidate_attributes(
    model: type[Resource[Any]],
) -> list[tuple[Path[Any], Returned, Mutability | None]]:
    """Return the attributes of a model, with their returned and mutability annotations."""
    candidates = []
    for path in parametrize(Path, model).iter_paths(include_subattributes=False):
        binding = path.resolve()
        returned = binding.get_annotation(Returned) if binding else None
        if binding is None or returned is None:
            continue

        candidates.append((path, returned, binding.get_annotation(Mutability)))
    return candidates


def _is_testable(
    path: Path[Any],
    returned: Returned,
    mutability: Mutability | None,
    baseline: Resource[Any],
) -> bool:
    """Tell whether the server has a value to return for an attribute.

    Attributes returned by default must be in the response without parameters.
    Attributes returned on request are not, but the check sent them a value,
    unless they are read-only.
    """
    if returned == Returned.never:
        return True

    if returned == Returned.request:
        return mutability != Mutability.read_only

    return _is_assigned(path.get(baseline))


def _returned_attributes(
    model: type[Resource[Any]], parameter: str, path: Path[Any]
) -> set[str]:
    """Return the attributes a response keeps when a parameter holds one attribute."""
    attributes = [path] if parameter == ATTRIBUTES else None
    excluded = [path] if parameter == EXCLUDED_ATTRIBUTES else None
    paths = parametrize(Path, model).iter_paths(
        include_subattributes=False,
        attributes=attributes,
        excluded_attributes=excluded,
    )
    return {str(returned) for returned in paths}


def _attribute_problems(
    candidates: list[tuple[Path[Any], Returned, Mutability | None]],
    baseline: Resource[Any],
    resource: Resource[Any],
    returned: set[str],
    requested: str,
) -> tuple[list[str], list[str]]:
    """Return the attributes missing from a response, and the unexpected ones."""
    missing = []
    unexpected = []
    for path, _, _ in candidates:
        attribute = str(path)
        expected = attribute in returned
        present = _is_assigned(path.get(resource))
        if present and not expected:
            unexpected.append(attribute)
        elif (
            expected
            and not present
            and (attribute == requested or _is_assigned(path.get(baseline)))
        ):
            missing.append(attribute)
    return missing, unexpected


def _find_resource(response: Any, resource_id: str | None) -> Resource[Any] | None:
    """Return a resource of a list response by its id, or :data:`None`."""
    resources = response.resources or []
    return next((r for r in resources if r.id == resource_id), None)


def _get_resource(
    context: CheckContext,
    model: type[Resource[Any]],
    resource_id: str | None,
    parameters: ResponseParameters[Any] | None,
) -> Any:
    return context.client.query(
        model,
        resource_id,
        query_parameters=parameters,
        expected_status_codes=context.conf.expected_status_codes or [200],
    )


def _list_resource(
    context: CheckContext,
    model: type[Resource[Any]],
    resource_id: str | None,
    parameters: ResponseParameters[Any] | None,
) -> Any:
    response = context.client.query(
        model,
        query_parameters=parameters,
        expected_status_codes=context.conf.expected_status_codes or [200],
    )
    return _find_resource(response, resource_id)


def _search_resource(
    context: CheckContext,
    model: type[Resource[Any]],
    resource_id: str | None,
    parameters: ResponseParameters[Any] | None,
) -> Any:
    search_request = SearchRequest(
        attributes=parameters.attributes if parameters else None,
        excluded_attributes=parameters.excluded_attributes if parameters else None,
    )
    response = context.client.search(
        search_request=search_request,
        expected_status_codes=context.conf.expected_status_codes or [200],
        raise_scim_errors=True,
    )
    return _find_resource(response, resource_id)


def _check_attribute(
    context: CheckContext,
    model: type[Resource[Any]],
    candidates: list[tuple[Path[Any], Returned, Mutability | None]],
    baseline: Resource[Any],
    fetch: Fetch,
    endpoint: str,
    parameter: str,
    path: Path[Any],
) -> CheckResult:
    """Request a resource with one attribute in a parameter, and check the response."""
    attribute = str(path)
    request = f"{endpoint} with {parameter}={attribute}"
    parameters: ResponseParameters[Any] = (
        ResponseParameters(attributes=[path])
        if parameter == ATTRIBUTES
        else ResponseParameters(excluded_attributes=[path])
    )
    try:
        resource = fetch(context, model, baseline.id, parameters)
    except (SCIMClientException, SCIMException) as exc:
        return check_result(
            context,
            status=Status.ERROR,
            reason=f"{request} failed: {_exception_reason(exc)}",
            data=_exception_data(exc),
            attribute=attribute,
        )

    if resource is None:
        return check_result(
            context,
            status=Status.ERROR,
            reason=f"{request}: the {model.__name__} {baseline.id} is not in the response",
            attribute=attribute,
        )

    returned = _returned_attributes(model, parameter, path)
    missing, unexpected = _attribute_problems(
        candidates, baseline, resource, returned, attribute
    )
    if not missing and not unexpected:
        return check_result(
            context,
            status=Status.SUCCESS,
            reason=f"{request}: the response has the expected attributes",
            data=resource,
            attribute=attribute,
        )

    problems = []
    if missing:
        problems.append(f"missing {', '.join(missing)}")
    if unexpected:
        problems.append(f"unexpected {', '.join(unexpected)}")
    return check_result(
        context,
        status=Status.ERROR,
        reason=f"{request}: {'; '.join(problems)}",
        data=resource,
        attribute=attribute,
    )


def _check_parameter(
    context: CheckContext,
    model: type[Resource[Any]],
    fetch: Fetch,
    endpoint: str,
    parameter: str,
) -> list[CheckResult]:
    """Check a parameter on each attribute of a model, one result per attribute.

    A request without parameters gives the attributes the server has a value for.
    """
    test_obj = context.resource_manager.create_and_register(model, fill_all=True)
    baseline = fetch(context, model, test_obj.id, None)
    if baseline is None:
        return [
            check_result(
                context,
                status=Status.ERROR,
                reason=f"{endpoint}: the {model.__name__} {test_obj.id} is not in the response",
            )
        ]

    candidates = _candidate_attributes(model)
    results = [
        _check_attribute(
            context, model, candidates, baseline, fetch, endpoint, parameter, path
        )
        for path, returned, mutability in candidates
        if _is_testable(path, returned, mutability, baseline)
    ]
    if not results:
        return [
            check_result(
                context,
                status=Status.SKIPPED,
                reason=f"No attribute of {model.__name__} to check {parameter} on",
            )
        ]

    return results


@checker("crud:read:attributes")
def object_query_with_attributes(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate that GET on a single resource honours ``attributes``.

    Creates a resource with all writable attributes, then retrieves it once per
    attribute, with ``attributes`` set to this attribute. Returns one result per
    attribute.

    The response must have the requested attribute, unless it is never returned,
    and the attributes that are always returned. It must not have the other
    attributes.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: The response has the expected attributes
    - :attr:`~scim2_tester.Status.ERROR`: An attribute is missing or unexpected
    - :attr:`~scim2_tester.Status.SKIPPED`: The resource has no attribute to check

    .. pull-quote:: :rfc:`RFC 7644 Section 3.4.2.5 <7644#section-3.4.2.5>`

       "attributes: A multi-valued list of strings indicating the names of
       resource attributes to return in the response, overriding the set of
       attributes that would be returned by default."
    """
    return _check_parameter(
        context, model, _get_resource, "GET /Resource/{id}", ATTRIBUTES
    )


@checker("crud:read:attributes")
def object_query_with_excluded_attributes(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate that GET on a single resource honours ``excludedAttributes``.

    Creates a resource with all writable attributes, then retrieves it once per
    attribute, with ``excludedAttributes`` set to this attribute. Returns one
    result per attribute.

    The response must not have the excluded attribute, unless it is always
    returned. It must have the other attributes returned by default.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: The response has the expected attributes
    - :attr:`~scim2_tester.Status.ERROR`: An attribute is missing or unexpected
    - :attr:`~scim2_tester.Status.SKIPPED`: The resource has no attribute to check

    .. pull-quote:: :rfc:`RFC 7644 Section 3.4.2.5 <7644#section-3.4.2.5>`

       "excludedAttributes: A multi-valued list of strings indicating the names
       of resource attributes to be removed from the default set of attributes
       to return. This parameter SHALL have no effect on attributes whose
       schema "returned" setting is "always"."
    """
    return _check_parameter(
        context, model, _get_resource, "GET /Resource/{id}", EXCLUDED_ATTRIBUTES
    )


@checker("crud:read:attributes")
def object_list_with_attributes(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate that GET on the collection endpoint honours ``attributes``.

    Same as ``object_query_with_attributes``, on the list of the resources.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: The response has the expected attributes
    - :attr:`~scim2_tester.Status.ERROR`: An attribute is missing or unexpected,
      or the resource is not in the list
    - :attr:`~scim2_tester.Status.SKIPPED`: The resource has no attribute to check

    .. pull-quote:: :rfc:`RFC 7644 Section 3.4.2 <7644#section-3.4.2>`

       "Clients MAY use the ``attributes`` query parameter to request
       particular attributes be included in a query response."
    """
    return _check_parameter(context, model, _list_resource, "GET /Resource", ATTRIBUTES)


@checker("crud:read:attributes")
def object_list_with_excluded_attributes(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate that GET on the collection endpoint honours ``excludedAttributes``.

    Same as ``object_query_with_excluded_attributes``, on the list of the resources.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: The response has the expected attributes
    - :attr:`~scim2_tester.Status.ERROR`: An attribute is missing or unexpected,
      or the resource is not in the list
    - :attr:`~scim2_tester.Status.SKIPPED`: The resource has no attribute to check

    .. pull-quote:: :rfc:`RFC 7644 Section 3.4.2.5 <7644#section-3.4.2.5>`

       "excludedAttributes: A multi-valued list of strings indicating the names
       of resource attributes to be removed from the default set of attributes
       to return."
    """
    return _check_parameter(
        context, model, _list_resource, "GET /Resource", EXCLUDED_ATTRIBUTES
    )


@checker("crud:read:attributes")
def search_with_attributes(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate that POST ``/.search`` honours ``attributes``.

    Same as ``object_query_with_attributes``, on a search at the root.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: The response has the expected attributes
    - :attr:`~scim2_tester.Status.ERROR`: An attribute is missing or unexpected,
      or the resource is not in the results
    - :attr:`~scim2_tester.Status.SKIPPED`: The resource has no attribute to check,
      or the server does not search several resource types at once

    .. pull-quote:: :rfc:`RFC 7644 Section 3.4.3 <7644#section-3.4.3>`

       "Clients MAY execute queries without passing parameters on the URL by
       using the HTTP POST verb combined with the ``/.search`` path extension."

    .. pull-quote:: :rfc:`RFC 7644 Section 3.12 <7644#section-3.12>`

       "501 (Not Implemented): Service provider does not support the request
       operation, e.g., PATCH."

    A server that does not search several resource types at once answers 501.
    The service provider configuration has no attribute to announce it.
    """
    return _check_search(context, model, ATTRIBUTES)


@checker("crud:read:attributes")
def search_with_excluded_attributes(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate that POST ``/.search`` honours ``excludedAttributes``.

    Same as ``object_query_with_excluded_attributes``, on a search at the root.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: The response has the expected attributes
    - :attr:`~scim2_tester.Status.ERROR`: An attribute is missing or unexpected,
      or the resource is not in the results
    - :attr:`~scim2_tester.Status.SKIPPED`: The resource has no attribute to check,
      or the server does not search several resource types at once

    .. pull-quote:: :rfc:`RFC 7644 Section 3.4.3 <7644#section-3.4.3>`

       "Clients MAY execute queries without passing parameters on the URL by
       using the HTTP POST verb combined with the ``/.search`` path extension."

    A server that does not search several resource types at once answers 501.
    """
    return _check_search(context, model, EXCLUDED_ATTRIBUTES)


def _check_search(
    context: CheckContext, model: type[Resource[Any]], parameter: str
) -> list[CheckResult]:
    """Check a parameter on a search at the root, or skip if the server answers 501."""
    try:
        return _check_parameter(
            context, model, _search_resource, "POST /.search", parameter
        )
    except NotImplementedException:
        return [
            check_result(
                context,
                status=Status.SKIPPED,
                reason="POST /.search: searching several resource types at once "
                "is not supported by the server",
            )
        ]
