"""GET /dashboard/stats — aggregate metrics for the authenticated user."""

from __future__ import annotations

from typing import Any

from lib import db, responses
from lib.auth import require_sub


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        sub = require_sub(event)
    except PermissionError:
        return responses.unauthorized()

    stats = db.stats_for_user(sub)
    return responses.ok(stats)
