import re

from scim2_models import Context
from scim2_models import Error
from scim2_models import ListResponse
from scim2_models import ResourceType

from scim2_tester.checkers import resource_types_endpoint
from scim2_tester.utils import Status


def test_resource_types_endpoint(httpserver, check_config):
    """Test a fully functional resource types endpoint."""
    httpserver.expect_request(re.compile(r"^/ResourceTypes$")).respond_with_json(
        ListResponse[ResourceType](
            resources=check_config.client.resource_types,
            total_results=len(check_config.client.resource_types),
        ).model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=200,
        content_type="application/scim+json",
    )
    for resource_type in check_config.client.resource_types:
        httpserver.expect_request(
            re.compile(rf"^/ResourceTypes/{resource_type.id}$")
        ).respond_with_json(
            resource_type.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
            status=200,
            content_type="application/scim+json",
        )
    httpserver.expect_request(re.compile(r"^/ResourceTypes/.*$")).respond_with_json(
        Error(status=404, detail="ResourceType Not Found").model_dump(),
        status=404,
        content_type="application/scim+json",
    )

    results = resource_types_endpoint(check_config)

    assert all(result.status == Status.SUCCESS for result in results)


def test_resource_missing_query_endpoint(httpserver, check_config):
    """Test that individual ResourceType endpoints are missing."""
    httpserver.expect_request(re.compile(r"^/ResourceTypes$")).respond_with_json(
        ListResponse[ResourceType](
            resources=check_config.client.resource_types,
            total_results=len(check_config.client.resource_types),
        ).model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=200,
        content_type="application/scim+json",
    )
    results = resource_types_endpoint(check_config)

    assert all(result.status == Status.ERROR for result in results[1:])
