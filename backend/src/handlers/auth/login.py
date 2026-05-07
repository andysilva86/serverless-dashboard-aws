"""POST /auth/login — authenticates a Cognito user and returns the JWT id/access tokens."""

from __future__ import annotations

import json
from typing import Any

from botocore.exceptions import ClientError

from lib import responses
from lib.auth import cognito_client, get_user_pool_client_id
from lib.logging import get_logger

logger = get_logger(__name__)


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return responses.bad_request("invalid JSON body")

    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    if not email or not password:
        return responses.bad_request("email and password are required")

    client = cognito_client()
    try:
        result = client.initiate_auth(
            ClientId=get_user_pool_client_id(),
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "Unknown")
        logger.warning("login failed", extra={"code": code, "email": email})
        if code in {"NotAuthorizedException", "UserNotFoundException"}:
            return responses.unauthorized("invalid credentials")
        if code == "UserNotConfirmedException":
            return responses.forbidden("user not confirmed")
        return responses.server_error("authentication error")

    auth_result = result.get("AuthenticationResult") or {}
    if not auth_result:
        return responses.unauthorized("authentication challenge required")

    return responses.ok(
        {
            "idToken": auth_result.get("IdToken"),
            "accessToken": auth_result.get("AccessToken"),
            "refreshToken": auth_result.get("RefreshToken"),
            "expiresIn": auth_result.get("ExpiresIn"),
            "tokenType": auth_result.get("TokenType"),
        }
    )
