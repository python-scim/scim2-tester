Filter the checks
=================

Use this guide to run a subset of the checks, for instance while developing a feature of a server.
Read the :doc:`../overview` first.
The same filters apply to the class attributes of :class:`~scim2_tester.testing.ScimServerContract`,
as :doc:`check-a-server-in-a-test-suite` shows.

Select the checks by tag
------------------------

Each check has tags.
Pass the tags to run to :paramref:`~scim2_tester.check_server.include_tags`,
and the tags to skip to :paramref:`~scim2_tester.check_server.exclude_tags`:

.. code-block:: python

    from scim2_tester import check_server

    # Run only the discovery checks
    results = check_server(client, include_tags={"discovery"})

    # Run the CRUD checks, except the deletion ones
    results = check_server(client, include_tags={"crud"}, exclude_tags={"crud:delete"})

The tags are:

- ``discovery``: the checks of the discovery endpoints;
- ``service-provider-config``: the checks of :class:`~scim2_models.ServiceProviderConfig`;
- ``resource-types``: the checks of :class:`~scim2_models.ResourceType`;
- ``schemas``: the checks of :class:`~scim2_models.Schema`;
- ``crud``: all the CRUD checks;
- ``crud:create``, ``crud:read``, ``crud:update``, ``crud:delete``: the CRUD checks of each operation;
- ``crud:read:attributes``: the checks of the ``attributes`` and ``excludedAttributes`` parameters;
- ``patch``: all the PATCH checks;
- ``patch:add``, ``patch:replace``, ``patch:remove``: the PATCH checks of each operation;
- ``misc``: the other checks.

A tag selects the tags under it: ``crud`` selects ``crud:create`` and ``crud:read:attributes``,
and ``crud:read`` selects ``crud:read:attributes``.
:func:`~scim2_tester.get_all_available_tags` lists all the tags.
An unknown tag raises a :class:`ValueError`.

The other checks need the discovery endpoints, so the discovery checks query them regardless of the tags.
When the tags do not select them, their successes are reported as skipped.
Their failures are still reported, as the other checks cannot run without them.

Select the resource types
-------------------------

Pass the names of the resource types to check to :paramref:`~scim2_tester.check_server.resource_types`:

.. code-block:: python

    results = check_server(client, resource_types=["User"])

Combine the filters
-------------------

The filters apply together:

.. code-block:: python

    # Check only the creation and the reading of users
    results = check_server(
        client,
        include_tags={"crud:create", "crud:read"},
        resource_types=["User"],
    )
