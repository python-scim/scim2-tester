"""Tests of the grading of the requests a server should reject."""

import pytest
from scim2_client import UnexpectedStatusCodeException
from scim2_models import Error

from scim2_tester.checkers._rejection_utils import rejection_status
from scim2_tester.utils import Status


@pytest.mark.parametrize(
    ("response", "status", "reason"),
    [
        (
            Error(status=400, scim_type="invalidValue"),
            Status.SUCCESS,
            "the server answered 400 invalidValue",
        ),
        (
            Error(status=400),
            Status.ACCEPTABLE,
            "the server answered 400 without a scimType",
        ),
        (
            Error(status=400, scim_type="mutability"),
            Status.DEVIATION,
            "the server answered 400 mutability instead of invalidValue",
        ),
        (
            Error(status=422),
            Status.DEVIATION,
            "the server answered 422 instead of 400",
        ),
        (Error(status=500), Status.ERROR, "the server answered 500"),
        (Error(), Status.ERROR, "the server answered None"),
        (
            UnexpectedStatusCodeException(400),
            Status.DEVIATION,
            "the server answered 400 without a SCIM error",
        ),
        (
            UnexpectedStatusCodeException(502),
            Status.ERROR,
            "the server answered 502 without a SCIM error",
        ),
        ({"id": "123"}, Status.ERROR, "the server accepted the request"),
        (None, Status.ERROR, "the server accepted the request"),
    ],
)
def test_rejection_status(response, status, reason):
    """A server answering a request it should reject is graded on its status and scimType."""
    assert rejection_status(response, "invalidValue", Status.ACCEPTABLE) == (
        status,
        reason,
    )


def test_rejection_status_without_scim_type_takes_the_given_status():
    """A 400 without scimType gets the status the check gives it."""
    status, _ = rejection_status(Error(status=400), "mutability", Status.DEVIATION)
    assert status == Status.DEVIATION
