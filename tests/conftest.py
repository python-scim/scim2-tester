import pytest
from scim2_client.engines.httpx2 import SyncSCIMClient
from scim2_models import EnterpriseUser
from scim2_models import Group
from scim2_models import ResourceType
from scim2_models import ScimProvider
from scim2_models import User

from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckContext
from tests.utils import Client


@pytest.fixture
def provider():
    return ScimProvider(
        models=[User, EnterpriseUser, Group],
        resource_types=[
            ResourceType.from_resource(User[EnterpriseUser]),
            ResourceType.from_resource(Group),
        ],
    )


@pytest.fixture
def scim_client(httpserver, provider):
    with Client(base_url=f"http://localhost:{httpserver.port}") as client:
        yield SyncSCIMClient(client, provider=provider)


@pytest.fixture
def testing_context(scim_client):
    conf = CheckConfig()
    return CheckContext(scim_client, conf)
