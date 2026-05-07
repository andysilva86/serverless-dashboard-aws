"""Tests for GET /users/me."""

from __future__ import annotations

import json

from handlers.users import me

from .conftest import make_authed_event


def test_users_me_returns_existing_profile(dynamo_table: None) -> None:
    from lib import db

    db.put_user_profile("sub-1", email="a@b.com", name="Anderson")
    res = me.handler(make_authed_event("sub-1", email="a@b.com"), None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["email"] == "a@b.com"


def test_users_me_lazy_creates_profile_when_missing(dynamo_table: None) -> None:
    res = me.handler(make_authed_event("sub-2", email="lazy@b.com"), None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["sub"] == "sub-2"
    assert body["email"] == "lazy@b.com"


def test_users_me_unauthorized_without_sub() -> None:
    res = me.handler({"requestContext": {}}, None)
    assert res["statusCode"] == 401
