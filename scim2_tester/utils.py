import functools
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from enum import auto
from typing import Any

from scim2_client import SCIMClient
from scim2_client import SCIMClientError
from scim2_models import Required
from scim2_models import Resource

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
    """Configuration for check behavior."""

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


class CheckContext:
    """Execution context with client, config and resource management."""

    def __init__(self, client: SCIMClient, conf: CheckConfig):
        self.client = client
        self.conf = conf
        from scim2_tester.utils import ResourceManager

        self.resource_manager = ResourceManager(self)


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


class ResourceManager:
    """Manages SCIM resources with automatic cleanup for tests."""

    def __init__(self, context: CheckContext):
        self.context = context
        self.resources: list[Resource] = []

    def create_and_register(self, model: type[Resource]) -> Resource:
        """Create an object and automatically register it for cleanup.

        :param model: The Resource model class to create
        :returns: The created Resource instance
        """
        from scim2_tester.filling import fill_with_random_values

        field_names = [
            field_name
            for field_name in model.model_fields
            if model.get_field_annotation(field_name, Required) == Required.true
        ]
        obj = fill_with_random_values(self.context, model(), self, field_names)

        # Should not happen since we're filling required fields, but handle just in case
        if obj is None:
            raise ValueError(
                f"Could not create valid {model.__name__} object with required fields"
            )

        created = self.context.client.create(obj)

        self.resources.append(created)

        return created

    def register(self, resource: Resource):
        """Manually register a resource for cleanup.

        :param resource: The Resource instance to register for cleanup
        """
        self.resources.append(resource)

    def register_dependencies(self, dependencies: list[Resource]):
        """Register multiple dependencies for cleanup.

        :param dependencies: List of Resource instances to register for cleanup
        """
        self.resources.extend(dependencies)

    def cleanup(self):
        """Clean up all registered resources in reverse order."""
        for resource in reversed(self.resources):
            try:
                self.context.client.delete(resource.__class__, resource.id)
            except Exception:
                # Best effort cleanup - ignore failures
                pass


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
        def wrapped(context: CheckContext, *args, **kwargs):
            func_tags = set(tags) if tags else set()

            # Check if function should be skipped based on tag filtering
            if context.conf.include_tags and not _matches_hierarchical_tags(
                func_tags, context.conf.include_tags
            ):
                return CheckResult(
                    context.conf,
                    status=Status.SKIPPED,
                    title=func.__name__,
                    description=func.__doc__,
                    tags=func_tags,
                    reason="Skipped due to tag filtering",
                )

            if context.conf.exclude_tags and _matches_hierarchical_tags(
                func_tags, context.conf.exclude_tags
            ):
                return CheckResult(
                    context.conf,
                    status=Status.SKIPPED,
                    title=func.__name__,
                    description=func.__doc__,
                    tags=func_tags,
                    reason="Skipped due to tag exclusion",
                )

            try:
                result = func(context, *args, **kwargs)

            except SCIMClientError as exc:
                if context.conf.raise_exceptions:
                    raise

                reason = f"{exc} {exc.__cause__}" if exc.__cause__ else str(exc)
                result = CheckResult(
                    context.conf, status=Status.ERROR, reason=reason, data=exc.source
                )

            except Exception as exc:
                if context.conf.raise_exceptions:
                    raise

                result = CheckResult(
                    context.conf, status=Status.ERROR, reason=str(exc), data=exc
                )

            finally:
                context.resource_manager.cleanup()

            if isinstance(result, CheckResult):
                result.title = func.__name__
                result.description = func.__doc__
                result.tags = func_tags

            elif isinstance(result, list):
                for r in result:
                    r.title = func.__name__
                    r.description = func.__doc__
                    r.tags = func_tags
            return result

        wrapped.tags = set(tags) if tags else set()

        if tags:
            _REGISTERED_TAGS.update(tags)

        return wrapped

    # Handle both @checker and @checker("tag1", "tag2")
    if len(tags) == 1 and callable(tags[0]):
        func = tags[0]
        tags = ()
        return decorator(func)
    return decorator
