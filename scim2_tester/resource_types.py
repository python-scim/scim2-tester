import uuid

from scim2_models import Error
from scim2_models import ResourceType

from .utils import CheckContext
from .utils import CheckResult
from .utils import Status
from .utils import checker


def check_resource_types_endpoint(context: CheckContext) -> list[CheckResult]:
    """As described in RFC7644 §4 <rfc7644#section-4>`, `/ResourceTypes` is a mandatory endpoint, and should only be accessible by GET.

    .. todo::

        - Check POST/PUT/PATCH/DELETE on the endpoint
        - Check that query parameters are ignored
        - Check that query parameters are ignored
        - Check that a 403 response is returned if a filter is passed
        - Check that the `schema` attribute exists and is available.
    """
    resource_types_result = check_query_all_resource_types(context)
    results = [resource_types_result]

    if resource_types_result.status == Status.SUCCESS:
        for resource_type in resource_types_result.data:
            results.append(check_query_resource_type_by_id(context, resource_type))

    results.append(check_access_invalid_resource_type(context))

    return results


@checker("discovery", "resource-types")
def check_query_all_resource_types(context: CheckContext) -> CheckResult:
    response = context.client.query(
        ResourceType, expected_status_codes=context.conf.expected_status_codes or [200]
    )
    available = ", ".join([f"'{resource.name}'" for resource in response.resources])
    reason = f"Resource types available are: {available}"
    return CheckResult(
        context.conf, status=Status.SUCCESS, reason=reason, data=response.resources
    )


@checker("discovery", "resource-types")
def check_query_resource_type_by_id(
    context: CheckContext, resource_type: ResourceType
) -> CheckResult:
    response = context.client.query(
        ResourceType,
        resource_type.id,
        expected_status_codes=context.conf.expected_status_codes or [200],
    )
    if isinstance(response, Error):
        return CheckResult(
            context.conf, status=Status.ERROR, reason=response.detail, data=response
        )

    reason = f"Successfully accessed the /ResourceTypes/{resource_type.id} endpoint."
    return CheckResult(
        context.conf, status=Status.SUCCESS, reason=reason, data=response
    )


@checker("discovery", "resource-types")
def check_access_invalid_resource_type(context: CheckContext) -> CheckResult:
    probably_invalid_id = str(uuid.uuid4())
    response = context.client.query(
        ResourceType,
        probably_invalid_id,
        expected_status_codes=context.conf.expected_status_codes or [404],
        raise_scim_errors=False,
    )

    if not isinstance(response, Error):
        return CheckResult(
            context.conf,
            status=Status.ERROR,
            reason=f"/resource_types/{probably_invalid_id} invalid URL did not return an Error object",
            data=response,
        )

    if response.status != 404:
        return CheckResult(
            context.conf,
            status=Status.ERROR,
            reason=f"/resource_types/{probably_invalid_id} invalid URL did return an object, but the status code is {response.status}",
            data=response,
        )

    return CheckResult(
        context.conf,
        status=Status.SUCCESS,
        reason=f"/resource_types/{probably_invalid_id} invalid URL correctly returned a 404 error",
        data=response,
    )
