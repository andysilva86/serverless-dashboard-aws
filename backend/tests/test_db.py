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
    assert stats["truncated"] is False


def test_stats_for_user_paginates_beyond_one_page(dynamo_table: None) -> None:
    """Sanity check that the new pagination loop returns more than the
    legacy 200-item cap when the user has more events than one DynamoDB
    page worth (we ask for 250 to cross the internal page boundary)."""
    for i in range(250):
        db.put_event("sub-paged", event_type=f"type{i % 4}", payload={"i": i})
    stats = db.stats_for_user("sub-paged")
    assert stats["totalEvents"] == 250
    assert sum(stats["byType"].values()) == 250
    assert stats["truncated"] is False


def test_stats_for_user_marks_truncated_when_max_items_hit(dynamo_table: None) -> None:
    for i in range(15):
        db.put_event("sub-cap", event_type="t", payload={"i": i})
    stats = db.stats_for_user("sub-cap", max_items=10)
    assert stats["totalEvents"] == 10
    assert stats["truncated"] is True


def test_put_user_profile_if_not_exists_preserves_first_write(dynamo_table: None) -> None:
    """Concurrent lazy-create paths must not overwrite the original
    ``createdAt`` once a profile row exists."""
    first = db.put_user_profile(
        "sub-race", email="first@example.com", name="First", if_not_exists=True
    )
    second = db.put_user_profile(
        "sub-race", email="second@example.com", name="Second", if_not_exists=True
    )
    assert second["createdAt"] == first["createdAt"]
    assert second["email"] == "first@example.com"
    assert second["name"] == "First"


def test_get_table_requires_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TABLE_NAME", raising=False)
    with pytest.raises(RuntimeError):
        db.get_table()
