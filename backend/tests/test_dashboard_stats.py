"""Tests for GET /dashboard/stats."""

from __future__ import annotations

import json

from handlers.dashboard import stats

from .conftest import make_authed_event


def test_stats_aggregates_events(dynamo_table: None) -> None:
    from lib import db

    db.put_event("sub-1", event_type="login", payload={})
    db.put_event("sub-1", event_type="page_view", payload={"p": "/home"})
    res = stats.handler(make_authed_event("sub-1"), None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["totalEvents"] == 2
    assert body["byType"] == {"login": 1, "page_view": 1}


def test_stats_unauthorized_without_sub() -> None:
    res = stats.handler({"requestContext": {}}, None)
    assert res["statusCode"] == 401
