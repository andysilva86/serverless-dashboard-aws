"""Tests for the /auth/register handler."""

from __future__ import annotations

import json

from handlers.auth import register


def make_event(body: dict | str | None) -> dict:
    if isinstance(body, dict):
        body = json.dumps(body)
    return {"body": body, "headers": {"Content-Type": "application/json"}}


def test_register_creates_user_and_profile(
    cognito_pool: tuple[str, str], dynamo_table: None
) -> None:
    res = register.handler(
        make_event({"email": "user@example.com", "password": "Password!1", "name": "User"}),
        None,
    )
    assert res["statusCode"] == 201, res
    body = json.loads(res["body"])
    assert body["email"] == "user@example.com"
    assert body["sub"]


def test_register_rejects_missing_password(
    cognito_pool: tuple[str, str], dynamo_table: None
) -> None:
    res = register.handler(make_event({"email": "user@example.com"}), None)
    assert res["statusCode"] == 400


def test_register_invalid_json(cognito_pool: tuple[str, str], dynamo_table: None) -> None:
    res = register.handler(make_event("{not json"), None)
    assert res["statusCode"] == 400


def test_register_duplicate_returns_409(
    cognito_pool: tuple[str, str], dynamo_table: None
) -> None:
    payload = {"email": "dup@example.com", "password": "Password!1", "name": "Dup"}
    first = register.handler(make_event(payload), None)
    assert first["statusCode"] == 201
    second = register.handler(make_event(payload), None)
    assert second["statusCode"] == 409
