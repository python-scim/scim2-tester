Tutorial
--------

Basic CLI
=========

scim2-tester is integrated in :doc:`scim2-cli <scim2_cli:index>`:

.. code-block:: console

    pip install scim2-cli
    scim https://scim.example test

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
