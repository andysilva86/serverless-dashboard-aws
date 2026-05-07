"""GET /users/me — returns the authenticated user's profile."""

from __future__ import annotations

from typing import Any

from lib import db, responses
from lib.auth import claims_from_event, require_sub
from lib.logging import get_logger

logger = get_logger(__name__)


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        sub = require_sub(event)
    except PermissionError:
        return responses.unauthorized()

    profile = db.get_user_profile(sub)
    if profile is None:
        claims = claims_from_event(event)
        email = str(claims.get("email") or "")
        name = str(claims.get("name") or "")
        profile = db.put_user_profile(sub, email=email, name=name, if_not_exists=True)

    return responses.ok(
        {
            "sub": profile["sub"],
            "email": profile["email"],
            "name": profile.get("name", ""),
            "createdAt": profile["createdAt"],
        }
    )
