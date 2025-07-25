import functools
from dataclasses import dataclass
from enum import Enum
from enum import auto
from typing import Any

from scim2_client import SCIMClient
from scim2_client import SCIMClientError


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

    def __post_init__(self):
        if self.conf.raise_exceptions and self.status == Status.ERROR:
            raise SCIMTesterError(self.reason, self)


def should_test_patch(conf: CheckConfig) -> bool:
    """Check if PATCH operations should be tested based on ServiceProviderConfig.

    :param conf: The check configuration containing the SCIM client
    :returns: True if PATCH is supported by the server, False otherwise
    """
    return (
        conf.client.service_provider_config is not None
        and conf.client.service_provider_config.patch is not None
        and conf.client.service_provider_config.patch.supported
    )


def checker(func):
    """Decorate checker methods.

    - It adds a title and a description to the returned result, extracted from the method name and its docstring.
    - It catches SCIMClient errors.
    """

    @functools.wraps(func)
    def wrapped(conf: CheckConfig, *args, **kwargs):
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
        else:
            result[0].title = func.__name__
            result[0].description = func.__doc__
        return result

    return wrapped
