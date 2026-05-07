"""Tests for POST /integrations/dispatch."""

from __future__ import annotations

import json

from handlers.integrations import dispatch

from .conftest import make_authed_event


def test_dispatch_publishes_and_stores(dynamo_table: None, event_bus: str) -> None:
    res = dispatch.handler(
        make_authed_event(
            "sub-1",
            body=json.dumps({"eventType": "user_action", "data": {"x": 1}}),
        ),
        None,
    )
    assert res["statusCode"] == 201, res
    body = json.loads(res["body"])
    assert body["id"].startswith("EVENT#")


def test_dispatch_unauthorized_without_sub(event_bus: str) -> None:
    res = dispatch.handler({"requestContext": {}, "body": "{}"}, None)
    assert res["statusCode"] == 401


def test_dispatch_requires_event_type(dynamo_table: None, event_bus: str) -> None:
    res = dispatch.handler(make_authed_event("sub-1", body=json.dumps({})), None)
    assert res["statusCode"] == 400


def test_dispatch_data_must_be_object(dynamo_table: None, event_bus: str) -> None:
    res = dispatch.handler(
        make_authed_event(
            "sub-1",
            body=json.dumps({"eventType": "x", "data": "nope"}),
        ),
        None,
    )
    assert res["statusCode"] == 400
