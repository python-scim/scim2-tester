import re

from scim2_models import Context
from scim2_models import Error
from scim2_models import ListResponse
from scim2_models import Schema

from scim2_tester.checkers.schemas import _schemas_endpoint
from scim2_tester.utils import Status


def test_shemas_endpoint(httpserver, check_config):
    """Test a fully functional schemas endpoint."""
    schemas = [model.to_schema() for model in check_config.client.resource_models]
    httpserver.expect_request(re.compile(r"^/Schemas$")).respond_with_json(
        ListResponse[Schema](
            resources=schemas,
            total_results=len(schemas),
        ).model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=200,
        content_type="application/scim+json",
    )
    for schema in schemas:
        httpserver.expect_request(
            re.compile(rf"^/Schemas/{schema.id}$")
        ).respond_with_json(
            schema.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
            status=200,
            content_type="application/scim+json",
        )
    httpserver.expect_request(re.compile(r"^/Schemas/.*$")).respond_with_json(
        Error(status=404, detail="Schema Not Found").model_dump(),
        status=404,
        content_type="application/scim+json",
    )

    results = _schemas_endpoint(check_config)

    assert all(result.status == Status.SUCCESS for result in results)


def test_missing_query_endpoint(httpserver, check_config):
    """Test that individual Schema endpoints are missing."""
    schemas = [model.to_schema() for model in check_config.client.resource_models]
    httpserver.expect_request(re.compile(r"^/Schemas$")).respond_with_json(
        ListResponse[Schema](
            resources=schemas,
            total_results=len(schemas),
        ).model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        status=200,
        content_type="application/scim+json",
    )
    results = _schemas_endpoint(check_config)

    assert all(result.status == Status.ERROR for result in results[1:])
