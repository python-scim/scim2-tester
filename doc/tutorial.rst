Tutorial
--------

Basic CLI
=========

scim2-tester is integrated in :doc:`scim2-cli <scim2_cli:index>`:

.. code-block:: console

    pip install scim2-cli
    export SCIM_CLI_URL="https://auth.example"
    scim test

You can check the :ref:`scim2-cli test command reference <scim2_cli:reference:test>` for more details.

Code integration
================

.. warning::

    The checks create, modify and delete resources on the server.
    Never run them against a production server.

.. note::

    Some checks list all the resources of a type, which can be slow on a server with many resources.

If you need to integrate the tester in your code, you can initialize a :doc:`scim2-client engine <scim2_client:reference/engines>`
and pass it to the :meth:`~scim2_tester.check_server` method:

.. code-block:: python

    from httpx2 import Client
    from scim2_client.engines.httpx2 import SyncSCIMClient
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

If you build a Python SCIM server application, you can run the checks of `scim2-tester` in its test suite.
With the scim2-client :class:`~scim2_client.engines.wsgi.WSGISCIMClient` engine, no real HTTP request is made: the server code runs directly.
This engine only needs the standard library, and works with any WSGI framework.

pytest suite
~~~~~~~~~~~~

:class:`~scim2_tester.testing.ScimServerContract` runs the checks as a pytest test.
It needs the ``testing`` extra, which installs pytest:

.. code-block:: console

    pip install scim2-tester[testing]

Subclass it in your tests, and give it a ``scim_client`` fixture:

.. code-block:: python

    import pytest
    from scim2_client.engines.wsgi import WSGISCIMClient
    from scim2_tester.testing import ScimServerContract
    from myapp import create_app


    class TestMyServer(ScimServerContract):
        @pytest.fixture
        def scim_client(self):
            app = create_app(...)
            return WSGISCIMClient(app, base_url="http://localhost/scim/v2")

The test runs the checks once, and reports each result as a subtest.
Successful, compliant and acceptable results pass.
Skipped results are skipped.
Errors and critical results fail.
Run pytest with ``-v`` to see each subtest.

Deviations pass with a :class:`~scim2_tester.testing.ScimDeviationWarning`.
To make them fail, turn the warning into an error:

.. code-block:: toml

    [tool.pytest.ini_options]
    filterwarnings = ["error::scim2_tester.testing.ScimDeviationWarning"]

The class attributes select the checks, as the parameters of :func:`~scim2_tester.check_server` do:

.. code-block:: python

    class TestMyServer(ScimServerContract):
        include_tags = {"crud", "patch"}
        exclude_tags = {"patch:remove"}
        resource_types = ["User", "Group"]

Known failures
~~~~~~~~~~~~~~

When you check a server you do not maintain, some checks may fail until the server is fixed.
List them in :attr:`~scim2_tester.testing.ScimServerContract.expected_results`, with their status and a reason.
The reason is free text, printed in the report, such as a ticket URL or an explanation:

.. code-block:: python

    from scim2_tester import Status


    class TestThirdPartyServer(ScimServerContract):
        expected_results = {
            ("User", "check_add_attribute", "nickName"): (
                Status.ERROR,
                "https://github.com/example/scim-server/issues/123",
            ),
            (None, "schemas_endpoint_methods", None): (
                Status.DEVIATION,
                "The server answers 404 to unknown methods",
            ),
        }

The key of a result is its resource type, its title and its attribute.
A result with the expected status is reported as an expected failure.
A result with another status fails, including a result that now passes: remove it from the list.
An expected result that the checks no longer return also fails the test.
A key applies to all the results that have it.
When these results have different statuses and one of them fails, the key cannot be expected, and the test fails.

When the test fails, its output prints the current failures in the format of ``expected_results``.
Copy them into your test class, and replace each ``TODO`` with a reason.

Replaying a run
~~~~~~~~~~~~~~~

The checks send random values.
When the test fails, its output prints the seed of these values:

.. code-block:: console

    scim2-tester seed: 2826105314

Set :attr:`~scim2_tester.testing.ScimServerContract.seed` to send the same values again:

.. code-block:: python

    class TestMyServer(ScimServerContract):
        seed = 2826105314

Debugging a check
~~~~~~~~~~~~~~~~~

With :paramref:`~scim2_tester.check_server.raise_exceptions`, :func:`~scim2_tester.check_server` raises the first error instead of returning it.
The traceback leads to the server code that failed:

.. code-block:: python

    from scim2_client.engines.wsgi import WSGISCIMClient
    from scim2_tester import check_server
    from myapp import create_app

    def test_scim_tester():
        app = create_app(...)
        client = WSGISCIMClient(app, base_url="http://localhost/scim/v2")
        check_server(client, raise_exceptions=True)
