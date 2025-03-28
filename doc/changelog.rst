Changelog
=========

[0.1.14] - 2025-03-28
---------------------

Fixed
^^^^^
- Fix a Pydantic warning.

[0.1.13] - 2024-12-11
---------------------

Fixed
^^^^^
- Generate valid emails and phone numbers when filling objects attributes.

[0.1.12] - 2024-12-08
---------------------

Fixed
^^^^^
- Resource replacement test was not using new values.

[0.1.11] - 2024-12-08
---------------------

Added
^^^^^
- Slightly improved error messages.
- Create temporary resources to test references.

[0.1.10] - 2024-12-02
---------------------

Added
^^^^^
- Restrict expected status codes in checks.
- Check individual :class:`~scim2_models.Schema` and :class:`~scim2_models.ResourceType` endpoints.
- Check for :class:`~scim2_models.Schema` and :class:`~scim2_models.ResourceType` with invalid ids.

Fixed
^^^^^
- Avoid to randomly generate references to unexisting objects.

[0.1.9] - 2024-11-29
--------------------

Added
^^^^^
- Added support for :class:`Extensions <scim2_models.Extension>`.

[0.1.8] - 2024-11-29
--------------------

Added
^^^^^
- Implement a :paramref:`~scim2_tester.check_server.raise_exceptions` parameter that allows failed checks to raise exceptions.

[0.1.7] - 2024-11-29
--------------------

Added
^^^^^
- Support with `scim2-client` 0.3.0.

[0.1.6] - 2024-11-28
--------------------

Added
^^^^^
- Python 3.13 support.

[0.1.5] - 2024-09-01
--------------------

Fixed
^^^^^
- check_random_url error after scim2-client 0.2.0 update. :issue:`8`

[0.1.4] - 2024-09-01
--------------------

Fixed
^^^^^
- Do not raise exceptions when encountering SCIM errors. :issue:`3`
- Invalid domains and network errors are properly handled. :issue:`6`

[0.1.3] - 2024-07-25
--------------------

Fixed
^^^^^
- Bug with the new :class:`~scim2_models.Reference` attribute type.

[0.1.2] - 2024-06-05
--------------------

Fixed
^^^^^
- Import exception.

[0.1.1] - 2024-06-05
--------------------

Added
^^^^^
- Basic checks: :class:`~scim2_models.ServiceProviderConfig`,
  :class:`~scim2_models.Schema` and :class:`~scim2_models.ResourceType` retrieval and
  creation, query, replacement and deletion operations on :class:`~scim2_models.User`
  and :class:`~scim2_models.Group`.

[0.1.0] - 2024-06-03
--------------------

Added
^^^^^
- Initial release
