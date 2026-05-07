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
from botocore.exceptions import ClientError

TABLE_NAME_ENV = "TABLE_NAME"
# Default cap for the dashboard event aggregation. Tuned to keep p99 query
# cost bounded; clients receive ``truncated=True`` when this cap is hit.
DEFAULT_STATS_MAX_ITEMS = 1000
_QUERY_PAGE_LIMIT = 100


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


def put_user_profile(
    sub: str,
    *,
    email: str,
    name: str | None = None,
    if_not_exists: bool = False,
) -> dict[str, Any]:
    """Upsert (or create-if-absent) the profile row for ``sub``.

    When ``if_not_exists=True`` we attach an ``attribute_not_exists(PK)``
    condition so concurrent lazy-create paths (e.g. two simultaneous
    ``GET /users/me`` requests for a user whose profile row was never
    written) can't race-overwrite each other's ``createdAt``. On a
    conditional check failure we fall back to returning the existing
    profile so callers always receive a well-formed item.
    """
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
    kwargs: dict[str, Any] = {"Item": item}
    if if_not_exists:
        kwargs["ConditionExpression"] = "attribute_not_exists(PK)"
    try:
        table.put_item(**kwargs)
    except ClientError as exc:
        if (
            if_not_exists
            and exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"
        ):
            existing = get_user_profile(sub)
            if existing is not None:
                return existing
        raise
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


def stats_for_user(sub: str, *, max_items: int = DEFAULT_STATS_MAX_ITEMS) -> dict[str, Any]:
    """Aggregate event metrics for ``sub`` across paginated DynamoDB queries.

    The previous implementation silently capped at 200 events, which made
    ``totalEvents`` and ``byType`` undercount for active users. We now page
    through up to ``max_items`` events and surface a ``truncated`` flag so
    consumers can tell when the response is an approximation rather than
    a full count.
    """
    table = get_table()
    by_type: dict[str, int] = {}
    latest_event: dict[str, Any] | None = None
    total = 0
    last_key: dict[str, Any] | None = None
    truncated = False

    while total < max_items:
        params: dict[str, Any] = {
            "KeyConditionExpression": "PK = :pk AND begins_with(SK, :sk)",
            "ExpressionAttributeValues": {":pk": user_pk(sub), ":sk": "EVENT#"},
            "ScanIndexForward": False,
            "Limit": min(_QUERY_PAGE_LIMIT, max_items - total),
        }
        if last_key is not None:
            params["ExclusiveStartKey"] = last_key
        res = table.query(**params)
        for item in res.get("Items", []):
            total += 1
            event_type = str(item.get("eventType", "unknown"))
            by_type[event_type] = by_type.get(event_type, 0) + 1
            if latest_event is None:
                latest_event = dict(item)
        last_key = res.get("LastEvaluatedKey")
        if last_key is None:
            break
    else:
        # Hit ``max_items`` while DynamoDB still has more pages to give us.
        truncated = last_key is not None

    return {
        "totalEvents": total,
        "byType": by_type,
        "latestEvent": latest_event,
        "truncated": truncated,
    }
