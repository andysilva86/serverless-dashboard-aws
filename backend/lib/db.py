"""DynamoDB helpers using a single-table design.

Layout
------
PK / SK keys:
- PK: "USER#<sub>"   SK: "PROFILE"           -> user profile metadata
- PK: "USER#<sub>"   SK: "EVENT#<iso-ts>"    -> tracking events for the user
- PK: "WEBHOOK#<id>" SK: "RECEIVED#<iso-ts>" -> incoming webhook payloads

GSI1 (GSI1PK / GSI1SK) is reserved for cross-user listings such as
``GSI1PK = "EVENT_TYPE#<type>"`` so the dashboard can aggregate without scans.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config

TABLE_NAME_ENV = "TABLE_NAME"


@lru_cache(maxsize=1)
def _resource() -> Any:
    return boto3.resource("dynamodb", config=Config(retries={"max_attempts": 5, "mode": "standard"}))


def get_table() -> Any:
    name = os.environ.get(TABLE_NAME_ENV)
    if not name:
        raise RuntimeError(f"Environment variable {TABLE_NAME_ENV} is not set")
    return _resource().Table(name)


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def user_pk(sub: str) -> str:
    return f"USER#{sub}"


def event_sk(iso_ts: str, *, suffix: str | None = None) -> str:
    suffix = suffix or uuid.uuid4().hex[:8]
    return f"EVENT#{iso_ts}#{suffix}"


def put_user_profile(sub: str, *, email: str, name: str | None = None) -> dict[str, Any]:
    table = get_table()
    item: dict[str, Any] = {
        "PK": user_pk(sub),
        "SK": "PROFILE",
        "type": "USER_PROFILE",
        "sub": sub,
        "email": email,
        "name": name or "",
        "createdAt": now_iso(),
    }
    table.put_item(Item=item)
    return item


def get_user_profile(sub: str) -> dict[str, Any] | None:
    table = get_table()
    res = table.get_item(Key={"PK": user_pk(sub), "SK": "PROFILE"})
    item = res.get("Item")
    return dict(item) if item else None


def put_event(sub: str, *, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    table = get_table()
    ts = now_iso()
    item: dict[str, Any] = {
        "PK": user_pk(sub),
        "SK": event_sk(ts),
        "type": "EVENT",
        "eventType": event_type,
        "payload": payload,
        "createdAt": ts,
        "GSI1PK": f"EVENT_TYPE#{event_type}",
        "GSI1SK": ts,
    }
    table.put_item(Item=item)
    return item


def list_events(sub: str, *, limit: int = 50) -> list[dict[str, Any]]:
    table = get_table()
    res = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk)",
        ExpressionAttributeValues={":pk": user_pk(sub), ":sk": "EVENT#"},
        ScanIndexForward=False,
        Limit=limit,
    )
    return [dict(item) for item in res.get("Items", [])]


def stats_for_user(sub: str) -> dict[str, Any]:
    events = list_events(sub, limit=200)
    by_type: dict[str, int] = {}
    for event in events:
        key = str(event.get("eventType", "unknown"))
        by_type[key] = by_type.get(key, 0) + 1
    return {
        "totalEvents": len(events),
        "byType": by_type,
        "latestEvent": events[0] if events else None,
    }
