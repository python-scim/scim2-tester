import pytest
from scim2_client import SCIMClientException
from scim2_client.engines.httpx2 import SyncSCIMClient
from scim2_models import Group
from scim2_models import ScimProvider
from scim2_models import User

from scim2_tester.checker import check_server
from tests.utils import Client


def test_raise_exceptions():
    """Test that exceptions are raised instead of stored in a Result object when 'raise_exceptions' is True."""
    client = Client(base_url="https://invalid.test")
    scim = SyncSCIMClient(client, provider=ScimProvider(models=[User, Group]))
    with pytest.raises(SCIMClientException):
        check_server(scim, raise_exceptions=True)
