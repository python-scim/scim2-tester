from collections.abc import Callable
from typing import Any

from scim2_models import Context
from scim2_models import Mutability
from scim2_models import Path
from scim2_models import Resource

from ..filling import fill_with_random_values
from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import check_result
from ..utils import checker
from ..utils import fields_equality
from ..utils import parametrize
from ..utils import resource_endpoint
from ._rejection_utils import INVALID_JSON
from ._rejection_utils import INVALID_JSON_HEADERS
from ._rejection_utils import rejection_result
from ._required_utils import check_required_attributes


@checker("crud:update")
def object_replacement(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate that PUT replaces the values of a resource.

    Creates a resource, then replaces it with new random values.
    Compares each read-write attribute in the PUT response, then in a GET of the resource.
    Returns one result per attribute.
    Attributes that the server does not return by default are not compared.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: The server returns the new value
    - :attr:`~scim2_tester.Status.ERROR`: The PUT fails,
      or the PUT response or the GET returns another value

    .. pull-quote:: :rfc:`RFC 7644 Section 3.5.1 <7644#section-3.5.1>`

       "readWrite, writeOnly: Any values provided SHALL replace the existing
       attribute values."

       "Unless otherwise specified, a successful PUT operation returns a 200
       OK response code and the entire resource within the response body."
    """
    test_obj = context.resource_manager.create_and_register(model)

    # Dirty hotfix, waiting to path management in scim2-models
    # to have a more generic way to do things
    # https://github.com/python-scim/scim2-models/issues/111
    # Store original immutable values to preserve them
    original_immutable_values = {}
    for field_name, field_info in model.model_fields.items():  # pragma: no cover
        # Check if field is immutable
        is_immutable = any(
            isinstance(metadata, Mutability) and metadata == Mutability.immutable
            for metadata in field_info.metadata
        )
        if is_immutable:
            original_value = getattr(test_obj, field_name, None)
            if original_value is not None:
                original_immutable_values[field_name] = original_value

    modified_obj = fill_with_random_values(
        context,
        test_obj,
        mutability=[Mutability.read_write, Mutability.write_only, Mutability.immutable],
    )

    # Dirty hotfix, waiting to path management in scim2-models
    # to have a more generic way to do things
    # https://github.com/python-scim/scim2-models/issues/111
    # Restore original immutable values for non-complex fields
    if modified_obj is not None:
        for (
            field_name,
            original_value,
        ) in original_immutable_values.items():  # pragma: no cover
            # Only restore if it's not a complex list (like members)
            if not (
                isinstance(original_value, list)
                and original_value
                and hasattr(original_value[0], "__class__")
                and hasattr(original_value[0].__class__, "model_fields")
            ):
                setattr(modified_obj, field_name, original_value)

    if modified_obj is None:
        raise ValueError(
            f"Could not modify {model.__name__} object with mutable fields"
        )

    response = context.client.replace(
        modified_obj, expected_status_codes=context.conf.expected_status_codes or [200]
    )
    queried = context.client.query(model, test_obj.id)

    expected = _returned_by_default(modified_obj)
    return [
        _replaced_value_result(context, path, expected, response, queried)
        for path in _compared_paths(model)
        if path.get(expected) is not None
    ]


def _returned_by_default(resource: Resource[Any]) -> Resource[Any]:
    """Return the resource without the values that the server does not return by default.

    The write-only values and the values returned never or on request are removed,
    including in sub-attributes.
    """
    return type(resource).model_validate(
        resource.model_dump(scim_ctx=Context.RESOURCE_REPLACEMENT_RESPONSE)
    )


def _compared_paths(model: type[Resource[Any]]) -> list[Path[Any]]:
    """Return the read-write attributes, without the extensions themselves."""
    return [
        path
        for path in parametrize(Path, model).iter_paths(
            mutability=[Mutability.read_write], include_subattributes=False
        )
        if path.resolve() is not None
    ]


def _replaced_value_result(
    context: CheckContext,
    path: Path[Any],
    expected_resource: Resource[Any],
    response: Any,
    queried: Any,
) -> CheckResult:
    """Compare the value sent for an attribute with the PUT response and the GET."""
    urn = str(path)
    expected = path.get(expected_resource)
    if response is not None and not fields_equality(expected, path.get(response)):
        return _unreplaced_value_result(
            context, urn, expected, path.get(response), "PUT response"
        )

    if not fields_equality(expected, path.get(queried)):
        return _unreplaced_value_result(
            context, urn, expected, path.get(queried), "GET after PUT"
        )

    return check_result(
        context,
        status=Status.SUCCESS,
        reason=f"Successfully replaced attribute '{urn}'",
        attribute=urn,
        data={"urn": urn, "value": expected},
    )


def _unreplaced_value_result(
    context: CheckContext, urn: str, expected: Any, actual: Any, source: str
) -> CheckResult:
    return check_result(
        context,
        status=Status.ERROR,
        reason=(
            f"The {source} returned another value for '{urn}'.\n"
            f"Sent value: {expected}\n"
            f"Returned value: {actual}"
        ),
        attribute=urn,
        data={"urn": urn, "expected": expected, "actual": actual, "source": source},
    )


@checker("crud:update")
def object_replacement_without_required_attribute(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate that PUT rejects a resource without one of its required attributes.

    For each required attribute, creates a resource, then replaces it with the
    same resource without this attribute. Returns one result per attribute.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: The server answers 400 ``invalidValue``
    - :attr:`~scim2_tester.Status.ACCEPTABLE`: The server answers 400 without a ``scimType``
    - :attr:`~scim2_tester.Status.DEVIATION`: The server answers 400 with another
      ``scimType``, another 4xx status, or an error without a SCIM body
    - :attr:`~scim2_tester.Status.ERROR`: The server replaces the resource, or answers 5xx
    - :attr:`~scim2_tester.Status.SKIPPED`: The resource has no required attribute to check

    .. pull-quote:: :rfc:`RFC 7644 Section 3.5.1 <7644#section-3.5.1>`

       "If an attribute is "required", clients MUST specify the attribute in
       the PUT request."

    .. pull-quote:: :rfc:`RFC 7644 Section 3.12 <7644#section-3.12>`

       "invalidValue: A required value was missing, or the value specified was
       not compatible with the operation or attribute type."

    The ``scimType`` is optional in an error response, so a 400 without it is acceptable.
    """

    def request_for(path: Path[Any], endpoint: str) -> tuple[str, Callable[[], Any]]:
        resource = context.resource_manager.create_and_register(model)
        url = f"{endpoint}/{resource.id}"
        path.delete(resource)
        payload = resource.model_dump(scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST)

        def send() -> Any:
            return context.client.replace(
                model,
                payload,
                check_request_payload=False,
                expected_status_codes=None,
                raise_scim_errors=False,
                url=url,
            )

        return f"PUT {url} without {path}", send

    return check_required_attributes(
        context, model, "invalidValue", Status.ACCEPTABLE, request_for
    )


@checker("crud:update")
def object_replacement_with_invalid_syntax(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate that PUT rejects a body that is not valid JSON.

    Creates a resource, then replaces it with a truncated JSON body.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: The server answers 400 ``invalidSyntax``
    - :attr:`~scim2_tester.Status.ACCEPTABLE`: The server answers 400 without a ``scimType``
    - :attr:`~scim2_tester.Status.DEVIATION`: The server answers 400 with another
      ``scimType``, another 4xx status, or an error without a SCIM body
    - :attr:`~scim2_tester.Status.ERROR`: The server replaces the resource, or answers 5xx

    .. pull-quote:: :rfc:`RFC 7644 Section 3.12 <7644#section-3.12>`

       "invalidSyntax: The request body message structure was invalid or did
       not conform to the request schema."

    The ``scimType`` is optional in an error response, so a 400 without it is acceptable.
    """
    resource = context.resource_manager.create_and_register(model)
    url = f"{resource_endpoint(context, model)}/{resource.id}"

    def send() -> Any:
        return context.client.replace(
            model,
            {},
            check_request_payload=False,
            expected_status_codes=None,
            raise_scim_errors=False,
            url=url,
            content=INVALID_JSON,
            headers=INVALID_JSON_HEADERS,
        )

    return [
        rejection_result(
            context,
            f"PUT {url} with invalid JSON",
            send,
            "invalidSyntax",
            Status.ACCEPTABLE,
        )
    ]
