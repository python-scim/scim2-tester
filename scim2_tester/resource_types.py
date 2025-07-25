import uuid

from scim2_models import Error
from scim2_models import ResourceType

from .utils import CheckConfig
from .utils import CheckResult
from .utils import Status
from .utils import checker


def check_resource_types_endpoint(conf: CheckConfig) -> list[CheckResult]:
    """As described in RFC7644 §4 <rfc7644#section-4>`, `/ResourceTypes` is a mandatory endpoint, and should only be accessible by GET.

    .. todo::

        - Check POST/PUT/PATCH/DELETE on the endpoint
        - Check that query parameters are ignored
        - Check that query parameters are ignored
        - Check that a 403 response is returned if a filter is passed
        - Check that the `schema` attribute exists and is available.
    """
    resource_types_result = check_query_all_resource_types(conf)
    results = [resource_types_result]

    if resource_types_result.status == Status.SUCCESS:
        for resource_type in resource_types_result.data:
            results.append(check_query_resource_type_by_id(conf, resource_type))

    results.append(check_access_invalid_resource_type(conf))

    return results


@checker("discovery", "resource-types")
def check_query_all_resource_types(conf: CheckConfig) -> CheckResult:
    response = conf.client.query(
        ResourceType, expected_status_codes=conf.expected_status_codes or [200]
    )
    available = ", ".join([f"'{resource.name}'" for resource in response.resources])
    reason = f"Resource types available are: {available}"
    return CheckResult(
        conf, status=Status.SUCCESS, reason=reason, data=response.resources
    )


@checker("discovery", "resource-types")
def check_query_resource_type_by_id(
    conf: CheckConfig, resource_type: ResourceType
) -> CheckResult:
    response = conf.client.query(
        ResourceType,
        resource_type.id,
        expected_status_codes=conf.expected_status_codes or [200],
    )
    if isinstance(response, Error):
        return CheckResult(
            conf, status=Status.ERROR, reason=response.detail, data=response
        )

    reason = f"Successfully accessed the /ResourceTypes/{resource_type.id} endpoint."
    return CheckResult(conf, status=Status.SUCCESS, reason=reason, data=response)


@checker("discovery", "resource-types")
def check_access_invalid_resource_type(conf: CheckConfig) -> CheckResult:
    probably_invalid_id = str(uuid.uuid4())
    response = conf.client.query(
        ResourceType,
        probably_invalid_id,
        expected_status_codes=conf.expected_status_codes or [404],
        raise_scim_errors=False,
    )

    if not isinstance(response, Error):
        return CheckResult(
            conf,
            status=Status.ERROR,
            reason=f"/resource_types/{probably_invalid_id} invalid URL did not return an Error object",
            data=response,
        )

    if response.status != 404:
        return CheckResult(
            conf,
            status=Status.ERROR,
            reason=f"/resource_types/{probably_invalid_id} invalid URL did return an object, but the status code is {response.status}",
            data=response,
        )

    return CheckResult(
        conf,
        status=Status.SUCCESS,
        reason=f"/resource_types/{probably_invalid_id} invalid URL correctly returned a 404 error",
        data=response,
    )
