# scim2-tester

Python methods based on [scim2-models](https://scim2-models.readthedocs.io) and [scim2-client](https://scim2-client.readthedocs.io/en), to check if SCIM servers respect the [RFC7643](https://datatracker.ietf.org/doc/html/rfc7643.html) and [RFC7644](https://datatracker.ietf.org/doc/html/rfc7644.html) specifications.

It aims to be used in unit test and Continuous Integration suites and in healthcheck tools.
If you are seeking a CLI integration of scim2-tester, take a look at [scim2-cli](https://scim2-cli.readthedocs.io).

## What's SCIM anyway?

SCIM stands for System for Cross-domain Identity Management, and it is a provisioning protocol.
Provisioning is the action of managing a set of resources across different services, usually users and groups.
SCIM is often used between Identity Providers and applications in completion of standards like OAuth2 and OpenID Connect.
It allows users and groups creations, modifications and deletions to be synchronized between applications.

## Features

- **Discovery Validation**: Tests `/ServiceProviderConfig`, `/ResourceTypes` and `/Schemas` endpoints
- **CRUD Testing**: Validates `create`, `read`, `update` and `delete` operations on all available resource types
- **PATCH Testing**: Tests `add`, `remove` and `replace` operations on all available simple, complex and extension attributes
- **RFC Compliance**: Checks adherence to [RFC7643](https://datatracker.ietf.org/doc/html/rfc7643) and [RFC7644](https://datatracker.ietf.org/doc/html/rfc7644) specifications
- **Structured Results**: `CheckResult` objects with status, description and debugging data
- **Tag-Based Filtering**: Run specific test categories (`discovery`, `crud`, `patch`, etc.)

## Installation

```shell
pip install scim2-tester
```

## Usage

Check the [tutorial](https://scim2-tester.readthedocs.io/en/latest/tutorial.html) and the [reference](https://scim2-tester.readthedocs.io/en/latest/reference.html) for more details.

scim2-tester belongs in a collection of SCIM tools developed by [Yaal Coop](https://yaal.coop),
with [scim2-models](https://github.com/python-scim/scim2-models),
[scim2-client](https://github.com/python-scim/scim2-client) and
[scim2-cli](https://github.com/python-scim/scim2-cli)
