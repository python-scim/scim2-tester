from typing import Any

from scim2_models import ListResponse
from scim2_models import Mutability
from scim2_models import Required
from scim2_models import Resource
from scim2_models import ResponseParameters
from scim2_models import Returned
from scim2_models import SearchRequest

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import check_result
from ..utils import checker


def _pick_attribute_names(
    model: type[Resource[Any]],
) -> tuple[str | None, str | None]:
    """Pick two default-returned, non-required attribute names for testing.

    Returns a tuple ``(included, excluded)`` of serialization aliases.
    Either may be :data:`None` if the model does not have enough suitable attributes.
    """
    candidates: list[str] = []
    for field_name, field_info in model.model_fields.items():
        returnability = model.get_field_annotation(field_name, Returned)
        mutability = model.get_field_annotation(field_name, Mutability)
        required = model.get_field_annotation(field_name, Required)
        if (
            returnability == Returned.default
            and mutability != Mutability.read_only
            and required != Required.true
            and field_name not in ("schemas", "meta", "id")
        ):
            alias = field_info.serialization_alias or field_name
            candidates.append(alias)

    included = candidates[0] if len(candidates) >= 1 else None
    excluded = candidates[1] if len(candidates) >= 2 else None
    return included, excluded


def _check_attribute_filtering(
    response_data: dict[str, Any],
    included: str | None,
    excluded: str | None,
    model_name: str,
    endpoint: str,
) -> tuple[Status, str]:
    """Verify that the response honours ``attributes`` or ``excludedAttributes``.

    Returns a ``(status, reason)`` pair.
    """
    if included is not None and included not in response_data:
        return (
            Status.ERROR,
            f"{endpoint}: requested attribute '{included}' missing "
            f"from {model_name} response",
        )

    if excluded is not None and excluded in response_data:
        return (
            Status.ERROR,
            f"{endpoint}: excluded attribute '{excluded}' still present "
            f"in {model_name} response",
        )

    return Status.SUCCESS, f"{endpoint}: attribute filtering honoured for {model_name}"


def _find_resource_in_list(
    response: ListResponse[Resource[Any]] | Any,
    resource_id: str,
) -> dict[str, Any] | None:
    """Find a resource by id in a list response and return its dumped dict."""
    if isinstance(response, ListResponse):
        for r in response.resources:
            if r.id == resource_id:
                return r.model_dump()
    return None


def _run_single_attribute_check(
    context: CheckContext,
    model: type[Resource[Any]],
    test_obj: Resource[Any],
    query_parameters: ResponseParameters,
    included: str | None,
    excluded: str | None,
    query_fn: Any,
    endpoint: str,
) -> CheckResult:
    """Run a single inclusion or exclusion check.

    :param query_fn: callable that takes a :class:`ResponseParameters` and returns
        a single :class:`Resource` or a :class:`ListResponse`.
    :param endpoint: human-readable endpoint label for messages.
    """
    response = query_fn(query_parameters)

    if isinstance(response, Resource) and not isinstance(response, ListResponse):
        response_data = response.model_dump()
    elif isinstance(response, ListResponse):
        response_data = _find_resource_in_list(response, test_obj.id)
        if response_data is None:
            return check_result(
                context,
                status=Status.ERROR,
                reason=f"{endpoint}: could not find {model.__name__} "
                f"with id {test_obj.id} in filtered results",
                data=response,
            )
    else:
        return check_result(
            context,
            status=Status.ERROR,
            reason=f"{endpoint}: unexpected response type {type(response).__name__}",
            data=response,
        )

    status, reason = _check_attribute_filtering(
        response_data, included, excluded, model.__name__, endpoint
    )
    return check_result(context, status=status, reason=reason, data=response)


def _run_attribute_checks(
    context: CheckContext,
    model: type[Resource[Any]],
    test_obj: Resource[Any],
    included: str | None,
    excluded: str | None,
    query_fn: Any,
    endpoint: str,
) -> list[CheckResult]:
    """Run inclusion and exclusion checks using the given query function.

    :param query_fn: callable that takes a :class:`ResponseParameters` and returns
        a single :class:`Resource` or a :class:`ListResponse`.
    :param endpoint: human-readable endpoint label for messages.
    """
    results: list[CheckResult] = []

    if included is not None:
        results.append(
            _run_single_attribute_check(
                context,
                model,
                test_obj,
                ResponseParameters(attributes=[included]),
                included=included,
                excluded=None,
                query_fn=query_fn,
                endpoint=endpoint,
            )
        )

    if excluded is not None:
        results.append(
            _run_single_attribute_check(
                context,
                model,
                test_obj,
                ResponseParameters(excluded_attributes=[excluded]),
                included=None,
                excluded=excluded,
                query_fn=query_fn,
                endpoint=endpoint,
            )
        )

    return results


@checker("crud:read:attributes")
def object_query_with_attributes(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate that GET on a single resource honours ``attributes`` and ``excludedAttributes``.

    Creates a resource with all writable fields populated, then retrieves it
    twice: once with ``attributes`` restricting the response to a single
    attribute, and once with ``excludedAttributes`` hiding another attribute.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Server correctly filters response attributes
    - :attr:`~scim2_tester.Status.ERROR`: Server ignores attribute filtering parameters
    - :attr:`~scim2_tester.Status.SKIPPED`: Model has no suitable attributes to test

    .. pull-quote:: :rfc:`RFC 7644 Section 3.4.1 <7644#section-3.4.1>`

       "Clients MAY request a partial resource representation on any
       operation that returns a resource within the response by specifying
       either of the mutually exclusive URL query parameters ``attributes``
       or ``excludedAttributes``."
    """
    included, excluded = _pick_attribute_names(model)
    if included is None and excluded is None:
        return [
            check_result(
                context,
                status=Status.SKIPPED,
                reason=f"No suitable attributes to test filtering on {model.__name__}",
            )
        ]

    test_obj = context.resource_manager.create_and_register(model, fill_all=True)

    def query_fn(query_parameters: ResponseParameters) -> Any:
        return context.client.query(
            model,
            test_obj.id,
            query_parameters=query_parameters,
            expected_status_codes=context.conf.expected_status_codes or [200],
        )

    return _run_attribute_checks(
        context, model, test_obj, included, excluded, query_fn, "GET /Resource/{id}"
    )


@checker("crud:read:attributes")
def object_list_with_attributes(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate that GET on the collection endpoint honours ``attributes`` and ``excludedAttributes``.

    Creates a resource with all writable fields populated, then lists the
    collection twice: once with ``attributes`` and once with
    ``excludedAttributes``.  Verifies that the created resource appears in
    the list and that its serialized form respects the filtering parameters.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Server correctly filters list response attributes
    - :attr:`~scim2_tester.Status.ERROR`: Server ignores attribute filtering on list endpoint
    - :attr:`~scim2_tester.Status.SKIPPED`: Model has no suitable attributes to test

    .. pull-quote:: :rfc:`RFC 7644 Section 3.4.2 <7644#section-3.4.2>`

       "Clients MAY use the ``attributes`` query parameter to request
       particular attributes be included in a query response."
    """
    included, excluded = _pick_attribute_names(model)
    if included is None and excluded is None:
        return [
            check_result(
                context,
                status=Status.SKIPPED,
                reason=f"No suitable attributes to test filtering on {model.__name__}",
            )
        ]

    test_obj = context.resource_manager.create_and_register(model, fill_all=True)

    def query_fn(query_parameters: ResponseParameters) -> Any:
        return context.client.query(
            model,
            query_parameters=query_parameters,
            expected_status_codes=context.conf.expected_status_codes or [200],
        )

    return _run_attribute_checks(
        context, model, test_obj, included, excluded, query_fn, "GET /Resource"
    )


@checker("crud:read:attributes")
def search_with_attributes(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate that POST ``/.search`` honours ``attributes`` and ``excludedAttributes``.

    Creates a resource with all writable fields populated, then issues
    ``/.search`` requests with attribute filtering.  Verifies that the
    created resource appears in the results and respects the filtering.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Server correctly filters search response attributes
    - :attr:`~scim2_tester.Status.ERROR`: Server ignores attribute filtering on search endpoint
    - :attr:`~scim2_tester.Status.SKIPPED`: Model has no suitable attributes to test

    .. pull-quote:: :rfc:`RFC 7644 Section 3.4.3 <7644#section-3.4.3>`

       "Clients MAY execute queries without passing parameters on the URL by
       using the HTTP POST verb combined with the ``/.search`` path extension."
    """
    included, excluded = _pick_attribute_names(model)
    if included is None and excluded is None:
        return [
            check_result(
                context,
                status=Status.SKIPPED,
                reason=f"No suitable attributes to test filtering on {model.__name__}",
            )
        ]

    test_obj = context.resource_manager.create_and_register(model, fill_all=True)

    def query_fn(query_parameters: ResponseParameters) -> Any:
        return context.client.search(
            search_request=SearchRequest(
                attributes=query_parameters.attributes,
                excluded_attributes=query_parameters.excluded_attributes,
            ),
            expected_status_codes=context.conf.expected_status_codes or [200],
        )

    return _run_attribute_checks(
        context, model, test_obj, included, excluded, query_fn, "POST /.search"
    )
