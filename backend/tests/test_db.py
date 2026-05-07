"""Tests for the DynamoDB helpers using a moto-backed table."""

from __future__ import annotations

import pytest
from lib import db


def test_put_and_get_user_profile(dynamo_table: None) -> None:
    db.put_user_profile("sub-1", email="a@b.com", name="Anderson")
    profile = db.get_user_profile("sub-1")
    assert profile is not None
    assert profile["email"] == "a@b.com"
    assert profile["name"] == "Anderson"


def test_get_user_profile_missing_returns_none(dynamo_table: None) -> None:
    assert db.get_user_profile("does-not-exist") is None


def test_put_event_then_list_events(dynamo_table: None) -> None:
    db.put_event("sub-1", event_type="page_view", payload={"path": "/dashboard"})
    db.put_event("sub-1", event_type="page_view", payload={"path": "/profile"})
    events = db.list_events("sub-1")
    assert len(events) == 2
    assert {e["eventType"] for e in events} == {"page_view"}


def test_stats_for_user_aggregates_by_type(dynamo_table: None) -> None:
    db.put_event("sub-1", event_type="page_view", payload={})
    db.put_event("sub-1", event_type="page_view", payload={})
    db.put_event("sub-1", event_type="signup", payload={})
    stats = db.stats_for_user("sub-1")
    assert stats["totalEvents"] == 3
    assert stats["byType"] == {"page_view": 2, "signup": 1}
    assert stats["latestEvent"] is not None


def test_get_table_requires_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TABLE_NAME", raising=False)
    with pytest.raises(RuntimeError):
        db.get_table()
