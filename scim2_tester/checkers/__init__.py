"""SCIM server compliance checkers.

This module contains all the individual checkers for validating SCIM server implementations.
Each checker is decorated with tags that allow selective test execution.

Available checker categories:

- discovery: ServiceProviderConfig, ResourceTypes, Schemas endpoints
- crud: Create, Read, Update, Delete operations
- misc: Random URL access tests
"""

from .misc import random_url
from .resource import resource_type_tests
from .resource_delete import object_deletion
from .resource_get import object_query
from .resource_get import object_query_without_id
from .resource_post import object_creation
from .resource_put import object_replacement
from .resource_types import access_invalid_resource_type
from .resource_types import query_all_resource_types
from .resource_types import query_resource_type_by_id
from .resource_types import resource_types_endpoint_methods
from .resource_types import resource_types_schema_validation
from .schemas import access_invalid_schema
from .schemas import access_schema_by_id
from .schemas import core_schemas_validation
from .schemas import query_all_schemas
from .schemas import schemas_endpoint_methods
from .service_provider_config import service_provider_config_endpoint
from .service_provider_config import service_provider_config_endpoint_methods

__all__ = [
    "service_provider_config_endpoint",
    "service_provider_config_endpoint_methods",
    "resource_types_endpoint_methods",
    "resource_types_schema_validation",
    "query_all_resource_types",
    "query_resource_type_by_id",
    "access_invalid_resource_type",
    "schemas_endpoint_methods",
    "query_all_schemas",
    "access_schema_by_id",
    "access_invalid_schema",
    "core_schemas_validation",
    "object_creation",
    "object_query",
    "object_query_without_id",
    "object_replacement",
    "object_deletion",
    "resource_type_tests",
    "random_url",
]
