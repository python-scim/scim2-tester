scim2-tester
============

scim2-tester checks that a SCIM server complies with :rfc:`RFC7643 <7643>` and :rfc:`RFC7644 <7644>`.
It reads the discovery endpoints of the server, then creates, reads, replaces, patches and deletes
resources of each resource type, and returns a result for each check.
It runs in the test suite of a SCIM server, in a CI job, or in a health check.
The ``test`` command of :doc:`scim2-cli <scim2_cli:index>` runs the same checks from the command line.

.. code-block:: python

    from httpx2 import Client
    from scim2_client.engines.httpx2 import SyncSCIMClient
    from scim2_tester import iter_check_server

    client = SyncSCIMClient(Client(base_url="https://auth.example/scim/v2"))
    for result in iter_check_server(client):
        print(result.status.name, result.id)

.. code-block:: shell

   pip install scim2-tester[httpx2]

.. warning::

    The checks create, modify and delete resources on the server.
    Run them against a test server, not against production data.

Choose a path
-------------

:doc:`Overview <overview>` shows how to run the checks and read their results.

:doc:`How-to guides <how-to/index>` show how to complete a specific task, such as running the checks
in the test suite of a server, or expecting the failures of a server that does not comply yet.

:doc:`Reference <reference>` lists the complete public API.

.. toctree::
    :maxdepth: 2
    :hidden:

    Overview <overview>
    How-to guides <how-to/index>
    Reference <reference>
    Contributing <contributing>
    Changelog <changelog>
