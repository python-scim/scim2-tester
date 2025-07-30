"""Test CLI functionality."""

import sys
from unittest.mock import patch

import pytest

from scim2_tester.cli import cli


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
