"""Authentication helpers for Cognito + API Gateway HTTP API JWT authorizer."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import boto3


def get_user_pool_id() -> str:
    value = os.environ.get("USER_POOL_ID")
    if not value:
        raise RuntimeError("USER_POOL_ID is not set")
    return value


def get_user_pool_client_id() -> str:
    value = os.environ.get("USER_POOL_CLIENT_ID")
    if not value:
        raise RuntimeError("USER_POOL_CLIENT_ID is not set")
    return value


@lru_cache(maxsize=1)
def cognito_client() -> Any:
    return boto3.client("cognito-idp")


def claims_from_event(event: dict[str, Any]) -> dict[str, Any]:
    """Extract JWT claims injected by the API Gateway JWT authorizer.

    Returns an empty dict when the request was not authenticated so the caller
    can decide whether to reject it.
    """
    request_context = event.get("requestContext") or {}
    authorizer = request_context.get("authorizer") or {}
    jwt_block = authorizer.get("jwt") or {}
    claims = jwt_block.get("claims") or {}
    return dict(claims)


def require_sub(event: dict[str, Any]) -> str:
    claims = claims_from_event(event)
    sub = claims.get("sub")
    if not sub:
        raise PermissionError("missing sub claim in JWT")
    return str(sub)


def require_api_key(event: dict[str, Any]) -> None:
    """Validate the inbound webhook API key shared with external systems."""
    expected = os.environ.get("WEBHOOK_API_KEY")
    if not expected:
        raise RuntimeError("WEBHOOK_API_KEY is not configured")
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    provided = headers.get("x-api-key")
    if provided != expected:
        raise PermissionError("invalid api key")
