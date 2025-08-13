from typing import Any
from typing import Literal

from pydantic import EmailStr
from scim2_models import Address
from scim2_models import Email
from scim2_models import EnterpriseUser
from scim2_models import Entitlement
from scim2_models import ExternalReference
from scim2_models import GroupMembership
from scim2_models import Im
from scim2_models import Manager
from scim2_models import Mutability
from scim2_models import Name
from scim2_models import PhoneNumber
from scim2_models import Photo
from scim2_models import Reference
from scim2_models import Required
from scim2_models import Role
from scim2_models import User
from scim2_models import X509Certificate
from scim2_models.utils import Base64Bytes

from scim2_tester.urns import get_annotation_by_urn
from scim2_tester.urns import get_attribute_type_by_urn
from scim2_tester.urns import get_multiplicity_by_urn
from scim2_tester.urns import get_target_model_by_urn
from scim2_tester.urns import get_value_by_urn
from scim2_tester.urns import iter_all_urns
from scim2_tester.urns import iter_urns
from scim2_tester.urns import set_value_by_urn


def test_iter_urns_resource():
    urns = list(iter_urns(User))
    assert "externalId" in urns
    assert "userName" in urns
    assert "name" in urns
    assert "name.formatted" in urns
    assert "name.familyName" in urns
    assert "name.givenName" in urns
    assert "name.middleName" in urns
    assert "name.honorificPrefix" in urns
    assert "name.honorificSuffix" in urns
    assert "displayName" in urns
    assert "nickName" in urns
    assert "profileUrl" in urns
    assert "title" in urns
    assert "userType" in urns
    assert "preferredLanguage" in urns
    assert "locale" in urns
    assert "timezone" in urns
    assert "active" in urns
    assert "password" in urns
    assert "emails" in urns
    assert "emails.type" in urns
    assert "emails.primary" in urns
    assert "emails.display" in urns
    assert "emails.value" in urns
    assert "emails.ref" in urns
    assert "phoneNumbers" in urns
    assert "phoneNumbers.type" in urns
    assert "phoneNumbers.primary" in urns
    assert "phoneNumbers.display" in urns
    assert "phoneNumbers.value" in urns
    assert "phoneNumbers.ref" in urns
    assert "ims" in urns
    assert "ims.type" in urns
    assert "ims.primary" in urns
    assert "ims.display" in urns
    assert "ims.value" in urns
    assert "ims.ref" in urns
    assert "photos" in urns
    assert "photos.type" in urns
    assert "photos.primary" in urns
    assert "photos.display" in urns
    assert "photos.value" in urns
    assert "photos.ref" in urns
    assert "addresses" in urns
    assert "addresses.type" in urns
    assert "addresses.primary" in urns
    assert "addresses.display" in urns
    # TODO: this should not exist
    assert "addresses.value" in urns
    assert "addresses.ref" in urns
    assert "addresses.formatted" in urns
    assert "addresses.streetAddress" in urns
    assert "addresses.locality" in urns
    assert "addresses.region" in urns
    assert "addresses.postalCode" in urns
    assert "addresses.country" in urns
    assert "groups" in urns
    assert "groups.type" in urns
    assert "groups.primary" in urns
    assert "groups.display" in urns
    assert "groups.value" in urns
    assert "groups.ref" in urns
    assert "entitlements" in urns
    assert "entitlements.type" in urns
    assert "entitlements.primary" in urns
    assert "entitlements.display" in urns
    # TODO: this should be str ?
    assert "entitlements.value" in urns
    assert "entitlements.ref" in urns
    assert "roles" in urns
    assert "roles.type" in urns
    assert "roles.primary" in urns
    assert "roles.display" in urns
    # TODO: this should be str?
    assert "roles.value" in urns
    assert "roles.ref" in urns
    assert "x509Certificates" in urns
    assert "x509Certificates.type" in urns
    assert "x509Certificates.primary" in urns
    assert "x509Certificates.display" in urns
    assert "x509Certificates.value" in urns
    assert "x509Certificates.ref" in urns


def test_iter_urns_extension():
    urns = list(iter_urns(EnterpriseUser))
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:costCenter"
    ) in urns
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:department"
    ) in urns
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:division"
    ) in urns
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
    ) in urns
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager"
    ) in urns
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName"
    ) in urns
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.ref"
    ) in urns
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.value"
    ) in urns
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:organization"
    ) in urns


def test_iter_all_urns():
    urns = list(iter_all_urns(User[EnterpriseUser]))
    assert ("externalId", User[EnterpriseUser]) in urns
    assert ("userName", User[EnterpriseUser]) in urns
    assert ("name", User[EnterpriseUser]) in urns
    assert ("name.formatted", User[EnterpriseUser]) in urns
    assert ("name.familyName", User[EnterpriseUser]) in urns
    assert ("name.givenName", User[EnterpriseUser]) in urns
    assert ("name.middleName", User[EnterpriseUser]) in urns
    assert ("name.honorificPrefix", User[EnterpriseUser]) in urns
    assert ("name.honorificSuffix", User[EnterpriseUser]) in urns
    assert ("displayName", User[EnterpriseUser]) in urns
    assert ("nickName", User[EnterpriseUser]) in urns
    assert ("profileUrl", User[EnterpriseUser]) in urns
    assert ("title", User[EnterpriseUser]) in urns
    assert ("userType", User[EnterpriseUser]) in urns
    assert ("preferredLanguage", User[EnterpriseUser]) in urns
    assert ("locale", User[EnterpriseUser]) in urns
    assert ("timezone", User[EnterpriseUser]) in urns
    assert ("active", User[EnterpriseUser]) in urns
    assert ("password", User[EnterpriseUser]) in urns
    assert ("emails", User[EnterpriseUser]) in urns
    assert ("emails.type", User[EnterpriseUser]) in urns
    assert ("emails.primary", User[EnterpriseUser]) in urns
    assert ("emails.display", User[EnterpriseUser]) in urns
    assert ("emails.value", User[EnterpriseUser]) in urns
    assert ("emails.ref", User[EnterpriseUser]) in urns
    assert ("phoneNumbers", User[EnterpriseUser]) in urns
    assert ("phoneNumbers.type", User[EnterpriseUser]) in urns
    assert ("phoneNumbers.primary", User[EnterpriseUser]) in urns
    assert ("phoneNumbers.display", User[EnterpriseUser]) in urns
    assert ("phoneNumbers.value", User[EnterpriseUser]) in urns
    assert ("phoneNumbers.ref", User[EnterpriseUser]) in urns
    assert ("ims", User[EnterpriseUser]) in urns
    assert ("ims.type", User[EnterpriseUser]) in urns
    assert ("ims.primary", User[EnterpriseUser]) in urns
    assert ("ims.display", User[EnterpriseUser]) in urns
    assert ("ims.value", User[EnterpriseUser]) in urns
    assert ("ims.ref", User[EnterpriseUser]) in urns
    assert ("photos", User[EnterpriseUser]) in urns
    assert ("photos.type", User[EnterpriseUser]) in urns
    assert ("photos.primary", User[EnterpriseUser]) in urns
    assert ("photos.display", User[EnterpriseUser]) in urns
    assert ("photos.value", User[EnterpriseUser]) in urns
    assert ("photos.ref", User[EnterpriseUser]) in urns
    assert ("addresses", User[EnterpriseUser]) in urns
    assert ("addresses.type", User[EnterpriseUser]) in urns
    assert ("addresses.primary", User[EnterpriseUser]) in urns
    assert ("addresses.display", User[EnterpriseUser]) in urns
    # TODO: this should not exist
    assert ("addresses.value", User[EnterpriseUser]) in urns
    assert ("addresses.ref", User[EnterpriseUser]) in urns
    assert ("addresses.formatted", User[EnterpriseUser]) in urns
    assert ("addresses.streetAddress", User[EnterpriseUser]) in urns
    assert ("addresses.locality", User[EnterpriseUser]) in urns
    assert ("addresses.region", User[EnterpriseUser]) in urns
    assert ("addresses.postalCode", User[EnterpriseUser]) in urns
    assert ("addresses.country", User[EnterpriseUser]) in urns
    assert ("groups", User[EnterpriseUser]) in urns
    assert ("groups.type", User[EnterpriseUser]) in urns
    assert ("groups.primary", User[EnterpriseUser]) in urns
    assert ("groups.display", User[EnterpriseUser]) in urns
    assert ("groups.value", User[EnterpriseUser]) in urns
    assert ("groups.ref", User[EnterpriseUser]) in urns
    assert ("entitlements", User[EnterpriseUser]) in urns
    assert ("entitlements.type", User[EnterpriseUser]) in urns
    assert ("entitlements.primary", User[EnterpriseUser]) in urns
    assert ("entitlements.display", User[EnterpriseUser]) in urns
    # TODO: this should be str ?
    assert ("entitlements.value", User[EnterpriseUser]) in urns
    assert ("entitlements.ref", User[EnterpriseUser]) in urns
    assert ("roles", User[EnterpriseUser]) in urns
    assert ("roles.type", User[EnterpriseUser]) in urns
    assert ("roles.primary", User[EnterpriseUser]) in urns
    assert ("roles.display", User[EnterpriseUser]) in urns
    # TODO: this should be str?
    assert ("roles.value", User[EnterpriseUser]) in urns
    assert ("roles.ref", User[EnterpriseUser]) in urns
    assert ("x509Certificates", User[EnterpriseUser]) in urns
    assert ("x509Certificates.type", User[EnterpriseUser]) in urns
    assert ("x509Certificates.primary", User[EnterpriseUser]) in urns
    assert ("x509Certificates.display", User[EnterpriseUser]) in urns
    assert ("x509Certificates.value", User[EnterpriseUser]) in urns
    assert ("x509Certificates.ref", User[EnterpriseUser]) in urns
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:costCenter",
        EnterpriseUser,
    ) in urns
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:department",
        EnterpriseUser,
    ) in urns
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:division",
        EnterpriseUser,
    ) in urns
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber",
        EnterpriseUser,
    ) in urns
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager",
        EnterpriseUser,
    ) in urns
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName",
        EnterpriseUser,
    ) in urns
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.ref",
        EnterpriseUser,
    ) in urns
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.value",
        EnterpriseUser,
    ) in urns
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:organization",
        EnterpriseUser,
    ) in urns


def test_get_target_model_by_urn():
    urns = iter_all_urns(User[EnterpriseUser])
    annotations = {urn: get_target_model_by_urn(model, urn) for urn, model in urns}
    assert annotations == {
        "active": (
            User[EnterpriseUser],
            "active",
        ),
        "addresses": (
            User[EnterpriseUser],
            "addresses",
        ),
        "addresses.country": (
            Address,
            "country",
        ),
        "addresses.display": (
            Address,
            "display",
        ),
        "addresses.formatted": (
            Address,
            "formatted",
        ),
        "addresses.locality": (
            Address,
            "locality",
        ),
        "addresses.postalCode": (
            Address,
            "postal_code",
        ),
        "addresses.primary": (
            Address,
            "primary",
        ),
        "addresses.ref": (
            Address,
            "ref",
        ),
        "addresses.region": (
            Address,
            "region",
        ),
        "addresses.streetAddress": (
            Address,
            "street_address",
        ),
        "addresses.type": (
            Address,
            "type",
        ),
        "addresses.value": (
            Address,
            "value",
        ),
        "displayName": (
            User[EnterpriseUser],
            "display_name",
        ),
        "emails": (
            User[EnterpriseUser],
            "emails",
        ),
        "emails.display": (
            Email,
            "display",
        ),
        "emails.primary": (
            Email,
            "primary",
        ),
        "emails.ref": (
            Email,
            "ref",
        ),
        "emails.type": (
            Email,
            "type",
        ),
        "emails.value": (
            Email,
            "value",
        ),
        "entitlements": (
            User[EnterpriseUser],
            "entitlements",
        ),
        "entitlements.display": (
            Entitlement,
            "display",
        ),
        "entitlements.primary": (
            Entitlement,
            "primary",
        ),
        "entitlements.ref": (
            Entitlement,
            "ref",
        ),
        "entitlements.type": (
            Entitlement,
            "type",
        ),
        "entitlements.value": (
            Entitlement,
            "value",
        ),
        "externalId": (
            User[EnterpriseUser],
            "external_id",
        ),
        "groups": (
            User[EnterpriseUser],
            "groups",
        ),
        "groups.display": (
            GroupMembership,
            "display",
        ),
        "groups.primary": (
            GroupMembership,
            "primary",
        ),
        "groups.ref": (
            GroupMembership,
            "ref",
        ),
        "groups.type": (
            GroupMembership,
            "type",
        ),
        "groups.value": (
            GroupMembership,
            "value",
        ),
        "ims": (
            User[EnterpriseUser],
            "ims",
        ),
        "ims.display": (
            Im,
            "display",
        ),
        "ims.primary": (
            Im,
            "primary",
        ),
        "ims.ref": (
            Im,
            "ref",
        ),
        "ims.type": (
            Im,
            "type",
        ),
        "ims.value": (
            Im,
            "value",
        ),
        "locale": (
            User[EnterpriseUser],
            "locale",
        ),
        "name": (
            User[EnterpriseUser],
            "name",
        ),
        "name.familyName": (
            Name,
            "family_name",
        ),
        "name.formatted": (
            Name,
            "formatted",
        ),
        "name.givenName": (
            Name,
            "given_name",
        ),
        "name.honorificPrefix": (
            Name,
            "honorific_prefix",
        ),
        "name.honorificSuffix": (
            Name,
            "honorific_suffix",
        ),
        "name.middleName": (
            Name,
            "middle_name",
        ),
        "nickName": (
            User[EnterpriseUser],
            "nick_name",
        ),
        "password": (
            User[EnterpriseUser],
            "password",
        ),
        "phoneNumbers": (
            User[EnterpriseUser],
            "phone_numbers",
        ),
        "phoneNumbers.display": (
            PhoneNumber,
            "display",
        ),
        "phoneNumbers.primary": (
            PhoneNumber,
            "primary",
        ),
        "phoneNumbers.ref": (
            PhoneNumber,
            "ref",
        ),
        "phoneNumbers.type": (
            PhoneNumber,
            "type",
        ),
        "phoneNumbers.value": (
            PhoneNumber,
            "value",
        ),
        "photos": (
            User[EnterpriseUser],
            "photos",
        ),
        "photos.display": (
            Photo,
            "display",
        ),
        "photos.primary": (
            Photo,
            "primary",
        ),
        "photos.ref": (
            Photo,
            "ref",
        ),
        "photos.type": (
            Photo,
            "type",
        ),
        "photos.value": (
            Photo,
            "value",
        ),
        "preferredLanguage": (
            User[EnterpriseUser],
            "preferred_language",
        ),
        "profileUrl": (
            User[EnterpriseUser],
            "profile_url",
        ),
        "roles": (
            User[EnterpriseUser],
            "roles",
        ),
        "roles.display": (
            Role,
            "display",
        ),
        "roles.primary": (
            Role,
            "primary",
        ),
        "roles.ref": (
            Role,
            "ref",
        ),
        "roles.type": (
            Role,
            "type",
        ),
        "roles.value": (
            Role,
            "value",
        ),
        "timezone": (
            User[EnterpriseUser],
            "timezone",
        ),
        "title": (
            User[EnterpriseUser],
            "title",
        ),
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": (
            User[EnterpriseUser],
            "EnterpriseUser",
        ),
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:costCenter": (
            EnterpriseUser,
            "cost_center",
        ),
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:department": (
            EnterpriseUser,
            "department",
        ),
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:division": (
            EnterpriseUser,
            "division",
        ),
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber": (
            EnterpriseUser,
            "employee_number",
        ),
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager": (
            EnterpriseUser,
            "manager",
        ),
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName": (
            Manager,
            "display_name",
        ),
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.ref": (
            Manager,
            "ref",
        ),
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.value": (
            Manager,
            "value",
        ),
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:organization": (
            EnterpriseUser,
            "organization",
        ),
        "userName": (
            User[EnterpriseUser],
            "user_name",
        ),
        "userType": (
            User[EnterpriseUser],
            "user_type",
        ),
        "x509Certificates": (
            User[EnterpriseUser],
            "x509_certificates",
        ),
        "x509Certificates.display": (
            X509Certificate,
            "display",
        ),
        "x509Certificates.primary": (
            X509Certificate,
            "primary",
        ),
        "x509Certificates.ref": (
            X509Certificate,
            "ref",
        ),
        "x509Certificates.type": (
            X509Certificate,
            "type",
        ),
        "x509Certificates.value": (
            X509Certificate,
            "value",
        ),
    }


def test_get_attribute_type_by_urn():
    urns = iter_all_urns(User[EnterpriseUser])
    types = {urn: get_attribute_type_by_urn(model, urn) for urn, model in urns}
    assert types == {
        "active": bool,
        "addresses": Address,
        "addresses.country": str,
        "addresses.display": str,
        "addresses.formatted": str,
        "addresses.locality": str,
        "addresses.postalCode": str,
        "addresses.primary": bool,
        "addresses.ref": Reference[Any],
        "addresses.region": str,
        "addresses.streetAddress": str,
        "addresses.type": Address.Type,
        "addresses.value": Any,
        "displayName": str,
        "emails": Email,
        "emails.display": str,
        "emails.primary": bool,
        "emails.ref": Reference[Any],
        "emails.type": Email.Type,
        "emails.value": EmailStr,
        "entitlements": Entitlement,
        "entitlements.display": str,
        "entitlements.primary": bool,
        "entitlements.ref": Reference[Any],
        "entitlements.type": str,
        "entitlements.value": Any,
        "externalId": str,
        "groups": GroupMembership,
        "groups.display": str,
        "groups.primary": bool,
        "groups.ref": Reference[Literal["User"] | Literal["Group"]],
        "groups.type": str,
        "groups.value": str,
        "ims": Im,
        "ims.display": str,
        "ims.primary": bool,
        "ims.ref": Reference[Any],
        "ims.type": Im.Type,
        "ims.value": str,
        "locale": str,
        "name": Name,
        "name.familyName": str,
        "name.formatted": str,
        "name.givenName": str,
        "name.honorificPrefix": str,
        "name.honorificSuffix": str,
        "name.middleName": str,
        "nickName": str,
        "password": str,
        "phoneNumbers": PhoneNumber,
        "phoneNumbers.display": str,
        "phoneNumbers.primary": bool,
        "phoneNumbers.ref": Reference[Any],
        "phoneNumbers.type": PhoneNumber.Type,
        "phoneNumbers.value": str,
        "photos": Photo,
        "photos.display": str,
        "photos.primary": bool,
        "photos.ref": Reference[Any],
        "photos.type": Photo.Type,
        "photos.value": Reference[ExternalReference],
        "preferredLanguage": str,
        "profileUrl": Reference[ExternalReference],
        "roles": Role,
        "roles.display": str,
        "roles.primary": bool,
        "roles.ref": Reference[Any],
        "roles.type": str,
        "roles.value": Any,
        "timezone": str,
        "title": str,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": EnterpriseUser,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:costCenter": str,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:department": str,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:division": str,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber": str,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager": Manager,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName": str,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.ref": Reference[
            Literal["User"]
        ],
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.value": str,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:organization": str,
        "userName": str,
        "userType": str,
        "x509Certificates": X509Certificate,
        "x509Certificates.display": str,
        "x509Certificates.primary": bool,
        "x509Certificates.ref": Reference[Any],
        "x509Certificates.type": str,
        "x509Certificates.value": Base64Bytes,
    }


def test_get_annotation_by_urn():
    urns = iter_all_urns(User[EnterpriseUser])
    annotations = {
        urn: get_annotation_by_urn(Mutability, urn, model) for urn, model in urns
    }
    assert annotations == {
        "active": Mutability.read_write,
        "addresses": Mutability.read_write,
        "addresses.country": Mutability.read_write,
        "addresses.display": Mutability.immutable,
        "addresses.formatted": Mutability.read_write,
        "addresses.locality": Mutability.read_write,
        "addresses.postalCode": Mutability.read_write,
        "addresses.primary": Mutability.read_write,
        "addresses.ref": Mutability.read_write,
        "addresses.region": Mutability.read_write,
        "addresses.streetAddress": Mutability.read_write,
        "addresses.type": Mutability.read_write,
        "addresses.value": Mutability.read_write,
        "displayName": Mutability.read_write,
        "emails": Mutability.read_write,
        "emails.display": Mutability.read_write,
        "emails.primary": Mutability.read_write,
        "emails.ref": Mutability.read_write,
        "emails.type": Mutability.read_write,
        "emails.value": Mutability.read_write,
        "entitlements": Mutability.read_write,
        "entitlements.display": Mutability.immutable,
        "entitlements.primary": Mutability.read_write,
        "entitlements.ref": Mutability.read_write,
        "entitlements.type": Mutability.read_write,
        "entitlements.value": Mutability.read_write,
        "externalId": Mutability.read_write,
        "groups": Mutability.read_only,
        "groups.display": Mutability.read_only,
        "groups.primary": Mutability.read_write,
        "groups.ref": Mutability.read_only,
        "groups.type": Mutability.read_only,
        "groups.value": Mutability.read_only,
        "ims": Mutability.read_write,
        "ims.display": Mutability.read_write,
        "ims.primary": Mutability.read_write,
        "ims.ref": Mutability.read_write,
        "ims.type": Mutability.read_write,
        "ims.value": Mutability.read_write,
        "locale": Mutability.read_write,
        "name": Mutability.read_write,
        "name.familyName": Mutability.read_write,
        "name.formatted": Mutability.read_write,
        "name.givenName": Mutability.read_write,
        "name.honorificPrefix": Mutability.read_write,
        "name.honorificSuffix": Mutability.read_write,
        "name.middleName": Mutability.read_write,
        "nickName": Mutability.read_write,
        "password": Mutability.write_only,
        "phoneNumbers": Mutability.read_write,
        "phoneNumbers.display": Mutability.read_write,
        "phoneNumbers.primary": Mutability.read_write,
        "phoneNumbers.ref": Mutability.read_write,
        "phoneNumbers.type": Mutability.read_write,
        "phoneNumbers.value": Mutability.read_write,
        "photos": Mutability.read_write,
        "photos.display": Mutability.read_write,
        "photos.primary": Mutability.read_write,
        "photos.ref": Mutability.read_write,
        "photos.type": Mutability.read_write,
        "photos.value": Mutability.read_write,
        "preferredLanguage": Mutability.read_write,
        "profileUrl": Mutability.read_write,
        "roles": Mutability.read_write,
        "roles.display": Mutability.immutable,
        "roles.primary": Mutability.read_write,
        "roles.ref": Mutability.read_write,
        "roles.type": Mutability.read_write,
        "roles.value": Mutability.read_write,
        "timezone": Mutability.read_write,
        "title": Mutability.read_write,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": Mutability.read_write,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:costCenter": Mutability.read_write,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:department": Mutability.read_write,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:division": Mutability.read_write,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber": Mutability.read_write,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager": Mutability.read_write,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName": Mutability.read_only,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.ref": Mutability.read_write,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.value": Mutability.read_write,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:organization": Mutability.read_write,
        "userName": Mutability.read_write,
        "userType": Mutability.read_write,
        "x509Certificates": Mutability.read_write,
        "x509Certificates.display": Mutability.immutable,
        "x509Certificates.primary": Mutability.read_write,
        "x509Certificates.ref": Mutability.read_write,
        "x509Certificates.type": Mutability.read_write,
        "x509Certificates.value": Mutability.read_write,
    }


def test_get_value_by_urn():
    user = User[EnterpriseUser](
        user_name="john.doe",
        external_id="ext-12345",
        display_name="John Doe",
        nick_name="Johnny",
        profile_url="https://example.com/profiles/john.doe",
        title="Senior Software Engineer",
        user_type="Employee",
        preferred_language="en-US",
        locale="en-US",
        timezone="America/New_York",
        active=True,
        password="SecurePassword123!",
        name=Name(
            formatted="Mr. John William Doe Jr.",
            family_name="Doe",
            given_name="John",
            middle_name="William",
            honorific_prefix="Mr.",
            honorific_suffix="Jr.",
        ),
        emails=[
            Email(
                value="john.doe@example.com",
                type=Email.Type.work,
                primary=True,
                display="Work Email",
            ),
            Email(
                value="johndoe@personal.com",
                type=Email.Type.home,
                primary=False,
                display="Personal Email",
            ),
        ],
        phone_numbers=[
            PhoneNumber(
                value="+1-555-123-4567",
                type=PhoneNumber.Type.work,
                primary=True,
                display="Work Phone",
            ),
            PhoneNumber(
                value="+1-555-987-6543",
                type=PhoneNumber.Type.mobile,
                primary=False,
                display="Mobile Phone",
            ),
        ],
        ims=[
            Im(
                value="john.doe.skype",
                type=Im.Type.skype,
                primary=True,
                display="Skype ID",
            )
        ],
        photos=[
            Photo(
                value="https://example.com/photos/john.jpg",
                type=Photo.Type.photo,
                primary=True,
                display="Profile Photo",
            ),
            Photo(
                value="https://example.com/thumbnails/john.jpg",
                type=Photo.Type.thumbnail,
                primary=False,
                display="Thumbnail",
            ),
        ],
        addresses=[
            Address(
                formatted="123 Main St, Suite 456, San Francisco, CA 94102, USA",
                street_address="123 Main St, Suite 456",
                locality="San Francisco",
                region="CA",
                postal_code="94102",
                country="USA",
                type=Address.Type.work,
                primary=True,
                display="Work Address",
            ),
            Address(
                formatted="789 Oak Ave, New York, NY 10001, USA",
                street_address="789 Oak Ave",
                locality="New York",
                region="NY",
                postal_code="10001",
                country="USA",
                type=Address.Type.home,
                primary=False,
                display="Home Address",
            ),
        ],
        groups=[
            GroupMembership(
                value="group-123",
                ref="https://example.com/Groups/group-123",
                display="Engineering Team",
                type="Team",
            ),
            GroupMembership(
                value="group-456",
                ref="https://example.com/Groups/group-456",
                display="Managers",
                type="Role",
            ),
        ],
        entitlements=[
            Entitlement(
                value="read-write",
                type="access-level",
                primary=True,
                display="Read-Write Access",
            ),
            Entitlement(
                value="admin", type="role", primary=False, display="Admin Role"
            ),
        ],
        roles=[
            Role(
                value="developer",
                type="technical",
                primary=True,
                display="Senior Developer",
            ),
            Role(
                value="team-lead", type="management", primary=False, display="Team Lead"
            ),
        ],
        x509_certificates=[
            X509Certificate(
                value=Base64Bytes(
                    b"MIIDQzCCAqygAwIBAgICEAAwDQYJKoZIhvcNAQEFBQAwTjEL..."
                ),
                type="signing",
                primary=True,
                display="Signing Certificate",
            ),
            X509Certificate(
                value=Base64Bytes(
                    b"MIIDRzCCAqygAwIBAgICEAAwDQYJKoZIhvcNAQEFBQAwTjEL..."
                ),
                type="encryption",
                primary=False,
                display="Encryption Certificate",
            ),
        ],
    )
    user[EnterpriseUser] = EnterpriseUser(
        cost_center="CC-1001",
        department="Engineering",
        division="Product Development",
        employee_number="EMP-98765",
        organization="Acme Corporation",
        manager=Manager(
            value="manager-789",
            ref="https://example.com/Users/manager-789",
            display_name="Jane Smith",
        ),
    )

    # Test simple attributes
    assert get_value_by_urn(user, "userName") == "john.doe"
    assert get_value_by_urn(user, "externalId") == "ext-12345"
    assert get_value_by_urn(user, "displayName") == "John Doe"
    assert get_value_by_urn(user, "nickName") == "Johnny"
    assert (
        get_value_by_urn(user, "profileUrl") == "https://example.com/profiles/john.doe"
    )
    assert get_value_by_urn(user, "title") == "Senior Software Engineer"
    assert get_value_by_urn(user, "userType") == "Employee"
    assert get_value_by_urn(user, "preferredLanguage") == "en-US"
    assert get_value_by_urn(user, "locale") == "en-US"
    assert get_value_by_urn(user, "timezone") == "America/New_York"
    assert get_value_by_urn(user, "active") is True
    assert get_value_by_urn(user, "password") == "SecurePassword123!"

    # Test complex attribute (name)
    assert get_value_by_urn(user, "name").formatted == "Mr. John William Doe Jr."
    assert get_value_by_urn(user, "name.formatted") == "Mr. John William Doe Jr."
    assert get_value_by_urn(user, "name.familyName") == "Doe"
    assert get_value_by_urn(user, "name.givenName") == "John"
    assert get_value_by_urn(user, "name.middleName") == "William"
    assert get_value_by_urn(user, "name.honorificPrefix") == "Mr."
    assert get_value_by_urn(user, "name.honorificSuffix") == "Jr."

    # Test multi-valued attributes (emails) - not possible until filters are supported
    assert get_value_by_urn(user, "emails") == [
        Email(
            type=Email.Type.work,
            primary=True,
            display="Work Email",
            value="john.doe@example.com",
        ),
        Email(
            type=Email.Type.home,
            primary=False,
            display="Personal Email",
            value="johndoe@personal.com",
        ),
    ]
    # assert get_value_by_urn(user, "emails.value") == [
    #    "john.doe@example.com",
    #    "johndoe@personal.com",
    # ]
    # assert get_value_by_urn(user, "emails.type") == [Email.Type.work, Email.Type.home]
    # assert get_value_by_urn(user, "emails.primary") == [True, False]
    # assert get_value_by_urn(user, "emails.display") == ["Work Email", "Personal Email"]

    # Test phone numbers - not possible until filters are supported
    assert get_value_by_urn(user, "phoneNumbers") == [
        PhoneNumber(
            value="+1-555-123-4567",
            type=PhoneNumber.Type.work,
            primary=True,
            display="Work Phone",
        ),
        PhoneNumber(
            value="+1-555-987-6543",
            type=PhoneNumber.Type.mobile,
            primary=False,
            display="Mobile Phone",
        ),
    ]
    # assert get_value_by_urn(user, "phoneNumbers.value") == [
    #    "+1-555-123-4567",
    #    "+1-555-987-6543",
    # ]
    # assert get_value_by_urn(user, "phoneNumbers.type") == [
    #    PhoneNumber.Type.work,
    #    PhoneNumber.Type.mobile,
    # ]
    # assert get_value_by_urn(user, "phoneNumbers.primary") == [True, False]
    # assert get_value_by_urn(user, "phoneNumbers.display") == [
    #    "Work Phone",
    #    "Mobile Phone",
    # ]

    # Test IMs - not possible until filters are supported
    assert get_value_by_urn(user, "ims") == [
        Im(
            value="john.doe.skype",
            type=Im.Type.skype,
            primary=True,
            display="Skype ID",
        )
    ]
    # assert get_value_by_urn(user, "ims.value") == ["john.doe.skype"]
    # assert get_value_by_urn(user, "ims.type") == [Im.Type.skype]
    # assert get_value_by_urn(user, "ims.primary") == [True]
    # assert get_value_by_urn(user, "ims.display") == ["Skype ID"]

    # Test photos - not possible until filters are supported
    assert get_value_by_urn(user, "photos") == [
        Photo(
            value="https://example.com/photos/john.jpg",
            type=Photo.Type.photo,
            primary=True,
            display="Profile Photo",
        ),
        Photo(
            value="https://example.com/thumbnails/john.jpg",
            type=Photo.Type.thumbnail,
            primary=False,
            display="Thumbnail",
        ),
    ]
    # assert get_value_by_urn(user, "photos.value") == [
    #    "https://example.com/photos/john.jpg",
    #    "https://example.com/thumbnails/john.jpg",
    # ]
    # assert get_value_by_urn(user, "photos.type") == [
    #    Photo.Type.photo,
    #    Photo.Type.thumbnail,
    # ]
    # assert get_value_by_urn(user, "photos.primary") == [True, False]
    # assert get_value_by_urn(user, "photos.display") == ["Profile Photo", "Thumbnail"]

    # Test addresses - not possible until filters are supported
    assert get_value_by_urn(user, "addresses") == [
        Address(
            formatted="123 Main St, Suite 456, San Francisco, CA 94102, USA",
            street_address="123 Main St, Suite 456",
            locality="San Francisco",
            region="CA",
            postal_code="94102",
            country="USA",
            type=Address.Type.work,
            primary=True,
            display="Work Address",
        ),
        Address(
            formatted="789 Oak Ave, New York, NY 10001, USA",
            street_address="789 Oak Ave",
            locality="New York",
            region="NY",
            postal_code="10001",
            country="USA",
            type=Address.Type.home,
            primary=False,
            display="Home Address",
        ),
    ]
    # assert get_value_by_urn(user, "addresses.formatted") == [
    #    "123 Main St, Suite 456, San Francisco, CA 94102, USA",
    #    "789 Oak Ave, New York, NY 10001, USA",
    # ]
    # assert get_value_by_urn(user, "addresses.streetAddress") == [
    #    "123 Main St, Suite 456",
    #    "789 Oak Ave",
    # ]
    # assert get_value_by_urn(user, "addresses.locality") == ["San Francisco", "New York"]
    # assert get_value_by_urn(user, "addresses.region") == ["CA", "NY"]
    # assert get_value_by_urn(user, "addresses.postalCode") == ["94102", "10001"]
    # assert get_value_by_urn(user, "addresses.country") == ["USA", "USA"]
    # assert get_value_by_urn(user, "addresses.type") == [
    #    Address.Type.work,
    #    Address.Type.home,
    # ]
    # assert get_value_by_urn(user, "addresses.primary") == [True, False]
    # assert get_value_by_urn(user, "addresses.display") == [
    #    "Work Address",
    #    "Home Address",
    # ]

    # Test groups - not possible until filters are supported
    assert get_value_by_urn(user, "groups") == [
        GroupMembership(
            value="group-123",
            ref="https://example.com/Groups/group-123",
            display="Engineering Team",
            type="Team",
        ),
        GroupMembership(
            value="group-456",
            ref="https://example.com/Groups/group-456",
            display="Managers",
            type="Role",
        ),
    ]
    # assert get_value_by_urn(user, "groups.value") == ["group-123", "group-456"]
    # assert get_value_by_urn(user, "groups.ref") == [
    #    "https://example.com/Groups/group-123",
    #    "https://example.com/Groups/group-456",
    # ]
    # assert get_value_by_urn(user, "groups.display") == ["Engineering Team", "Managers"]
    # assert get_value_by_urn(user, "groups.type") == ["Team", "Role"]

    # Test entitlements - not possible until filters are supported
    assert get_value_by_urn(user, "entitlements") == [
        Entitlement(
            value="read-write",
            type="access-level",
            primary=True,
            display="Read-Write Access",
        ),
        Entitlement(value="admin", type="role", primary=False, display="Admin Role"),
    ]
    # assert get_value_by_urn(user, "entitlements.value") == ["read-write", "admin"]
    # assert get_value_by_urn(user, "entitlements.type") == ["access-level", "role"]
    # assert get_value_by_urn(user, "entitlements.primary") == [True, False]
    # assert get_value_by_urn(user, "entitlements.display") == [
    #    "Read-Write Access",
    #    "Admin Role",
    # ]

    # Test roles - not possible until filters are supported
    assert get_value_by_urn(user, "roles") == [
        Role(
            value="developer",
            type="technical",
            primary=True,
            display="Senior Developer",
        ),
        Role(value="team-lead", type="management", primary=False, display="Team Lead"),
    ]
    # assert get_value_by_urn(user, "roles.value") == ["developer", "team-lead"]
    # assert get_value_by_urn(user, "roles.type") == ["technical", "management"]
    # assert get_value_by_urn(user, "roles.primary") == [True, False]
    # assert get_value_by_urn(user, "roles.display") == ["Senior Developer", "Team Lead"]

    # Test x509Certificates - not possible until filters are supported
    assert get_value_by_urn(user, "x509Certificates") == [
        X509Certificate(
            value=Base64Bytes(b"MIIDQzCCAqygAwIBAgICEAAwDQYJKoZIhvcNAQEFBQAwTjEL..."),
            type="signing",
            primary=True,
            display="Signing Certificate",
        ),
        X509Certificate(
            value=Base64Bytes(b"MIIDRzCCAqygAwIBAgICEAAwDQYJKoZIhvcNAQEFBQAwTjEL..."),
            type="encryption",
            primary=False,
            display="Encryption Certificate",
        ),
    ]
    # assert get_value_by_urn(user, "x509Certificates.type") == ["signing", "encryption"]
    # assert get_value_by_urn(user, "x509Certificates.primary") == [True, False]
    # assert get_value_by_urn(user, "x509Certificates.display") == [
    #    "Signing Certificate",
    #    "Encryption Certificate",
    # ]

    # Test enterprise extension with full URN
    assert (
        get_value_by_urn(
            user, "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
        ).cost_center
        == "CC-1001"
    )
    assert (
        get_value_by_urn(
            user,
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:costCenter",
        )
        == "CC-1001"
    )
    assert (
        get_value_by_urn(
            user,
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:department",
        )
        == "Engineering"
    )
    assert (
        get_value_by_urn(
            user, "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:division"
        )
        == "Product Development"
    )
    assert (
        get_value_by_urn(
            user,
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber",
        )
        == "EMP-98765"
    )
    assert (
        get_value_by_urn(
            user,
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:organization",
        )
        == "Acme Corporation"
    )

    # Test manager sub-attributes
    assert (
        get_value_by_urn(
            user, "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager"
        ).value
        == "manager-789"
    )
    assert (
        get_value_by_urn(
            user,
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.value",
        )
        == "manager-789"
    )
    assert (
        get_value_by_urn(
            user,
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.ref",
        )
        == "https://example.com/Users/manager-789"
    )
    assert (
        get_value_by_urn(
            user,
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName",
        )
        == "Jane Smith"
    )


def test_set_value_by_urn():
    # Create a minimal user object
    user = User[EnterpriseUser](
        user_name="initial.user",
    )

    # Test setting simple attributes
    set_value_by_urn(user, "userName", "updated.user")
    assert user.user_name == "updated.user"

    set_value_by_urn(user, "externalId", "ext-99999")
    assert user.external_id == "ext-99999"

    set_value_by_urn(user, "displayName", "Updated User")
    assert user.display_name == "Updated User"

    set_value_by_urn(user, "nickName", "UpdatedNick")
    assert user.nick_name == "UpdatedNick"

    set_value_by_urn(user, "profileUrl", "https://example.com/updated")
    assert user.profile_url == "https://example.com/updated"

    set_value_by_urn(user, "title", "Updated Title")
    assert user.title == "Updated Title"

    set_value_by_urn(user, "userType", "UpdatedType")
    assert user.user_type == "UpdatedType"

    set_value_by_urn(user, "preferredLanguage", "fr-FR")
    assert user.preferred_language == "fr-FR"

    set_value_by_urn(user, "locale", "fr-FR")
    assert user.locale == "fr-FR"

    set_value_by_urn(user, "timezone", "Europe/Paris")
    assert user.timezone == "Europe/Paris"

    set_value_by_urn(user, "active", False)
    assert user.active is False

    set_value_by_urn(user, "password", "NewPassword456!")
    assert user.password == "NewPassword456!"

    # Test setting complex attribute (name)
    set_value_by_urn(
        user,
        "name",
        Name(formatted="Ms. Jane Smith", family_name="Smith", given_name="Jane"),
    )
    assert user.name.formatted == "Ms. Jane Smith"
    assert user.name.family_name == "Smith"
    assert user.name.given_name == "Jane"

    # Test setting sub-attributes of complex fields
    set_value_by_urn(user, "name.familyName", "Johnson")
    assert user.name.family_name == "Johnson"

    set_value_by_urn(user, "name.givenName", "Emily")
    assert user.name.given_name == "Emily"

    set_value_by_urn(user, "name.middleName", "Marie")
    assert user.name.middle_name == "Marie"

    set_value_by_urn(user, "name.honorificPrefix", "Dr.")
    assert user.name.honorific_prefix == "Dr."

    set_value_by_urn(user, "name.honorificSuffix", "PhD")
    assert user.name.honorific_suffix == "PhD"

    set_value_by_urn(user, "name.formatted", "Dr. Emily Marie Johnson, PhD")
    assert user.name.formatted == "Dr. Emily Marie Johnson, PhD"

    # Test setting multi-valued attributes (emails)
    # Setting a single email should wrap it in a list
    set_value_by_urn(
        user,
        "emails",
        Email(value="new.email@example.com", type=Email.Type.work, primary=True),
    )
    assert len(user.emails) == 1
    assert user.emails[0].value == "new.email@example.com"

    # Test setting multiple emails
    set_value_by_urn(
        user,
        "emails",
        [
            Email(value="work@example.com", type=Email.Type.work, primary=True),
            Email(value="home@example.com", type=Email.Type.home, primary=False),
        ],
    )
    assert len(user.emails) == 2
    assert user.emails[0].value == "work@example.com"
    assert user.emails[1].value == "home@example.com"

    # Test setting phone numbers
    set_value_by_urn(
        user,
        "phoneNumbers",
        PhoneNumber(
            value="+33-1-23-45-67-89", type=PhoneNumber.Type.work, primary=True
        ),
    )
    assert len(user.phone_numbers) == 1
    assert user.phone_numbers[0].value == "+33-1-23-45-67-89"

    # Test setting multiple phone numbers
    set_value_by_urn(
        user,
        "phoneNumbers",
        [
            PhoneNumber(value="+33-1-11-11-11-11", type=PhoneNumber.Type.work),
            PhoneNumber(value="+33-6-22-22-22-22", type=PhoneNumber.Type.mobile),
        ],
    )
    assert len(user.phone_numbers) == 2
    assert user.phone_numbers[0].value == "+33-1-11-11-11-11"
    assert user.phone_numbers[1].value == "+33-6-22-22-22-22"

    # Test setting IMs
    set_value_by_urn(
        user, "ims", Im(value="user.teams", type=Im.Type.skype, primary=True)
    )
    assert len(user.ims) == 1
    assert user.ims[0].value == "user.teams"

    # Test setting photos
    set_value_by_urn(
        user,
        "photos",
        Photo(
            value="https://example.com/new-photo.jpg",
            type=Photo.Type.photo,
            primary=True,
        ),
    )
    assert len(user.photos) == 1
    assert user.photos[0].value == "https://example.com/new-photo.jpg"

    # Test setting addresses
    set_value_by_urn(
        user,
        "addresses",
        Address(
            formatted="456 New Street, Paris, France",
            street_address="456 New Street",
            locality="Paris",
            country="France",
            type=Address.Type.work,
            primary=True,
        ),
    )
    assert len(user.addresses) == 1
    assert user.addresses[0].formatted == "456 New Street, Paris, France"
    assert user.addresses[0].locality == "Paris"

    # Test setting multiple addresses
    set_value_by_urn(
        user,
        "addresses",
        [
            Address(
                street_address="123 Work St",
                locality="Lyon",
                country="France",
                type=Address.Type.work,
            ),
            Address(
                street_address="456 Home Ave",
                locality="Nice",
                country="France",
                type=Address.Type.home,
            ),
        ],
    )
    assert len(user.addresses) == 2
    assert user.addresses[0].locality == "Lyon"
    assert user.addresses[1].locality == "Nice"

    # Test setting entitlements
    set_value_by_urn(
        user,
        "entitlements",
        Entitlement(value="full-access", type="permission", primary=True),
    )
    assert len(user.entitlements) == 1
    assert user.entitlements[0].value == "full-access"

    # Test setting roles
    set_value_by_urn(
        user, "roles", Role(value="manager", type="position", primary=True)
    )
    assert len(user.roles) == 1
    assert user.roles[0].value == "manager"

    # Test setting x509 certificates
    cert_data = "MIIDQzCCAqygAwIBAgICADA="  # Valid base64 string
    set_value_by_urn(
        user,
        "x509Certificates",
        X509Certificate(value=cert_data, type="auth", primary=True),
    )
    assert len(user.x509_certificates) == 1
    assert user.x509_certificates[0].type == "auth"

    # Test setting enterprise extension
    user[EnterpriseUser] = EnterpriseUser()

    # Test setting enterprise attributes with full URN
    set_value_by_urn(
        user,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:costCenter",
        "CC-2002",
    )
    assert user[EnterpriseUser].cost_center == "CC-2002"

    set_value_by_urn(
        user,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:department",
        "Marketing",
    )
    assert user[EnterpriseUser].department == "Marketing"

    set_value_by_urn(
        user,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:division",
        "Sales Division",
    )
    assert user[EnterpriseUser].division == "Sales Division"

    set_value_by_urn(
        user,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber",
        "EMP-11111",
    )
    assert user[EnterpriseUser].employee_number == "EMP-11111"

    set_value_by_urn(
        user,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:organization",
        "NewCorp Inc.",
    )
    assert user[EnterpriseUser].organization == "NewCorp Inc."

    # Test setting manager
    set_value_by_urn(
        user,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager",
        Manager(
            value="manager-999",
            ref="https://example.com/Users/manager-999",
            display_name="Bob Manager",
        ),
    )
    assert user[EnterpriseUser].manager.value == "manager-999"
    assert user[EnterpriseUser].manager.ref == "https://example.com/Users/manager-999"
    assert user[EnterpriseUser].manager.display_name == "Bob Manager"

    # Test setting manager sub-attributes
    set_value_by_urn(
        user,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.value",
        "manager-888",
    )
    assert user[EnterpriseUser].manager.value == "manager-888"

    set_value_by_urn(
        user,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.ref",
        "https://example.com/Users/manager-888",
    )
    assert user[EnterpriseUser].manager.ref == "https://example.com/Users/manager-888"

    # Test setting manager.displayName (even though it's read-only, it should work)
    set_value_by_urn(
        user,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName",
        "Alice Director",
    )
    assert user[EnterpriseUser].manager.display_name == "Alice Director"

    # Test setting entire extension at once
    set_value_by_urn(
        user,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        EnterpriseUser(
            cost_center="CC-3003",
            department="IT",
            division="Tech",
            employee_number="EMP-33333",
            organization="TechCorp",
        ),
    )
    assert user[EnterpriseUser].cost_center == "CC-3003"
    assert user[EnterpriseUser].department == "IT"
    assert user[EnterpriseUser].division == "Tech"
    assert user[EnterpriseUser].employee_number == "EMP-33333"
    assert user[EnterpriseUser].organization == "TechCorp"

    # Test edge cases
    # Test setting None value
    set_value_by_urn(user, "title", None)
    assert user.title is None

    # Test setting empty string
    set_value_by_urn(user, "nickName", "")
    assert user.nick_name == ""

    # Test setting empty list for multi-valued
    set_value_by_urn(user, "emails", [])
    assert user.emails == []

    # Test that read-only fields can now be set (groups is read-only but should work)
    set_value_by_urn(
        user, "groups", [GroupMembership(value="group-999", display="Test Group")]
    )
    # Should now be changed since we no longer filter by mutability
    assert len(user.groups) == 1
    assert user.groups[0].value == "group-999"
    assert user.groups[0].display == "Test Group"


def test_iter_urns_with_required_filter():
    """Test iter_urns with Required filter."""
    required_urns = list(iter_urns(User, required=[Required.true]))
    all_urns = list(iter_urns(User))

    assert len(required_urns) < len(all_urns)
    assert "userName" in required_urns


def test_iter_urns_with_mutability_filter():
    """Test iter_urns with Mutability filter."""
    read_only_urns = list(iter_urns(User, mutability=[Mutability.read_only]))
    all_urns = list(iter_urns(User))

    assert len(read_only_urns) < len(all_urns)


def test_iter_all_urns_with_simple_resource():
    """Test iter_all_urns with a resource that has no extensions."""
    from scim2_models import Group

    urns = list(iter_all_urns(Group))
    assert len(urns) > 0
    assert all(isinstance(urn, tuple) and len(urn) == 2 for urn in urns)


def test_get_multiplicity_by_urn():
    """Test get_multiplicity_by_urn function."""
    # Test single-valued attribute
    assert get_multiplicity_by_urn(User[EnterpriseUser], "userName") is False

    # Test multi-valued attribute
    assert get_multiplicity_by_urn(User[EnterpriseUser], "emails") is True

    # Test sub-attribute of multi-valued
    assert get_multiplicity_by_urn(User[EnterpriseUser], "emails.value") is False

    # Test extension attribute
    assert (
        get_multiplicity_by_urn(
            User[EnterpriseUser],
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:costCenter",
        )
        is False
    )

    # Test non-existent attribute returns None
    result = get_multiplicity_by_urn(User[EnterpriseUser], "nonExistent")
    assert result is None


def test_get_attribute_type_by_urn_error_cases():
    """Test error cases for get_attribute_type_by_urn."""
    # Test non-existent URN
    assert get_attribute_type_by_urn(User, "nonExistent") is None

    # Test malformed URN
    assert get_attribute_type_by_urn(User, "invalid.nonexistent.path") is None


def test_get_annotation_by_urn_error_cases():
    """Test error cases for get_annotation_by_urn."""
    # Test non-existent URN
    assert get_annotation_by_urn(Mutability, "nonExistent", User) is None

    # Test malformed URN
    assert get_annotation_by_urn(Mutability, "invalid.nonexistent.path", User) is None


def test_get_target_model_by_urn_with_extensions():
    """Test get_target_model_by_urn with extension URNs."""
    # Test direct extension schema URN
    result = get_target_model_by_urn(
        User[EnterpriseUser],
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
    )
    assert result == (User[EnterpriseUser], "EnterpriseUser")

    # Test extension attribute URN
    result = get_target_model_by_urn(
        User[EnterpriseUser],
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:costCenter",
    )
    assert result == (EnterpriseUser, "cost_center")


def test_get_value_by_urn_error_cases():
    """Test error cases for get_value_by_urn."""
    user = User(user_name="test")

    # Test non-existent field
    assert get_value_by_urn(user, "nonExistent") is None

    # Test accessing field on None object (name is None)
    assert get_value_by_urn(user, "name.familyName") is None

    # Test malformed path
    assert get_value_by_urn(user, "nonexistent.field") is None

    # Test accessing non-existent sub-field
    user.name = Name(given_name="John")
    assert get_value_by_urn(user, "name.nonExistent") is None


def test_get_value_by_urn_with_extension():
    """Test get_value_by_urn with extension URNs."""
    user = User[EnterpriseUser](user_name="test")
    user[EnterpriseUser] = EnterpriseUser(cost_center="CC-123")

    # Test direct extension access
    extension = get_value_by_urn(
        user, "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )
    assert extension.cost_center == "CC-123"

    # Test extension attribute access
    cost_center = get_value_by_urn(
        user, "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:costCenter"
    )
    assert cost_center == "CC-123"


def test_set_value_by_urn_extension_creation():
    """Test set_value_by_urn creates extension objects when needed."""
    user = User[EnterpriseUser](user_name="test")
    # Extension not set initially
    assert user[EnterpriseUser] is None

    # Setting extension attribute should create extension
    set_value_by_urn(
        user,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:costCenter",
        "CC-456",
    )

    assert user[EnterpriseUser] is not None
    assert user[EnterpriseUser].cost_center == "CC-456"


def test_set_value_by_urn_complex_object_creation():
    """Test set_value_by_urn creates complex objects when needed."""
    user = User(user_name="test")
    # Name is None initially
    assert user.name is None

    # Setting sub-attribute should create Name object
    set_value_by_urn(user, "name.givenName", "John")

    assert user.name is not None
    assert user.name.given_name == "John"


def test_set_value_by_urn_error_cases():
    """Test error cases for set_value_by_urn."""
    user = User(user_name="test")

    set_value_by_urn(user, "nonExistent", "value")

    user.emails = [Email(value="test@example.com")]
    set_value_by_urn(user, "emails.value", "new@example.com")
    assert user.emails[0].value == "test@example.com"


def test_set_value_by_urn_with_extension_schema():
    """Test set_value_by_urn with direct extension schema URN."""
    user = User[EnterpriseUser](user_name="test")

    # Set entire extension object
    enterprise_data = EnterpriseUser(cost_center="CC-789", department="IT")

    set_value_by_urn(
        user,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        enterprise_data,
    )

    assert user[EnterpriseUser] == enterprise_data
    assert user[EnterpriseUser].cost_center == "CC-789"
    assert user[EnterpriseUser].department == "IT"


def test_iter_all_urns_non_resource_type():
    """Test iter_all_urns with non-Resource type (should only yield base URNs)."""
    # Use Extension directly, not as part of a Resource
    urns = list(iter_all_urns(EnterpriseUser))
    # Should only contain URNs from the extension itself, no extension processing
    assert len(urns) > 0
    assert all(source_model == EnterpriseUser for _, source_model in urns)


def test_get_target_model_by_urn_with_resource_schema():
    """Test get_target_model_by_urn with resource's own schema prefix."""
    # User's own schema URN should work
    user_schema = "urn:ietf:params:scim:schemas:core:2.0:User"
    result = get_target_model_by_urn(User, f"{user_schema}:userName")
    assert result == (User, "user_name")


def test_get_target_model_by_urn_complex_path_error():
    """Test get_target_model_by_urn with invalid complex path."""
    # Invalid nested path should return None
    result = get_target_model_by_urn(User, "nonexistent.invalid.path")
    assert result is None


def test_get_value_by_urn_with_resource_schema():
    """Test get_value_by_urn with resource's own schema URN."""
    user = User(user_name="test")
    user_schema = "urn:ietf:params:scim:schemas:core:2.0:User"

    # Should work with resource's own schema prefix
    value = get_value_by_urn(user, f"{user_schema}:userName")
    assert value == "test"


def test_get_value_by_urn_extension_not_set():
    """Test get_value_by_urn when extension is not set."""
    user = User[EnterpriseUser](user_name="test")
    # Extension not set, should return None for extension URN
    cost_center = get_value_by_urn(
        user, "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:costCenter"
    )
    assert cost_center is None


def test_set_value_by_urn_with_resource_schema():
    """Test set_value_by_urn with resource's own schema URN."""
    user = User(user_name="test")
    user_schema = "urn:ietf:params:scim:schemas:core:2.0:User"

    # Should work with resource's own schema prefix
    set_value_by_urn(user, f"{user_schema}:userName", "updated")
    assert user.user_name == "updated"


def test_set_value_by_urn_cannot_create_complex_object():
    """Test set_value_by_urn when it cannot create a complex object."""
    user = User(user_name="test")

    # Create a scenario where field_type is not a BaseModel subclass
    # This is hard to trigger with real SCIM models, but tests the branch
    user.emails = [Email(value="test@example.com")]

    # Try to navigate into list - should return early due to isinstance(sub_obj, list)
    set_value_by_urn(user, "emails.value", "should_not_change")
    # Should not have changed
    assert user.emails[0].value == "test@example.com"


def test_set_value_by_urn_field_name_none_in_else():
    """Test set_value_by_urn when field_name is None in the else branch."""
    user = User(user_name="test")

    set_value_by_urn(user, "totallyNonExistent", "value")
    assert not hasattr(user, "totallyNonExistent")


def test_get_target_model_by_urn_unknown_extension():
    """Test get_target_model_by_urn with unknown extension schema."""
    result = get_target_model_by_urn(
        User[EnterpriseUser], "urn:unknown:schema:extension:unknown:2.0:User:field"
    )
    assert result is None


def test_get_value_by_urn_direct_extension_schema():
    """Test get_value_by_urn with direct extension schema URN."""
    user = User[EnterpriseUser](user_name="test")
    user[EnterpriseUser] = EnterpriseUser(cost_center="CC-123")

    extension = get_value_by_urn(
        user, "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )
    assert extension is not None
    assert extension.cost_center == "CC-123"


def test_set_value_ignores_empty_multivalued_field():
    """Test setting nested field on empty multivalued field is ignored."""
    user = User(user_name="test")
    user.emails = []

    set_value_by_urn(user, "emails.value", "test@example.com")

    assert user.emails == []


def test_get_target_model_returns_none_for_nonexistent_intermediate():
    """Test resolving path with nonexistent intermediate field returns None."""
    result = get_target_model_by_urn(User, "nonexistent.field.subfield")
    assert result is None


def test_get_value_returns_none_for_unset_field():
    """Test getting value from unset optional field returns None."""
    user = User(user_name="test")
    user.name = Name()

    value = get_value_by_urn(user, "name.formatted")

    assert value is None


def test_set_value_creates_missing_extension():
    """Test setting extension field creates extension object when missing."""
    user = User[EnterpriseUser](user_name="test")

    set_value_by_urn(
        user,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:costCenter",
        "CC-TEST",
    )

    assert user[EnterpriseUser] is not None
    assert user[EnterpriseUser].cost_center == "CC-TEST"


def test_set_value_creates_complex_object_for_nested_field():
    """Test creating complex object when setting nested field."""
    user = User(user_name="test")
    assert user.name is None

    set_value_by_urn(user, "name.givenName", "John")

    assert user.name is not None
    assert user.name.given_name == "John"


def test_set_value_ignores_nested_field_in_populated_multivalued():
    """Test setting nested field in populated multivalued attribute is ignored."""
    user = User(user_name="test")
    user.emails = [Email(value="test@example.com")]
    original_email = user.emails[0].value

    set_value_by_urn(user, "emails.value", "new@example.com")

    assert user.emails[0].value == original_email


def test_get_target_model_resolves_extension_schema():
    """Test resolving target model for extension URN."""
    result = get_target_model_by_urn(
        User[EnterpriseUser],
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:costCenter",
    )
    assert result == (EnterpriseUser, "cost_center")


def test_get_value_returns_entire_extension_object():
    """Test retrieving entire extension object by schema URN."""
    user = User[EnterpriseUser](user_name="test")
    user[EnterpriseUser] = EnterpriseUser(cost_center="CC-123")

    extension = get_value_by_urn(
        user, "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )
    assert extension.cost_center == "CC-123"


def test_set_value_replaces_entire_extension_object():
    """Test setting entire extension object by schema URN."""
    user = User[EnterpriseUser](user_name="test")
    new_extension = EnterpriseUser(cost_center="CC-456", department="IT")

    set_value_by_urn(
        user,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        new_extension,
    )
    assert user[EnterpriseUser].cost_center == "CC-456"
    assert user[EnterpriseUser].department == "IT"


def test_set_value_creates_intermediate_complex_object():
    """Test creating intermediate object when setting nested field."""
    user = User(user_name="test")
    assert user.name is None

    set_value_by_urn(user, "name.familyName", "Doe")

    assert user.name is not None
    assert user.name.family_name == "Doe"


def test_set_value_ignores_multivalued_field_navigation():
    """Test setting field on multivalued attribute is ignored."""
    user = User(user_name="test")
    user.addresses = [Address(country="US")]
    original_country = user.addresses[0].country

    set_value_by_urn(user, "addresses.country", "FR")

    assert user.addresses[0].country == original_country


def test_get_target_model_returns_none_for_invalid_nested_path():
    """Test resolving deeply nested invalid path returns None."""
    result = get_target_model_by_urn(User, "name.invalid.deeply.nested")
    assert result is None


def test_get_target_model_with_unknown_schema_falls_through():
    """Test handling URN with unknown schema that doesn't match extensions."""
    result = get_target_model_by_urn(User[EnterpriseUser], "urn:unknown:schema:field")
    assert result is None


def test_get_value_by_urn_with_direct_extension_schema_match():
    """Test getting value by direct extension schema match."""
    user = User[EnterpriseUser](user_name="test")
    user[EnterpriseUser] = EnterpriseUser(cost_center="CC-123")

    extension = get_value_by_urn(
        user, "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )
    assert extension.cost_center == "CC-123"


def test_get_value_by_urn_with_unknown_schema_falls_through():
    """Test getting value with unknown schema that doesn't match extensions."""
    user = User[EnterpriseUser](user_name="test")

    result = get_value_by_urn(user, "urn:unknown:schema:field")
    assert result is None


def test_set_value_by_urn_with_direct_extension_schema_match():
    """Test setting value by direct extension schema match."""
    user = User[EnterpriseUser](user_name="test")
    new_extension = EnterpriseUser(cost_center="CC-456")

    set_value_by_urn(
        user,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        new_extension,
    )
    assert user[EnterpriseUser] == new_extension


def test_set_value_by_urn_with_unknown_schema_falls_through():
    """Test setting value with unknown schema that doesn't match extensions."""
    user = User[EnterpriseUser](user_name="test")

    set_value_by_urn(user, "urn:unknown:schema:field", "value")


def test_urn_with_colon_but_no_extension_match():
    """Test URN with colon that doesn't match any extension schema."""
    user = User[EnterpriseUser](user_name="test")

    result = get_target_model_by_urn(user.__class__, "urn:other:schema:userName")
    assert result is None

    value = get_value_by_urn(user, "urn:other:schema:userName")
    assert value is None

    original_username = user.user_name
    set_value_by_urn(user, "urn:other:schema:userName", "testvalue")
    assert user.user_name == original_username


def test_urn_fallthrough_with_dot():
    """Test URN that falls through extension processing to dot handling."""
    user = User[EnterpriseUser](user_name="test")

    result = get_target_model_by_urn(user.__class__, "urn:other:schema:name.givenName")
    assert result is None

    value = get_value_by_urn(user, "urn:other:schema:name.givenName")
    assert value is None

    set_value_by_urn(user, "urn:other:schema:name.givenName", "test")


def test_extension_loop_fallthrough():
    """Test URN that loops through extensions but finds no match."""
    user = User[EnterpriseUser](user_name="test")

    result = get_target_model_by_urn(user.__class__, "urn:nomatch:userName")
    assert result is None

    value = get_value_by_urn(user, "urn:nomatch:userName")
    assert value is None

    set_value_by_urn(user, "urn:nomatch:userName", "Jane")
    assert user.user_name == "test"


def test_get_target_model_by_urn_extension_bad_schema():
    assert get_target_model_by_urn(EnterpriseUser, "bad:urn") is None


def test_get_value_by_urn_extension_bad_schema():
    assert get_value_by_urn(EnterpriseUser(), "bad:urn") is None


def test_set_value_by_urn_extension_bad_schema():
    obj = EnterpriseUser()
    set_value_by_urn(obj, "bad:urn", "foobar")
    assert obj == EnterpriseUser()
