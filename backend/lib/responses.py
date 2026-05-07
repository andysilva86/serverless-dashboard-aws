"""HTTP response helpers for API Gateway HTTP API Lambda integrations."""

from __future__ import annotations

import json
from typing import Any

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-API-Key",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


def response(status_code: int, body: Any) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(body, default=str),
    }


def ok(body: Any) -> dict[str, Any]:
    return response(200, body)


def created(body: Any) -> dict[str, Any]:
    return response(201, body)


def bad_request(message: str, *, code: str = "bad_request") -> dict[str, Any]:
    return response(400, {"error": code, "message": message})


def unauthorized(message: str = "unauthorized") -> dict[str, Any]:
    return response(401, {"error": "unauthorized", "message": message})


def forbidden(message: str = "forbidden") -> dict[str, Any]:
    return response(403, {"error": "forbidden", "message": message})


def not_found(message: str = "not found") -> dict[str, Any]:
    return response(404, {"error": "not_found", "message": message})


def conflict(message: str) -> dict[str, Any]:
    return response(409, {"error": "conflict", "message": message})


def server_error(message: str = "internal server error") -> dict[str, Any]:
    return response(500, {"error": "internal_error", "message": message})
