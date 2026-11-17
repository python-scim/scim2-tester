Debug a failed check
====================

Use this guide to find the server code that makes a check fail.
Read :doc:`check-a-server-in-a-test-suite` first.

Let the exceptions through
--------------------------

When a check fails on an exception raised by the server code, the failed subtest shows its traceback.
The server must let its exceptions through.
For instance, a Flask application does it in testing mode only.

Stop on the first error
-----------------------

With :paramref:`~scim2_tester.check_server.raise_exceptions`,
:func:`~scim2_tester.check_server` raises the first error instead of returning it.
The traceback leads to the server code that failed:

.. code-block:: python

    from scim2_client.engines.wsgi import WSGISCIMClient
    from scim2_tester import check_server
    from myapp import create_app


    def test_scim_tester():
        app = create_app(...)
        client = WSGISCIMClient(app, base_url="http://localhost/scim/v2")
        check_server(client, raise_exceptions=True)
