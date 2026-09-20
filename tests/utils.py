"""Test utilities for SCIM compliance testing."""

from typing import Any

try:
    from httpx2 import Client
except ImportError:
    from httpx import Client

from scim2_models.utils import _to_camel

__all__ = ["Client", "build_nested_response"]


def build_nested_response(base_response: dict, path: str, value: Any) -> dict:
    """Build a SCIM response with value at the correct nested path."""
    write_only_attributes = {"password"}
    if path in write_only_attributes:
        return base_response

    response = base_response.copy()

    if path.startswith("urn:"):
        known_extension_urns = {
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        }

        if path in known_extension_urns:
            response[path] = value
        else:
            namespace, field_name = path.rsplit(":", 1)
            if namespace not in response or not isinstance(response[namespace], dict):
                response[namespace] = {}
            response[namespace][field_name] = value

    else:
        response[_to_camel(path)] = value

    return response
