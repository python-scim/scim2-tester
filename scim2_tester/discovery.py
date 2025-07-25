"""Utility functions for discovering available tags and resources."""

from scim2_tester.utils import get_registered_tags


def get_all_available_tags() -> set[str]:
    """Get all available tags from the global registry.

    This function returns tags that have been registered by checker decorators
    throughout the codebase. The registration happens automatically when
    modules containing @checker decorators are imported.

    :returns: Set of all unique tags found in the codebase.
    :rtype: set[str]
    """
    # Import all scim2_tester modules to ensure decorators are executed
    _ensure_modules_imported()

    # Get registered tags from the global registry
    registered_tags = get_registered_tags()

    return registered_tags


def _ensure_modules_imported() -> None:
    """Ensure all scim2_tester modules are imported to register their tags."""
    # Import key modules that contain checker decorators
    try:
        import scim2_tester.checker  # noqa: F401
        import scim2_tester.resource_delete  # noqa: F401
        import scim2_tester.resource_get  # noqa: F401
        import scim2_tester.resource_post  # noqa: F401
        import scim2_tester.resource_put  # noqa: F401
        import scim2_tester.resource_types  # noqa: F401
        import scim2_tester.schemas  # noqa: F401
        import scim2_tester.service_provider_config  # noqa: F401
    except ImportError:
        pass  # In case some modules don't exist or have import issues


def get_standard_resource_types() -> list[str]:
    """Get standard SCIM resource types.

    :returns: List of standard resource type names.
    :rtype: list[str]
    """
    return ["User", "Group"]
