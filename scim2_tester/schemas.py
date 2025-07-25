import uuid

from scim2_models import Error
from scim2_models import Schema

from .utils import CheckConfig
from .utils import CheckResult
from .utils import Status
from .utils import checker


def check_schemas_endpoint(conf: CheckConfig) -> list[CheckResult]:
    """As described in RFC7644 §4 <rfc7644#section-4>`, `/ResourceTypes` is a mandatory endpoint, and should only be accessible by GET.

    .. todo::

        - Check the POST/PUT/PATCH/DELETE methods on the endpoint
        - Check accessing every subschema with /Schemas/urn:ietf:params:scim:schemas:core:2.0:User
        - Check that query parameters are ignored
        - Check that a 403 response is returned if a filter is passed
        - Check that the 'ResourceType', 'ServiceProviderConfig' and 'Schema' schemas are provided.
    """
    schemas_result = check_query_all_schemas(conf)
    results = [schemas_result]

    if schemas_result.status == Status.SUCCESS:
        for resource_type in schemas_result.data:
            results.append(check_query_schema_by_id(conf, resource_type))

    results.append(check_access_invalid_schema(conf))

    return results


@checker("discovery", "schemas")
def check_query_all_schemas(conf: CheckConfig) -> CheckResult:
    response = conf.client.query(
        Schema, expected_status_codes=conf.expected_status_codes or [200]
    )
    available = ", ".join([f"'{resource.name}'" for resource in response.resources])
    return CheckResult(
        conf,
        status=Status.SUCCESS,
        reason=f"Schemas available are: {available}",
        data=response.resources,
    )


@checker("discovery", "schemas")
def check_query_schema_by_id(conf: CheckConfig, schema: Schema) -> CheckResult:
    response = conf.client.query(
        Schema,
        schema.id,
        expected_status_codes=conf.expected_status_codes or [200],
    )
    if isinstance(response, Error):
        return CheckResult(
            conf, status=Status.ERROR, reason=response.detail, data=response
        )

    reason = f"Successfully accessed the /Schemas/{schema.id} endpoint."
    return CheckResult(conf, status=Status.SUCCESS, reason=reason, data=response)


@checker("discovery", "schemas")
def check_access_invalid_schema(conf: CheckConfig) -> CheckResult:
    probably_invalid_id = str(uuid.uuid4())
    response = conf.client.query(
        Schema,
        probably_invalid_id,
        expected_status_codes=conf.expected_status_codes or [404],
        raise_scim_errors=False,
    )

    if not isinstance(response, Error):
        return CheckResult(
            conf,
            status=Status.ERROR,
            reason=f"/Schemas/{probably_invalid_id} invalid URL did not return an Error object",
            data=response,
        )

    if response.status != 404:
        return CheckResult(
            conf,
            status=Status.ERROR,
            reason=f"/Schemas/{probably_invalid_id} invalid URL did return an object, but the status code is {response.status}",
            data=response,
        )

    return CheckResult(
        conf,
        status=Status.SUCCESS,
        reason=f"/Schemas/{probably_invalid_id} invalid URL correctly returned a 404 error",
        data=response,
    )
