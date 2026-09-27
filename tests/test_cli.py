"""Test CLI functionality."""

import sys
from unittest.mock import patch

import pytest

from scim2_tester import CheckResult
from scim2_tester import Status
from scim2_tester.cli import cli

HOSTILE_SEQUENCES = [
    pytest.param("\x1b[1A\x1b[2K", "\\x1b[1A\\x1b[2K", id="csi"),
    pytest.param("\x1b]0;title\x1b\\", "\\x1b]0;title\\x1b\\", id="osc"),
    pytest.param("\x9b31m", "\\x9b31m", id="c1-csi"),
    pytest.param("\r", "\\r", id="carriage-return"),
    pytest.param("\x7f", "\\x7f", id="delete"),
    pytest.param("\u202e", "\\u202e", id="bidi-override"),
    pytest.param("\u2066", "\\u2066", id="bidi-isolate"),
]


def test_cli_function_help(capsys):
    """Validates CLI help output contains all expected options."""
    with patch.object(sys, "argv", ["scim2_tester", "--help"]):
        with pytest.raises(SystemExit):
            cli()

    captured = capsys.readouterr()
    assert "SCIM server compliance checker" in captured.out
    assert "--token" in captured.out
    assert "--verbose" in captured.out
    assert "--include-tags" in captured.out
    assert "--exclude-tags" in captured.out
    assert "--resource-types" in captured.out


def serve_empty_discovery(httpserver):
    for endpoint in ("/ResourceTypes", "/Schemas"):
        httpserver.expect_request(endpoint).respond_with_json(
            {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
                "totalResults": 0,
                "Resources": [],
            }
        )
    httpserver.expect_request("/ServiceProviderConfig").respond_with_json(
        {"schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"]}
    )


@pytest.mark.parametrize("field", ["title", "resource_type", "reason", "data"])
@pytest.mark.parametrize(("sequence", "escaped"), HOSTILE_SEQUENCES)
def test_cli_escapes_control_characters_sent_by_the_server(
    httpserver, capsys, monkeypatch, field, sequence, escaped
):
    """The server cannot rewrite the report on the terminal with escape sequences."""
    serve_empty_discovery(httpserver)
    result = CheckResult(
        status=Status.ERROR,
        title="object_creation",
        reason="Creation failed",
        data="payload",
        resource_type="User",
    )
    setattr(result, field, f"{getattr(result, field)}{sequence}")
    monkeypatch.setattr(
        "scim2_tester.cli.check_server", lambda *args, **kwargs: [result]
    )

    with patch.object(
        sys, "argv", ["scim2_tester", httpserver.url_for("/"), "--verbose"]
    ):
        cli()

    output = capsys.readouterr().out
    assert escaped in output
    assert sequence not in output


def test_cli_keeps_line_breaks_and_tabulations(httpserver, capsys, monkeypatch):
    """Line breaks and tabulations are the layout of the messages, not escape sequences."""
    serve_empty_discovery(httpserver)
    result = CheckResult(status=Status.ERROR, title="check", reason="first\n\tsecond")
    monkeypatch.setattr(
        "scim2_tester.cli.check_server", lambda *args, **kwargs: [result]
    )

    with patch.object(sys, "argv", ["scim2_tester", httpserver.url_for("/")]):
        cli()

    assert "first\n\tsecond" in capsys.readouterr().out


def test_cli_full_execution(httpserver, capsys):
    """Ensures full CLI execution with all parameters works correctly."""
    httpserver.expect_request("/ResourceTypes").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": 0,
            "Resources": [],
        }
    )
    httpserver.expect_request("/Schemas").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": 0,
            "Resources": [],
        }
    )
    httpserver.expect_request("/ServiceProviderConfig").respond_with_json(
        {"schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"]}
    )

    with patch.object(
        sys,
        "argv",
        [
            "scim2_tester",
            httpserver.url_for("/"),
            "--token",
            "test-token",
            "--verbose",
            "--include-tags",
            "discovery",
        ],
    ):
        cli()

    captured = capsys.readouterr()
    assert captured.out
    assert "SUCCESS" in captured.out or "ERROR" in captured.out


def test_cli_without_token(httpserver, capsys):
    """Ensures client creation without authentication headers when no token provided."""
    httpserver.expect_request("/ResourceTypes").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": 0,
            "Resources": [],
        }
    )
    httpserver.expect_request("/Schemas").respond_with_json(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": 0,
            "Resources": [],
        }
    )
    httpserver.expect_request("/ServiceProviderConfig").respond_with_json(
        {"schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"]}
    )

    with patch.object(sys, "argv", ["scim2_tester", httpserver.url_for("/")]):
        cli()

    captured = capsys.readouterr()
    assert captured.out
    assert "SUCCESS" in captured.out or "ERROR" in captured.out


def test_cli_verbose_output(scim2_server, capsys):
    """Verifies verbose mode displays additional data in output."""
    server_url = f"http://localhost:{scim2_server.port}"

    with patch.object(
        sys,
        "argv",
        ["scim2_tester", server_url, "--include-tags", "discovery", "crud:read"],
    ):
        cli()

    captured_normal = capsys.readouterr()

    with patch.object(
        sys,
        "argv",
        [
            "scim2_tester",
            server_url,
            "--verbose",
            "--include-tags",
            "discovery",
            "crud:read",
        ],
    ):
        cli()

    captured_verbose = capsys.readouterr()

    assert len(captured_verbose.out) > len(captured_normal.out)
