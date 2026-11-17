Check a server in its test suite
================================

Use this guide to run the checks of scim2-tester in the pytest suite of a Python SCIM server.
Read the :doc:`../overview` first.
:doc:`filter-the-checks` covers the selection of the checks,
and :doc:`expect-known-failures` covers a server that does not comply yet.

Install the testing extra
-------------------------

:class:`~scim2_tester.testing.ScimServerContract` runs the checks as a pytest test.
It needs the ``testing`` extra, which installs pytest:

.. code-block:: console

    $ pip install scim2-tester[testing]

Write the test
--------------

Subclass :class:`~scim2_tester.testing.ScimServerContract`, and give it a ``scim_client`` fixture.
With the :class:`~scim2_client.engines.wsgi.WSGISCIMClient` engine, no HTTP request is sent:
the server code runs directly.
This engine only needs the standard library, and works with any WSGI framework.

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

Read the report
---------------

The test runs the checks once, and reports each result as a subtest:

- successful, compliant and acceptable results pass;
- skipped results are skipped;
- errors and critical results fail;
- deviations pass with a :class:`~scim2_tester.testing.ScimDeviationWarning`.

Run pytest with ``-v`` to see each subtest.

Fail on the deviations
----------------------

To make the deviations fail, turn the warning into an error:

.. code-block:: toml

    [tool.pytest.ini_options]
    filterwarnings = ["error::scim2_tester.testing.ScimDeviationWarning"]

Select the checks
-----------------

The class attributes select the checks, as the parameters of :func:`~scim2_tester.check_server` do:

.. code-block:: python

    class TestMyServer(ScimServerContract):
        include_tags = {"crud", "patch"}
        exclude_tags = {"patch:remove"}
        resource_types = ["User", "Group"]

:doc:`filter-the-checks` lists the tags.
