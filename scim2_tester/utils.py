import functools
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from enum import auto
from typing import Any

from scim2_client import SCIMClient
from scim2_client import SCIMClientError

# Global registry for all tags discovered by checker decorators
_REGISTERED_TAGS: set[str] = set()


def get_registered_tags() -> set[str]:
    """Get all tags that have been registered by checker decorators.

    :returns: Set of all registered tags.
    :rtype: set[str]
    """
    return _REGISTERED_TAGS.copy()


def _matches_hierarchical_tags(func_tags: set[str], filter_tags: set[str]) -> bool:
    """Check if function tags match filter tags using hierarchical logic.

    Supports patterns like:
    - "crud" matches "crud:read", "crud:create", etc.
    - "crud:read" matches exactly "crud:read"

    :param func_tags: Tags on the function
    :param filter_tags: Tags to filter by
    :returns: True if there's a match
    """
    for filter_tag in filter_tags:
        for func_tag in func_tags:
            # Exact match
            if filter_tag == func_tag:
                return True

            # Hierarchical match: filter "crud" matches func "crud:read"
            if ":" in func_tag and filter_tag in func_tag.split(":"):
                return True

    return False


class Status(Enum):
    SUCCESS = auto()
    ERROR = auto()
    SKIPPED = auto()


@dataclass
class CheckConfig:
    """Object used to configure the checks behavior."""

    client: SCIMClient
    """The SCIM client that will be used to perform the requests."""

    raise_exceptions: bool = False
    """Whether to raise exceptions or store them in a :class:`~scim2_tester.Result` object."""

    expected_status_codes: list[int] | None = None
    """The expected response status codes."""

    include_tags: set[str] | None = None
    """Execute only checks with at least one of these tags."""

    exclude_tags: set[str] | None = None
    """Skip checks with any of these tags."""

    resource_types: list[str] | None = None
    """Filter by resource type names (e.g., ["User", "Group"])."""


class SCIMTesterError(Exception):
    """Exception raised when a check failed and the `raise_exceptions` config parameter is :data:`True`."""

    def __init__(self, message: str, conf: CheckConfig):
        super().__init__()
        self.message = message
        self.conf = conf

    def __str__(self):
        return self.message


@dataclass
class CheckResult:
    """Store a check result."""

    conf: CheckConfig
    status: Status

    title: str | None = None
    """The title of the check."""

    description: str | None = None
    """What the check does, and why the spec advises it to do."""

    reason: str | None = None
    """Why it failed, or how it succeed."""

    data: Any | None = None
    """Any related data that can help to debug."""

    tags: set[str] = field(default_factory=set)
    """Tags associated with this check for filtering."""

    resource_type: str | None = None
    """The resource type name if this check is related to a specific resource."""

    def __post_init__(self):
        if self.conf.raise_exceptions and self.status == Status.ERROR:
            raise SCIMTesterError(self.reason, self)


def checker(*tags):
    """Decorate checker methods with tags for selective execution.

    - It adds a title and a description to the returned result, extracted from the method name and its docstring.
    - It catches SCIMClient errors.
    - It allows tagging checks for selective execution.
    - It skips execution based on tag filtering in CheckConfig.

    Usage:
        @checker("discovery", "schemas")
        def check_schemas_endpoint(...):
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapped(conf: CheckConfig, *args, **kwargs):
            func_tags = set(tags) if tags else set()

            # Check if function should be skipped based on tag filtering
            if conf.include_tags and not _matches_hierarchical_tags(
                func_tags, conf.include_tags
            ):
                return CheckResult(
                    conf,
                    status=Status.SKIPPED,
                    title=func.__name__,
                    description=func.__doc__,
                    tags=func_tags,
                    reason="Skipped due to tag filtering",
                )

            if conf.exclude_tags and _matches_hierarchical_tags(
                func_tags, conf.exclude_tags
            ):
                return CheckResult(
                    conf,
                    status=Status.SKIPPED,
                    title=func.__name__,
                    description=func.__doc__,
                    tags=func_tags,
                    reason="Skipped due to tag exclusion",
                )

            # Execute the function normally
            try:
                result = func(conf, *args, **kwargs)
            except SCIMClientError as exc:
                if conf.raise_exceptions:
                    raise

                reason = f"{exc} {exc.__cause__}" if exc.__cause__ else str(exc)
                result = CheckResult(
                    conf, status=Status.ERROR, reason=reason, data=exc.source
                )

            # decorate results
            if isinstance(result, CheckResult):
                result.title = func.__name__
                result.description = func.__doc__
                result.tags = func_tags
            elif isinstance(result, list):
                # Handle list of results
                for r in result:
                    r.title = func.__name__
                    r.description = func.__doc__
                    r.tags = func_tags
            return result

        # Store tags on the function for potential filtering
        wrapped.tags = set(tags) if tags else set()

        # Register tags globally for discovery
        if tags:
            _REGISTERED_TAGS.update(tags)

        return wrapped

    # Handle both @checker and @checker("tag1", "tag2")
    if len(tags) == 1 and callable(tags[0]):
        func = tags[0]
        tags = ()
        return decorator(func)
    return decorator
