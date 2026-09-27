import argparse
import re

from httpx2 import Client
from scim2_client.engines.httpx2 import SyncSCIMClient

from scim2_tester.checker import check_server

_CONTROL_CHARACTERS = re.compile(
    "[\x00-\x08\x0b-\x1f\x7f-\x9f\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]"
)


def _escape_control_characters(text: object) -> str:
    """Replace the control characters of a text by their escaped form.

    The server writes part of the report, and the terminal would interpret
    the escape sequences it sends.
    """
    return _CONTROL_CHARACTERS.sub(
        lambda match: match.group().encode("unicode_escape").decode(), str(text)
    )


def cli() -> None:
    parser = argparse.ArgumentParser(description="SCIM server compliance checker.")
    parser.add_argument("host")
    parser.add_argument("--token", required=False)
    parser.add_argument("--verbose", required=False, action="store_true")
    parser.add_argument(
        "--include-tags",
        nargs="+",
        help="Run only checks with these tags",
        required=False,
    )
    parser.add_argument(
        "--exclude-tags",
        nargs="+",
        help="Skip checks with these tags",
        required=False,
    )
    parser.add_argument(
        "--resource-types",
        nargs="+",
        help="Filter by resource type names",
        required=False,
    )
    args = parser.parse_args()

    client = Client(
        base_url=args.host,
        headers={"Authorization": f"Bearer {args.token}"} if args.token else None,
    )
    scim = SyncSCIMClient(client)
    scim.discover()  # type: ignore[no-untyped-call]

    include_tags: set[str] | None = (
        set(args.include_tags) if args.include_tags else None
    )
    exclude_tags: set[str] | None = (
        set(args.exclude_tags) if args.exclude_tags else None
    )

    results = check_server(
        scim,
        include_tags=include_tags,
        exclude_tags=exclude_tags,
        resource_types=args.resource_types,
    )

    for result in results:
        title = _escape_control_characters(result.title)
        resource_info = (
            f" [{_escape_control_characters(result.resource_type)}]"
            if result.resource_type
            else ""
        )
        print(f"{result.status.name} {title}{resource_info}")
        if result.reason:
            print("  ", _escape_control_characters(result.reason))
            if args.verbose and result.data:
                print("  ", _escape_control_characters(result.data))
