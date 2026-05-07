"""POST /integrations/dispatch — outbound integration that publishes to EventBridge.

Authenticated users push events here that get fanned out via an EventBridge
custom bus to downstream systems (other Lambdas, SQS targets, partner
HTTP endpoints, etc.).
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

import boto3

from lib import db, responses
from lib.auth import require_sub
from lib.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _events_client() -> Any:
    return boto3.client("events")


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        sub = require_sub(event)
    except PermissionError:
        return responses.unauthorized()

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return responses.bad_request("invalid JSON body")

    event_type = (body.get("eventType") or "").strip()
    data = body.get("data") or {}
    if not event_type:
        return responses.bad_request("eventType is required")
    if not isinstance(data, dict):
        return responses.bad_request("data must be an object")

    bus_name = os.environ.get("EVENT_BUS_NAME")
    if not bus_name:
        return responses.server_error("EVENT_BUS_NAME is not set")

    detail = {"sub": sub, "eventType": event_type, "data": data}
    result = _events_client().put_events(
        Entries=[
            {
                "Source": "serverless-dashboard.app",
                "DetailType": event_type,
                "Detail": json.dumps(detail),
                "EventBusName": bus_name,
            }
        ]
    )
    failed = int(result.get("FailedEntryCount") or 0)
    if failed:
        logger.error("eventbridge dispatch failed", extra={"result": result})
        return responses.server_error("dispatch failed")

    item = db.put_event(sub, event_type=event_type, payload=data)
    return responses.created({"id": item["SK"], "createdAt": item["createdAt"]})
