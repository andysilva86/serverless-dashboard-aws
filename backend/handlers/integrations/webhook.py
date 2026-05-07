"""POST /integrations/webhook — inbound webhook protected by an API key.

External systems POST events here using the shared ``X-API-Key`` header. The
payload must contain ``userSub`` (the Cognito sub of the target user) and
``eventType``. Anything under ``data`` is stored as the event payload.
"""

from __future__ import annotations

import json
from typing import Any

from lib import db, responses
from lib.auth import require_api_key
from lib.logging import get_logger

logger = get_logger(__name__)


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        require_api_key(event)
    except PermissionError:
        return responses.unauthorized("invalid api key")
    except RuntimeError:
        # ``WEBHOOK_API_KEY`` is missing in the Lambda environment. Raising
        # here would surface as a raw 500 without CORS headers or a JSON
        # body; return a structured error instead and log loudly.
        logger.exception("webhook misconfigured: WEBHOOK_API_KEY env var is not set")
        return responses.server_error("webhook misconfigured")

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return responses.bad_request("invalid JSON body")

    sub = (body.get("userSub") or "").strip()
    event_type = (body.get("eventType") or "").strip()
    data = body.get("data") or {}

    if not sub or not event_type:
        return responses.bad_request("userSub and eventType are required")
    if not isinstance(data, dict):
        return responses.bad_request("data must be an object")

    item = db.put_event(sub, event_type=event_type, payload=data)
    logger.info("webhook event stored", extra={"sub": sub, "eventType": event_type})

    return responses.created(
        {"id": item["SK"], "createdAt": item["createdAt"], "eventType": event_type}
    )
