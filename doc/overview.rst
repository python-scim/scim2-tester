Overview
========

scim2-tester checks that a **System for Cross-domain Identity Management** (**SCIM**) server
complies with the :rfc:`SCIM data model <7643>` and :rfc:`SCIM protocol <7644>` specifications.
It sends the requests with a :doc:`scim2-client <scim2_client:index>` engine.

This page shows how to run the checks from Python code and how to read their results.
It assumes a SCIM server is available.
The :doc:`how-to guides <how-to/index>` cover focused tasks,
and the :doc:`reference` lists the complete API.

.. tip::

    The ``test`` command of :doc:`scim2-cli <scim2_cli:index>` runs the same checks
    from the command line:

    .. code-block:: console

        $ pip install scim2-cli
        $ scim2 --url https://auth.example/scim/v2 test

    The :ref:`scim2-cli test command reference <scim2_cli:reference:test>` lists its options.

Run the checks
--------------

Install scim2-tester with the engine it will use:

.. code-block:: shell

   pip install scim2-tester[httpx2]

Pass a scim2-client engine to :func:`~scim2_tester.iter_check_server`.
It yields each result as soon as its check ends, so a long run can display its progress:

.. code-block:: python

    from httpx2 import Client
    from scim2_client.engines.httpx2 import SyncSCIMClient
    from scim2_tester import iter_check_server

    httpx_client = Client(
        base_url="https://auth.example/scim/v2",
        headers={"Authorization": "Bearer foobar"},
    )
    scim_client = SyncSCIMClient(httpx_client)
    for result in iter_check_server(scim_client):
        print(result.status.name, result.id)

:func:`~scim2_tester.check_server` takes the same parameters, and returns all the results at once.

.. warning::

    The checks create, modify and delete resources on the server.
    Run them against a test server, not against production data.

Some checks list all the resources of a type.
On a server with many resources, they can take a while.

Read the results
----------------

Each :class:`~scim2_tester.CheckResult` holds:

- :attr:`~scim2_tester.CheckResult.status`: how the server behaved, such as
  :attr:`~scim2_tester.Status.SUCCESS`, :attr:`~scim2_tester.Status.DEVIATION`
  or :attr:`~scim2_tester.Status.ERROR`;
- :attr:`~scim2_tester.CheckResult.id`: the identifier of the result, such as
  ``check_add_attribute[User][name.givenName]``;
- :attr:`~scim2_tester.CheckResult.title`, :attr:`~scim2_tester.CheckResult.resource_type`
  and :attr:`~scim2_tester.CheckResult.attribute`: the check, and what it was run on;
- :attr:`~scim2_tester.CheckResult.reason` and :attr:`~scim2_tester.CheckResult.data`:
  why the check failed, and the response that made it fail.

Decide whether the server passes
--------------------------------

The :attr:`~scim2_tester.Status.outcome` of a status tells whether the result passes, warns,
fails or is skipped:

.. list-table::
   :header-rows: 1

   * - Outcome
     - Statuses
   * - :attr:`~scim2_tester.Outcome.PASSED`
     - ``SUCCESS``, ``COMPLIANT``, ``ACCEPTABLE``
   * - :attr:`~scim2_tester.Outcome.WARNING`
     - ``DEVIATION``
   * - :attr:`~scim2_tester.Outcome.FAILED`
     - ``ERROR``, ``CRITICAL``
   * - :attr:`~scim2_tester.Outcome.SKIPPED`
     - ``SKIPPED``

Collect the failures:

.. code-block:: python

    from scim2_tester import Outcome
    from scim2_tester import check_server

    results = check_server(scim_client)
    failed = [r for r in results if r.status.outcome is Outcome.FAILED]

To run the checks in the test suite of a server, follow :doc:`how-to/check-a-server-in-a-test-suite`.
