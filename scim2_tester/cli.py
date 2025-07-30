import argparse

from httpx import Client
from scim2_client.engines.httpx import SyncSCIMClient

from scim2_tester.checker import check_server


def cli():
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
        resource_info = f" [{result.resource_type}]" if result.resource_type else ""
        print(f"{result.status.name} {result.title}{resource_info}")
        if result.reason:
            print("  ", result.reason)
            if args.verbose and result.data:
                print("  ", result.data)
