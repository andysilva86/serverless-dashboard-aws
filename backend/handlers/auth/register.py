"""POST /auth/register — registers a new user in Cognito and stores a profile row."""

from __future__ import annotations

import json
from typing import Any

from botocore.exceptions import ClientError
from lib import db, responses
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
    name = (body.get("name") or "").strip()

    if not email or not password:
        return responses.bad_request("email and password are required")

    client = cognito_client()
    try:
        result = client.sign_up(
            ClientId=get_user_pool_client_id(),
            Username=email,
            Password=password,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "name", "Value": name},
            ],
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "Unknown")
        message = exc.response.get("Error", {}).get("Message", "Cognito error")
        logger.warning("sign_up failed", extra={"code": code, "email": email})
        if code == "UsernameExistsException":
            return responses.conflict("user already exists")
        if code in {"InvalidPasswordException", "InvalidParameterException"}:
            return responses.bad_request(message, code=code)
        return responses.server_error(message)

    sub = result["UserSub"]
    db.put_user_profile(sub, email=email, name=name)
    logger.info("user registered", extra={"sub": sub, "email": email})

    return responses.created(
        {
            "sub": sub,
            "email": email,
            "name": name,
            "confirmed": result.get("UserConfirmed", False),
        }
    )
