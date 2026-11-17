"""Utility functions for discovering available tags and resources."""

from scim2_tester.utils import get_registered_tags


def get_all_available_tags() -> list[str]:
    """Get the tags that can select the checks, in alphabetical order.

    The list holds the tags of the checks, and the tags above them.
    For instance, ``crud`` selects ``crud:read`` and ``crud:read:attributes``.
    """
    import scim2_tester.checkers  # noqa: F401

    tags: set[str] = set()
    for tag in get_registered_tags() - {"*"}:
        segments = tag.split(":")
        tags.update(":".join(segments[:end]) for end in range(1, len(segments) + 1))
    return sorted(tags)


def get_standard_resource_types() -> list[str]:
    """Get standard SCIM resource types.

    :returns: List of standard resource type names.
    """
    return ["User", "Group"]
