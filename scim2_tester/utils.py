import functools
import sys
import types
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from enum import auto
from typing import Any

from scim2_client import SCIMClientError
from scim2_client.engines.httpx import SyncSCIMClient
from scim2_models import BaseModel
from scim2_models import Mutability
from scim2_models import Required
from scim2_models import Resource

# Global registry for all tags discovered by checker decorators
_REGISTERED_TAGS: set[str] = set()


def get_registered_tags() -> set[str]:
    """Get all tags that have been registered by checker decorators.

    :returns: Set of all registered tags.
    """
    return _REGISTERED_TAGS.copy()


def _matches_hierarchical_tags(func_tags: set[str], filter_tags: set[str]) -> bool:
    """Check if function tags match filter tags using hierarchical logic.

    Supports patterns like:
    - "crud" matches "crud:read", "crud:create", etc.
    - "crud:read" matches exactly "crud:read"
    - "*" matches any function with tags (always executed)

    :param func_tags: Tags on the function
    :param filter_tags: Tags to filter by
    :returns: True if there's a match
    """
    if "*" in func_tags:
        return True

    for filter_tag in filter_tags:
        for func_tag in func_tags:
            if filter_tag == func_tag:
                return True
            if ":" in func_tag and filter_tag in func_tag.split(":"):
                return True

    return False


class Status(Enum):
    SUCCESS = auto()
    """Server behavior strictly conforms to RFC requirements (MUST/MUST NOT)."""

    COMPLIANT = auto()
    """Server behavior follows RFC recommendations (SHOULD/SHOULD NOT) correctly."""

    ACCEPTABLE = auto()
    """Server behavior is RFC-compliant but uses optional features (MAY)
    or applies robustness principle reasonably."""

    DEVIATION = auto()
    """Server behavior deviates from RFC recommendations (SHOULD/SHOULD NOT)
    but remains within specification bounds."""

    ERROR = auto()
    """Server behavior violates mandatory RFC requirements (MUST/MUST NOT)."""

    CRITICAL = auto()
    """Server behavior creates security risks or fundamental protocol violations."""

    SKIPPED = auto()
    """Check was not executed due to filtering or prerequisites."""


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

    resource_manager: "ResourceManager"

    def __init__(self, client: SyncSCIMClient, conf: CheckConfig):
        self.client = client
        self.conf = conf
        # ResourceManager is defined later in the file, so we instantiate it here
        self.resource_manager = ResourceManager(self)  # type: ignore[name-defined]


class SCIMTesterError(Exception):
    """Exception raised when a check failed and the `raise_exceptions` config parameter is :data:`True`."""

    def __init__(self, message: str, conf: CheckConfig):
        super().__init__()
        self.message = message
        self.conf = conf

    def __str__(self) -> str:
        return self.message


def raise_on_caller(exc: Exception) -> None:
    """Raise exception appearing from caller's frame."""
    frame = sys._getframe(2)
    tb = types.TracebackType(
        tb_next=None,
        tb_frame=frame,
        tb_lasti=frame.f_lasti,
        tb_lineno=frame.f_lineno,
    )
    raise exc.with_traceback(tb)


@dataclass
class CheckResult:
    """Store a check result."""

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

    def __repr__(self):
        """Return string representation without verbose description field."""
        parts = [f"CheckResult(status={self.status!r}"]
        if self.title:
            parts.append(f"title={self.title!r}")
        if self.reason:
            parts.append(f"reason={self.reason!r}")
        if self.data is not None:
            parts.append(f"data={self.data!r}")
        if self.tags:
            parts.append(f"tags={self.tags!r}")
        if self.resource_type:
            parts.append(f"resource_type={self.resource_type!r}")
        return ", ".join(parts) + ")"


def check_result(
    context: CheckContext,
    status: Status,
    title: str | None = None,
    description: str | None = None,
    reason: str | None = None,
    data: Any | None = None,
    tags: set[str] | None = None,
    resource_type: str | None = None,
) -> CheckResult:
    """Create a CheckResult that raises SCIMTesterError immediately if configured.

    This factory function creates a CheckResult and immediately raises a
    SCIMTesterError if raise_exceptions is True and the status is ERROR or CRITICAL.
    This ensures the exception is raised at the exact location where the check fails.

    :param context: The check context containing configuration
    :param status: The status of the check result
    :param title: Optional title of the check
    :param description: Optional description of what the check does
    :param reason: Optional reason for the result
    :param data: Optional related data for debugging
    :param tags: Optional tags for filtering
    :param resource_type: Optional resource type name
    :returns: The created CheckResult
    :raises SCIMTesterError: If raise_exceptions is True and status is ERROR or CRITICAL
    """
    if context.conf.raise_exceptions and status in (Status.ERROR, Status.CRITICAL):
        exc = SCIMTesterError(reason or "Check failed", context.conf)
        raise_on_caller(exc)

    return CheckResult(
        status=status,
        title=title,
        description=description,
        reason=reason,
        data=data,
        tags=tags or set(),
        resource_type=resource_type,
    )


class ResourceManager:
    """Manages SCIM resources with automatic cleanup for tests."""

    def __init__(self, context: CheckContext):
        self.context = context
        self.resources: list[Resource[Any]] = []

    def create_and_register(
        self, model: type[Resource[Any]], fill_all: bool = False
    ) -> Resource[Any]:
        """Create an object and automatically register it for cleanup.

        :param model: The Resource model class to create
        :param fill_all: If True, fill all writable attributes (excluding read-only).
                         If False, fill only required attributes (default behavior).
        :returns: The created Resource instance
        """
        # Import here to avoid circular imports
        from scim2_tester.filling import fill_with_random_values

        obj = model()

        if fill_all:
            obj = fill_with_random_values(
                self.context,
                obj,
                mutability=[
                    Mutability.read_write,
                    Mutability.write_only,
                    Mutability.immutable,
                ],
            )
        else:
            obj = fill_with_random_values(self.context, obj, required=[Required.true])
        created = self.context.client.create(obj)

        # Handle the case where create might return Error or dict
        if isinstance(created, Resource):
            self.resources.append(created)
            return created
        else:
            # This shouldn't happen with valid inputs, but handle for type safety
            raise ValueError(f"Failed to create resource: {created}")

    def cleanup(self) -> None:
        """Clean up all registered resources in reverse order."""
        for resource in reversed(self.resources):
            try:
                if resource.id is not None:
                    self.context.client.delete(resource.__class__, resource.id)
            except Exception:
                # Best effort cleanup - ignore failures
                pass


def checker(*tags: str) -> Any:
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

    def decorator(func: Any) -> Any:
        @functools.wraps(func)
        def wrapped(context: CheckContext, *args: Any, **kwargs: Any) -> Any:
            func_tags = set(tags) if tags else set()

            if context.conf.include_tags and not _matches_hierarchical_tags(
                func_tags, context.conf.include_tags
            ):
                return [
                    CheckResult(
                        status=Status.SKIPPED,
                        title=func.__name__,
                        description=func.__doc__,
                        tags=func_tags,
                        reason="Skipped due to tag filtering",
                    )
                ]

            if context.conf.exclude_tags and _matches_hierarchical_tags(
                func_tags, context.conf.exclude_tags
            ):
                return [
                    CheckResult(
                        status=Status.SKIPPED,
                        title=func.__name__,
                        description=func.__doc__,
                        tags=func_tags,
                        reason="Skipped due to tag exclusion",
                    )
                ]

            try:
                result = func(context, *args, **kwargs)

            except SCIMClientError as exc:
                if context.conf.raise_exceptions:
                    raise

                reason = f"{exc} {exc.__cause__}" if exc.__cause__ else str(exc)
                result = [
                    CheckResult(status=Status.ERROR, reason=reason, data=exc.source)
                ]

            except Exception as exc:
                if context.conf.raise_exceptions:
                    raise

                result = [CheckResult(status=Status.ERROR, reason=str(exc), data=exc)]

            finally:
                context.resource_manager.cleanup()

            # All checkers now return list[CheckResult]
            for r in result:
                r.title = func.__name__
                r.description = func.__doc__
                r.tags = func_tags
            return result

        wrapped.tags = set(tags) if tags else set()  # type: ignore[attr-defined]

        if tags:
            _REGISTERED_TAGS.update(tags)

        return wrapped

    # Handle both @checker and @checker("tag1", "tag2")
    if len(tags) == 1 and callable(tags[0]):
        func = tags[0]
        tags = ()
        return decorator(func)
    return decorator


def compare_field(expected: Any, actual: Any) -> bool:
    if expected is None or actual is None:
        return False

    expected = expected.model_dump() if isinstance(expected, BaseModel) else expected
    actual = actual.model_dump() if isinstance(actual, BaseModel) else actual

    return expected == actual
