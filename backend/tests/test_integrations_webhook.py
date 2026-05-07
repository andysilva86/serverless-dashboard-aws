"""Tests for POST /integrations/webhook."""

from __future__ import annotations

import json

import pytest
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


def test_webhook_rejects_missing_api_key(dynamo_table: None) -> None:
    res = webhook.handler(
        make_event({"userSub": "sub-1", "eventType": "ping"}, api_key=None),
        None,
    )
    assert res["statusCode"] == 401


def test_webhook_rejects_api_key_of_different_length(dynamo_table: None) -> None:
    """`hmac.compare_digest` raises TypeError on bytes-vs-str mismatches but
    accepts strings of differing length — the result must still be a 401."""
    res = webhook.handler(
        make_event({"userSub": "sub-1", "eventType": "ping"}, api_key="x"),
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


def test_webhook_returns_500_when_api_key_env_missing(
    dynamo_table: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When ``WEBHOOK_API_KEY`` is unset, ``require_api_key`` raises
    ``RuntimeError``. The handler must catch that and return a structured
    500 (with CORS headers and a JSON body) instead of crashing the Lambda
    with an unhandled exception."""
    monkeypatch.delenv("WEBHOOK_API_KEY", raising=False)
    res = webhook.handler(
        make_event({"userSub": "sub-1", "eventType": "ping"}, api_key="anything"),
        None,
    )
    assert res["statusCode"] == 500
    assert res["headers"]["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert body["error"] == "internal_error"
