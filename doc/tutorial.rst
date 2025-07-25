Tutorial
--------

Basic CLI
=========

scim2-tester is integrated in :doc:`scim2-cli <scim2_cli:index>`:

.. code-block:: console

    pip install scim2-cli
    export SCIM_CLI_URL="https://auth.example"
    scim test

You can check the :ref:`scim2-cli test command reference <scim2_cli:test>` for more details.

Code integration
================

If you need to integrate the tester in your code, you can initialize a :ref:`scim2-client engine <scim2_client:engines>`
and pass it to the :meth:`~scim2_tester.check_server` method:

.. code-block:: python

    from httpx import Client
    from scim2_client.engines.httpx import SyncSCIMClient
    from scim2_tester import check_server

    httpx_client = Client(
        base_url="https://auth.example/scim/v2",
        headers={"Authorization": "Bearer foobar"},
    )
    scim_client = SyncSCIMClient(httpx_client)
    results = check_server(scim_client)
    for result in results:
        print(result.status.name, result.title)


scim2-tester supports filtering tests using tags and resource types to run only specific subsets of checks.
This is useful for targeted testing or when developing specific features.

Tag-based filtering
~~~~~~~~~~~~~~~~~~~

Tests are organized using hierarchical tags that allow fine-grained control over which checks to execute. Use the :paramref:`~scim2_tester.check_server.include_tags` and :paramref:`~scim2_tester.check_server.exclude_tags` parameters:

.. code-block:: python

    from scim2_tester import check_server

    # Run only discovery tests
    results = check_server(client, include_tags={"discovery"})

    # Run all CRUD operations except delete
    results = check_server(
        client,
        include_tags={"crud"},
        exclude_tags={"crud:delete"}
    )

    # Run only resource creation tests
    results = check_server(client, include_tags={"crud:create"})

Available tags include:

- **discovery**: Configuration endpoint tests (:class:`~scim2_models.ServiceProviderConfig`, :class:`~scim2_models.ResourceType`, :class:`~scim2_models.Schema`)
- **service-provider-config**: :class:`~scim2_models.ServiceProviderConfig` endpoint tests
- **resource-types**: :class:`~scim2_models.ResourceType` endpoint tests
- **schemas**: :class:`~scim2_models.Schema` endpoint tests
- **crud**: All CRUD operation tests
- **crud:create**: Resource creation tests
- **crud:read**: Resource reading tests
- **crud:update**: Resource update tests
- **crud:delete**: Resource deletion tests
- **misc**: Miscellaneous tests

The tag system is hierarchical, so ``crud`` will match ``crud:create``, ``crud:read``, etc.

Resource type filtering
~~~~~~~~~~~~~~~~~~~~~~~

You can also filter tests by resource type using the :paramref:`~scim2_tester.check_server.resource_types` parameter:

.. code-block:: python

    # Test only User resources
    results = check_server(client, resource_types=["User"])

    # Test both User and Group resources
    results = check_server(client, resource_types=["User", "Group"])

Combining filters
~~~~~~~~~~~~~~~~~

Filters can be combined for precise control using both :paramref:`~scim2_tester.check_server.include_tags` and :paramref:`~scim2_tester.check_server.resource_types` parameters:

.. code-block:: python

    # Test only User creation and reading
    results = check_server(
        client,
        include_tags={"crud:create", "crud:read"},
        resource_types=["User"]
    )

Unit test suite integration
===========================

If you build a Python SCIM sever application and need a complete test suite to check you implementation, you can integrate `scim2-tester` in your test suite with little effort.
Thanks to scim2-client :class:`~scim2_client.engines.werkzeug.TestSCIMClient` engine, no real HTTP request is made, but the server code is directly executed.
In combination with :paramref:`~scim2_tester.check_server.raise_exceptions`, this allows you to catch server exceptions in the test contexts, which is very handy for development.

As :class:`~scim2_client.engines.werkzeug.TestSCIMClient` relies on :doc:`Werkzeug <werkzeug:index>`, you need to check that you have installed the right dependencies to use it:

.. code-block:: console

   uv add --group dev scim2-models[werkzeug]

.. code-block:: python

    from scim2_client.engines.werkzeug import TestSCIMClient
    from scim2_tester import check_server
    from werkzeug.test import Client
    from myapp import create_app

    def test_scim_tester():
        app = create_app(...)
        testclient = Client(app)
        client = TestSCIMClient(app=testclient, scim_prefix="/scim/v2")
        check_server(client, raise_exceptions=True)

Parametrized testing
~~~~~~~~~~~~~~~~~~~~

For comprehensive test coverage, you can create parametrized tests that exercise different combinations of tags and resource types using :func:`~scim2_tester.discovery.get_all_available_tags` and :func:`~scim2_tester.discovery.get_standard_resource_types`:

.. code-block:: python

    import pytest
    from scim2_tester import Status, check_server
    from scim2_tester.discovery import get_all_available_tags, get_standard_resource_types

    @pytest.mark.parametrize("tag", get_all_available_tags())
    @pytest.mark.parametrize("resource_type", [None] + get_standard_resource_types())
    def test_individual_filters(scim_client, tag, resource_type):
        results = check_server(
            scim_client,
            raise_exceptions=False,
            include_tags={tag},
            resource_types=resource_type
        )

        for result in results:
            assert result.status in (Status.SKIPPED, Status.SUCCESS)

This parametrized approach automatically discovers all available tags and resource types, ensuring that your test suite covers all possible combinations as your SCIM implementation evolves. Each test verifies that results have either :attr:`~scim2_tester.Status.SUCCESS` or :attr:`~scim2_tester.Status.SKIPPED` status.
