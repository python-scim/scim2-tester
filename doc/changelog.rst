Changelog
=========

[0.1.6] - Unreleased
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
