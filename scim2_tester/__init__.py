from scim2_tester.checker import check_server
from scim2_tester.discovery import get_all_available_tags
from scim2_tester.discovery import get_standard_resource_types
from scim2_tester.utils import CheckConfig
from scim2_tester.utils import CheckResult
from scim2_tester.utils import SCIMTesterError
from scim2_tester.utils import Status

__all__ = [
    "check_server",
    "Status",
    "CheckResult",
    "CheckConfig",
    "SCIMTesterError",
    "get_all_available_tags",
    "get_standard_resource_types",
]

if __name__ == "__main__":  # pragma: no cover
    from scim2_tester.cli import cli

    cli()
