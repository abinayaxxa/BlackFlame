"""Central access-control helpers for Black Flame security and role enforcement."""

from __future__ import annotations

from typing import Any, Iterable, Optional

FAMILY_ACCOUNT_TYPE = "family"
STAFF_ROLES = {"SYSTEM_ADMINISTRATOR", "HOSPITAL_STAFF", "RESCUE_CAMP_STAFF"}


def get_account_type(account: Optional[dict]) -> Optional[str]:
    """Return the normalized account type for a session user."""
    if not account:
        return None
    account_type = str(account.get("account_type") or "").strip().lower()
    if account_type:
        return account_type
    return "staff" if account.get("role") else None


def is_family_account(account: Optional[dict]) -> bool:
    return get_account_type(account) == FAMILY_ACCOUNT_TYPE


def is_staff_account(account: Optional[dict]) -> bool:
    return get_account_type(account) == "staff"


def get_account_role(account: Optional[dict]) -> str:
    """Normalize the staff role name for access checks."""
    if not account:
        return ""
    if is_family_account(account):
        return "FAMILY"
    role = str(account.get("role") or "").strip().upper()
    return role


def require_access(
    account: Optional[dict],
    *,
    allowed_roles: Optional[Iterable[str]] = None,
    allowed_account_types: Optional[Iterable[str]] = None,
    require_auth: bool = True,
) -> bool:
    """Enforce a minimum permission gate.

    Returns True when the provided account is allowed; False otherwise.
    """
    if require_auth and not account:
        return False

    if allowed_account_types:
        normalized_types = {str(v).strip().lower() for v in allowed_account_types}
        if get_account_type(account) in normalized_types:
            return True

    if allowed_roles:
        normalized_roles = {str(v).strip().upper() for v in allowed_roles}
        if get_account_role(account) in normalized_roles:
            return True

    return False
