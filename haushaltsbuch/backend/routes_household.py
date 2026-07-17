from __future__ import annotations

from fastapi import APIRouter, Response, status

from . import assets, households
from .access import Principal
from .models import (
    AccountCreate,
    AccountUpdate,
    CategoryCreate,
    CategoryUpdate,
    HouseholdCreate,
    HouseholdDelete,
    HouseholdUpdate,
    InviteAccept,
    InviteCreate,
    MemberAdd,
    OwnershipTransfer,
)

router = APIRouter()


@router.get("/household")
def get_household(principal: Principal) -> dict:
    return households.get_household(principal)


@router.post("/household", status_code=status.HTTP_201_CREATED)
def create_household(body: HouseholdCreate, principal: Principal) -> dict:
    return households.create_household(body, principal)


@router.put("/household")
def update_household(body: HouseholdUpdate, principal: Principal) -> dict:
    return households.update_household(body, principal)


@router.post("/household/members", status_code=status.HTTP_201_CREATED)
def add_member(body: MemberAdd, principal: Principal) -> dict:
    return households.add_member(body.username, principal)


@router.delete("/household/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(member_id: int, revision: int, principal: Principal) -> Response:
    households.remove_member(member_id, revision, principal)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/household/ownership")
def transfer_ownership(body: OwnershipTransfer, principal: Principal) -> dict:
    return households.transfer_ownership(body.member_id, body.revision, principal)


@router.get("/household/invites")
def list_invites(principal: Principal) -> list[dict]:
    return households.list_invites(principal)


@router.post("/household/invites", status_code=status.HTTP_201_CREATED)
def create_invite(body: InviteCreate, principal: Principal) -> dict:
    return households.create_invite(body.expires_in_hours, principal)


@router.post("/household/invites/accept")
def accept_invite(body: InviteAccept, principal: Principal) -> dict:
    return households.accept_invite(body.code, principal)


@router.delete("/household/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invite(invite_id: int, revision: int, principal: Principal) -> Response:
    households.revoke_invite(invite_id, revision, principal)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/household/export")
def export_household(principal: Principal) -> dict:
    return households.export_household(principal)


@router.post("/household/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_household(body: HouseholdDelete, principal: Principal) -> Response:
    households.delete_household(body.household_name, principal)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/accounts")
def list_accounts(principal: Principal, include_archived: bool = False) -> list[dict]:
    return assets.list_accounts(principal, include_archived)


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
def create_account(body: AccountCreate, principal: Principal) -> dict:
    return assets.create_account(body, principal)


@router.put("/accounts/{account_id}")
def update_account(account_id: int, body: AccountUpdate, principal: Principal) -> dict:
    return assets.update_account(account_id, body, principal)


@router.get("/categories")
def list_categories(principal: Principal, include_archived: bool = False) -> list[dict]:
    return assets.list_categories(principal, include_archived)


@router.post("/categories", status_code=status.HTTP_201_CREATED)
def create_category(body: CategoryCreate, principal: Principal) -> dict:
    return assets.create_category(body, principal)


@router.put("/categories/{category_id}")
def update_category(
    category_id: int, body: CategoryUpdate, principal: Principal
) -> dict:
    return assets.update_category(category_id, body, principal)
