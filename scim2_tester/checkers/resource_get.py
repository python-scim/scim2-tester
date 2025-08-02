from typing import Any

from scim2_models import Resource
from scim2_models import ResourceType

from ..utils import CheckContext
from ..utils import CheckResult
from ..utils import Status
from ..utils import checker


def _model_from_resource_type(
    context: CheckContext, resource_type: ResourceType
) -> type[Resource[Any]] | None:
    """Resolve Resource model class from ResourceType metadata.

    Maps a :class:`~scim2_models.ResourceType` object (containing schema URIs and metadata) to the
    corresponding Python model class registered in the SCIM client.
    """
    for resource_model in context.client.resource_models:
        if resource_model.model_fields["schemas"].default[0] == resource_type.schema_:
            return resource_model

    return None


@checker("crud:read")
def object_query(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate SCIM resource retrieval by ID via GET requests.

    Tests that individual resources can be successfully retrieved using GET method
    on the resource endpoint with specific resource ID, with automatic cleanup.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Resource retrieved successfully with valid data
    - :attr:`~scim2_tester.Status.ERROR`: Failed to retrieve or received invalid response

    .. pull-quote:: :rfc:`RFC 7644 Section 3.4.1 - Retrieving a Known Resource <7644#section-3.4.1>`

       "Clients retrieve a known resource using an HTTP GET request to the resource
       endpoint, such as ``/Users/{id}`` or ``/Groups/{id}``."

       "If successful, the server responds with HTTP status code 200 (OK) and includes
       the target resource within the response body."
    """
    test_obj = context.resource_manager.create_and_register(model)

    response = context.client.query(
        model,
        test_obj.id,
        expected_status_codes=context.conf.expected_status_codes or [200],
    )

    return [
        CheckResult(
            status=Status.SUCCESS,
            reason=f"Successfully queried {model.__name__} object with id {test_obj.id}",
            data=response,
        )
    ]


@checker("crud:read")
def object_query_without_id(
    context: CheckContext, model: type[Resource[Any]]
) -> list[CheckResult]:
    """Validate SCIM resource listing via GET requests without ID.

    Tests that resources can be successfully listed using GET method on the
    collection endpoint, validating bulk retrieval with automatic cleanup.

    **Status:**

    - :attr:`~scim2_tester.Status.SUCCESS`: Resources listed successfully, created resource found
    - :attr:`~scim2_tester.Status.ERROR`: Failed to list resources or created resource not found

    .. pull-quote:: :rfc:`RFC 7644 Section 3.4.2 - List/Query Resources <7644#section-3.4.2>`

       "To query resources, clients send GET requests to the resource endpoint
       (e.g., ``/Users`` or ``/Groups``). The response to a successful query
       operation SHALL be a JSON structure that matches the ListResponse schema."
    """
    test_obj = context.resource_manager.create_and_register(model)

    response = context.client.query(
        model, expected_status_codes=context.conf.expected_status_codes or [200]
    )

    found = any(test_obj.id == resource.id for resource in response.resources)
    if not found:
        return [
            CheckResult(
                status=Status.ERROR,
                reason=f"Could not find {model.__name__} object with id {test_obj.id} in list response",
                data=response,
            )
        ]

    return [
        CheckResult(
            status=Status.SUCCESS,
            reason=f"Successfully found {model.__name__} object with id {test_obj.id} in list response",
            data=response,
        )
    ]
