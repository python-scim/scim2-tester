Expect the known failures
=========================

Use this guide to check a server that does not comply yet, such as a server maintained by a third party.
The test passes while the known failures stay the same, and fails when they change.
Read :doc:`check-a-server-in-a-test-suite` first.

List the expected results
-------------------------

List the known failures in :attr:`~scim2_tester.testing.ScimServerContract.expected_results`,
with their status.
A status can come with a reason.
The reason is free text, printed in the report, such as a ticket URL or an explanation:

.. code-block:: python

    from scim2_tester import Status
    from scim2_tester.testing import ScimServerContract


    class TestThirdPartyServer(ScimServerContract):
        expected_results = {
            ("User", "check_add_attribute", "nickName"): (
                Status.ERROR,
                "https://github.com/example/scim-server/issues/123",
            ),
            (None, "schemas_endpoint_methods", None): Status.DEVIATION,
        }

The key of a result is its resource type, its title and its attribute.

Copy the current failures
-------------------------

When the test fails, its output prints the current failures in the format of ``expected_results``.
Copy them into the test class, and add a reason where it helps.

Read the outcome
----------------

- A result with the expected status is reported as an expected failure.
- A result with another status fails, including a result that now passes: remove it from the list.
- An expected result that the checks no longer return fails the test.
- A key applies to all the results that have it.
  When these results have different statuses and one of them fails, the key cannot be expected,
  and the test fails.
