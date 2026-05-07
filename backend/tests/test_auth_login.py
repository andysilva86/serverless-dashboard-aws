"""Tests for the /auth/login handler."""

from __future__ import annotations

import json
import os

import boto3

from handlers.auth import login, register


def _register(email: str, password: str) -> None:
    register.handler(
        {"body": json.dumps({"email": email, "password": password, "name": "u"})},
        None,
    )


def _confirm(email: str) -> None:
    client = boto3.client("cognito-idp", region_name="us-east-1")
    client.admin_confirm_sign_up(UserPoolId=os.environ["USER_POOL_ID"], Username=email)


def test_login_returns_tokens(cognito_pool: tuple[str, str], dynamo_table: None) -> None:
    _register("login@example.com", "Password!1")
    _confirm("login@example.com")
    res = login.handler(
        {"body": json.dumps({"email": "login@example.com", "password": "Password!1"})},
        None,
    )
    assert res["statusCode"] == 200, res
    body = json.loads(res["body"])
    assert body["idToken"]
    assert body["accessToken"]


def test_login_with_wrong_password_is_unauthorized(
    cognito_pool: tuple[str, str], dynamo_table: None
) -> None:
    _register("wrong@example.com", "Password!1")
    _confirm("wrong@example.com")
    res = login.handler(
        {"body": json.dumps({"email": "wrong@example.com", "password": "nope"})},
        None,
    )
    assert res["statusCode"] == 401


def test_login_unknown_user_is_unauthorized(
    cognito_pool: tuple[str, str], dynamo_table: None
) -> None:
    res = login.handler(
        {"body": json.dumps({"email": "missing@example.com", "password": "Password!1"})},
        None,
    )
    assert res["statusCode"] == 401


def test_login_requires_email_and_password(cognito_pool: tuple[str, str]) -> None:
    res = login.handler({"body": json.dumps({"email": ""})}, None)
    assert res["statusCode"] == 400
