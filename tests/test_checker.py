"""Test the main checker functionality."""

import re

import pytest
from scim2_client.engines.httpx2 import SyncSCIMClient
from scim2_client.engines.wsgi import WSGISCIMClient
from scim2_models import Context
from scim2_models import Error
from scim2_models import ListResponse
from scim2_models import Patch
from scim2_models import ResourceType
from scim2_models import Schema
from scim2_models import ScimProvider
from scim2_models import ServiceProviderConfig
from scim2_models import User

from scim2_tester.checker import check_server
from scim2_tester.utils import SCIMTesterError
from scim2_tester.utils import Status
from tests.utils import Client


def test_check_server_with_tag_filtering(httpserver):
    """Validates tag filtering includes specified tags and excludes others."""
    client = SyncSCIMClient(Client(base_url=httpserver.url_for("/")))

    results = check_server(client, include_tags={"discovery"})
    for result in results:
        assert any("discovery" in tag for tag in result.tags)

    results = check_server(client, exclude_tags={"crud"})
    for result in results:
        assert not any("crud" in tag for tag in result.tags)


def test_check_server_with_resource_type_filtering(scim2_server_app):
    """Validates resource type filtering excludes unwanted resource types."""
    client = WSGISCIMClient(scim2_server_app)

    all_results = check_server(client, include_tags={"discovery", "crud:read"})
    user_results = [
        r for r in all_results if getattr(r, "resource_type", None) == "User"
    ]
    group_results = [
        r for r in all_results if getattr(r, "resource_type", None) == "Group"
    ]
    assert user_results
    assert group_results

    filtered_results = check_server(
        client, resource_types=["User"], include_tags={"discovery", "crud:read"}
    )
    user_filtered = [
        r for r in filtered_results if getattr(r, "resource_type", None) == "User"
    ]
    group_filtered = [
        r for r in filtered_results if getattr(r, "resource_type", None) == "Group"
    ]
    assert user_filtered
    assert not group_filtered


def test_check_server_ignores_data_of_failed_discovery_checks(httpserver):
    """Ensures the debugging data of failed discovery checks is not registered on the client."""
    client = SyncSCIMClient(Client(base_url=httpserver.url_for("/")))

    results = check_server(client)

    assert client.provider.config is None
    assert client.provider.resource_types == ()
    assert client.provider.models == ()
    assert all(result.status == Status.ERROR for result in results)


def test_check_server_exception_handling(httpserver):
    """Ensures proper exception handling based on raise_exceptions parameter."""
    client = SyncSCIMClient(Client(base_url=httpserver.url_for("/")))

    results = check_server(client, raise_exceptions=False)
    assert isinstance(results, list)
    error_results = [r for r in results if r.status == Status.ERROR]
    assert len(error_results) > 0

    with pytest.raises((SCIMTesterError, Exception)):
        check_server(client, raise_exceptions=True)


def serve_discovery(httpserver, resource_type, schema):
    """Serve the discovery endpoints of a server publishing one resource type and one schema."""
    httpserver.expect_request("/ServiceProviderConfig").respond_with_json(
        ServiceProviderConfig(patch=Patch(supported=True)).model_dump(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE
        ),
        content_type="application/scim+json",
    )
    httpserver.expect_request("/ResourceTypes").respond_with_json(
        ListResponse[ResourceType](
            resources=[resource_type], total_results=1
        ).model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        content_type="application/scim+json",
    )
    httpserver.expect_request(f"/ResourceTypes/{resource_type.id}").respond_with_json(
        resource_type.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        content_type="application/scim+json",
    )
    httpserver.expect_request("/Schemas").respond_with_json(
        ListResponse[Schema](resources=[schema], total_results=1).model_dump(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE
        ),
        content_type="application/scim+json",
    )
    httpserver.expect_request(f"/Schemas/{schema.id}").respond_with_json(
        schema.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        content_type="application/scim+json",
    )
    httpserver.expect_request(
        re.compile(r"^/(Schemas|ResourceTypes)/.*$")
    ).respond_with_json(
        Error(status=404, detail="Not Found").model_dump(),
        status=404,
        content_type="application/scim+json",
    )


def test_check_server_reports_an_uncomposable_service_description(httpserver):
    """Ensures a resource type naming a schema the server does not publish is reported."""
    resource_type = ResourceType(
        id="Ghost",
        name="Ghost",
        endpoint="/Ghosts",
        schema_="urn:example:params:scim:schemas:Ghost",
    )
    serve_discovery(httpserver, resource_type, User.to_schema())

    results = check_server(SyncSCIMClient(Client(base_url=httpserver.url_for("/"))))

    description = [r for r in results if r.title == "service_description"]
    assert len(description) == 1
    assert description[0].status == Status.ERROR
    assert "urn:example:params:scim:schemas:Ghost" in description[0].reason


def failing_discovery(*args, **kwargs):
    raise TypeError("'FieldInfo' object is not iterable")


def test_check_server_reports_an_unexpected_service_description_failure(
    httpserver, monkeypatch
):
    """A failure of scim2-models while composing the models is reported, and the checks go on."""
    monkeypatch.setattr(ScimProvider, "from_discovery", failing_discovery)
    serve_discovery(httpserver, ResourceType.from_resource(User), User.to_schema())

    results = check_server(SyncSCIMClient(Client(base_url=httpserver.url_for("/"))))

    description = [r for r in results if r.title == "service_description"]
    assert len(description) == 1
    assert description[0].status == Status.ERROR
    assert "'FieldInfo' object is not iterable" in description[0].reason


def test_check_server_raises_on_an_unexpected_service_description_failure(
    httpserver, monkeypatch
):
    """With raise_exceptions, the failing service description stops the checks."""
    monkeypatch.setattr(ScimProvider, "from_discovery", failing_discovery)
    serve_discovery(httpserver, ResourceType.from_resource(User), User.to_schema())
    client = SyncSCIMClient(Client(base_url=httpserver.url_for("/")))

    with pytest.raises(SCIMTesterError):
        check_server(client, raise_exceptions=True)
