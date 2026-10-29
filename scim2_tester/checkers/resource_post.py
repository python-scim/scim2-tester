from collections.abc import Callable
from typing import Any

from scim2_models import Context
from scim2_models import Path
from scim2_models import Required
from scim2_models import Resource

from ..filling import fill_with_random_values
from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import CreationNotSupportedError
from ..utils import Status
from ..utils import check_result
from ..utils import checker
from ..utils import resource_endpoint
from ._rejection_utils import INVALID_JSON
from ._rejection_utils import INVALID_JSON_HEADERS
from ._rejection_utils import rejection_result
from ._required_utils import check_required_attributes


@checker("crud:create")
def object_creation(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate SCIM resource creation via POST requests.

    Tests that resources can be successfully created using POST method on the
    appropriate resource endpoint, with automatic cleanup after validation.
    Creates a test object with all required fields populated with valid data.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Resource created successfully with valid response
    - :attr:`~scim2_tester.Status.ACCEPTABLE`: The server answers 501, as it does not support
      the creation of this resource type
    - :attr:`~scim2_tester.Status.ERROR`: Creation failed due to client/server error

    .. pull-quote:: :rfc:`RFC 7644 Section 3.3 - Creating Resources <7644#section-3.3>`

       "To create new resources, clients send HTTP POST requests to the resource
       endpoint, such as ``/Users`` or ``/Groups``."

       "If the resource is successfully created, the server SHALL return a ``201``
       'Created' response code with the newly created resource."

    .. pull-quote:: :rfc:`RFC 7644 Section 3.12 - HTTP Status and Error Response Handling <7644#section-3.12>`

       501 (Not Implemented): "Service provider does not support the request
       operation, e.g., PATCH."
    """
    try:
        created_obj = context.resource_manager.create_and_register(model)
    except CreationNotSupportedError as exc:
        return [check_result(context, status=Status.ACCEPTABLE, reason=str(exc))]

    return [
        check_result(
            context,
            status=Status.SUCCESS,
            reason=f"Successfully created {model.__name__} object with id {created_obj.id}",
            data=created_obj,
        )
    ]


@checker("crud:create")
def object_creation_without_required_attribute(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate that POST rejects a resource without one of its required attributes.

    For each required attribute, sends a resource with all the other required
    attributes, and without this one. Returns one result per attribute.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: The server answers 400 ``invalidValue``
    - :attr:`~scim2_tester.Status.ACCEPTABLE`: The server answers 400 without a ``scimType``
    - :attr:`~scim2_tester.Status.DEVIATION`: The server answers 400 with another
      ``scimType``, another 4xx status, or an error without a SCIM body
    - :attr:`~scim2_tester.Status.ERROR`: The server creates the resource, or answers 5xx
    - :attr:`~scim2_tester.Status.SKIPPED`: The resource has no required attribute to check

    .. pull-quote:: :rfc:`RFC 7644 Section 3.12 <7644#section-3.12>`

       "invalidValue: A required value was missing, or the value specified was
       not compatible with the operation or attribute type."

    The ``scimType`` is optional in an error response, so a 400 without it is acceptable.
    """

    def request_for(path: Path[Any], endpoint: str) -> tuple[str, Callable[[], Any]]:
        obj = fill_with_random_values(context, model(), required=[Required.true])
        path.delete(obj)
        payload = obj.model_dump(scim_ctx=Context.RESOURCE_CREATION_REQUEST)

        def send() -> Any:
            response = context.client.create(
                model,
                payload,
                check_request_payload=False,
                expected_status_codes=None,
                raise_scim_errors=False,
                url=endpoint,
            )
            if isinstance(response, dict) and response.get("id"):
                context.resource_manager.register(model(id=response["id"]))
            return response

        return f"POST {endpoint} without {path}", send

    return check_required_attributes(
        context, model, "invalidValue", Status.ACCEPTABLE, request_for
    )


@checker("crud:create")
def object_creation_with_invalid_syntax(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate that POST rejects a body that is not valid JSON.

    Sends a truncated JSON body to the resource endpoint.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: The server answers 400 ``invalidSyntax``
    - :attr:`~scim2_tester.Status.ACCEPTABLE`: The server answers 400 without a ``scimType``
    - :attr:`~scim2_tester.Status.DEVIATION`: The server answers 400 with another
      ``scimType``, another 4xx status, or an error without a SCIM body
    - :attr:`~scim2_tester.Status.ERROR`: The server creates a resource, or answers 5xx

    .. pull-quote:: :rfc:`RFC 7644 Section 3.12 <7644#section-3.12>`

       "invalidSyntax: The request body message structure was invalid or did
       not conform to the request schema."

    The ``scimType`` is optional in an error response, so a 400 without it is acceptable.
    """
    endpoint = resource_endpoint(context, model)

    def send() -> Any:
        response = context.client.create(
            model,
            {},
            check_request_payload=False,
            expected_status_codes=None,
            raise_scim_errors=False,
            url=endpoint,
            content=INVALID_JSON,
            headers=INVALID_JSON_HEADERS,
        )
        if isinstance(response, dict) and response.get("id"):
            context.resource_manager.register(model(id=response["id"]))
        return response

    return [
        rejection_result(
            context,
            f"POST {endpoint} with invalid JSON",
            send,
            "invalidSyntax",
            Status.ACCEPTABLE,
        )
    ]
