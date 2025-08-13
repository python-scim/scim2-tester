"""Utility functions for discovering available tags and resources."""

from scim2_tester.utils import get_registered_tags


def get_all_available_tags() -> list[str]:
    """Get all available tags from the global registry.

    This function returns tags that have been registered by checker decorators
    throughout the codebase. The registration happens automatically when
    modules containing @checker decorators are imported.

    :returns: Set of all unique tags found in the codebase.
    """
    import scim2_tester.checkers  # noqa: F401

    registered_tags = sorted(get_registered_tags())

    registered_tags = [tag for tag in registered_tags if tag != "*"]

    return registered_tags


def get_standard_resource_types() -> list[str]:
    """Get standard SCIM resource types.

    :returns: List of standard resource type names.
    """
    return ["User", "Group"]
