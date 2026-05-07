"""Unit tests for the response helpers."""

from __future__ import annotations

import json

from lib import responses


def test_ok_returns_200_and_cors_headers() -> None:
    res = responses.ok({"hello": "world"})
    assert res["statusCode"] == 200
    assert res["headers"]["Content-Type"] == "application/json"
    assert res["headers"]["Access-Control-Allow-Origin"] == "*"
    assert json.loads(res["body"]) == {"hello": "world"}


def test_error_helpers_carry_error_codes() -> None:
    assert json.loads(responses.bad_request("nope")["body"])["error"] == "bad_request"
    assert json.loads(responses.unauthorized()["body"])["error"] == "unauthorized"
    assert json.loads(responses.forbidden()["body"])["error"] == "forbidden"
    assert json.loads(responses.not_found()["body"])["error"] == "not_found"
    assert json.loads(responses.conflict("dup")["body"])["error"] == "conflict"
    assert json.loads(responses.server_error()["body"])["error"] == "internal_error"
