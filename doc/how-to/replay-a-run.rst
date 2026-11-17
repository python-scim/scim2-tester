Replay a run
============

Use this guide to send the same values again, to reproduce a failure.
Read :doc:`check-a-server-in-a-test-suite` first.

Read the seed
-------------

The checks send random values.
When the test of :class:`~scim2_tester.testing.ScimServerContract` fails,
its output prints the seed of these values:

.. code-block:: console

    scim2-tester seed: 2826105314

Set the seed
------------

Set :attr:`~scim2_tester.testing.ScimServerContract.seed` to send the same values again:

.. code-block:: python

    class TestMyServer(ScimServerContract):
        seed = 2826105314

:func:`~scim2_tester.check_server` takes the same value in its
:paramref:`~scim2_tester.check_server.seed` parameter.
