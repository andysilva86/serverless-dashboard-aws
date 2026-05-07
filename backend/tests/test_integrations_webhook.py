"""Tests for POST /integrations/webhook."""

from __future__ import annotations

import json

from handlers.integrations import webhook

from .conftest import WEBHOOK_API_KEY


def make_event(body: dict | str | None, *, api_key: str | None = WEBHOOK_API_KEY) -> dict:
    if isinstance(body, dict):
        body = json.dumps(body)
    headers = {"Content-Type": "application/json"}
    if api_key is not None:
        headers["X-API-Key"] = api_key
    return {"body": body, "headers": headers}


def test_webhook_stores_event(dynamo_table: None) -> None:
    res = webhook.handler(
        make_event({"userSub": "sub-1", "eventType": "ping", "data": {"value": 1}}),
        None,
    )
    assert res["statusCode"] == 201, res
    body = json.loads(res["body"])
    assert body["eventType"] == "ping"


def test_webhook_rejects_invalid_api_key(dynamo_table: None) -> None:
    res = webhook.handler(
        make_event({"userSub": "sub-1", "eventType": "ping"}, api_key="bad"),
        None,
    )
    assert res["statusCode"] == 401


def test_webhook_requires_fields(dynamo_table: None) -> None:
    res = webhook.handler(make_event({"userSub": "sub-1"}), None)
    assert res["statusCode"] == 400


def test_webhook_invalid_json(dynamo_table: None) -> None:
    res = webhook.handler(make_event("garbage"), None)
    assert res["statusCode"] == 400


def test_webhook_data_must_be_object(dynamo_table: None) -> None:
    res = webhook.handler(
        make_event({"userSub": "sub-1", "eventType": "x", "data": "nope"}),
        None,
    )
    assert res["statusCode"] == 400
