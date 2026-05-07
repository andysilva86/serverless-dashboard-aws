"""Shared pytest fixtures: mocked DynamoDB, Cognito and EventBridge via moto."""

from __future__ import annotations

from collections.abc import Iterator

import boto3
import pytest
from moto import mock_aws

TABLE_NAME = "serverless-dashboard-test"
USER_POOL_NAME = "serverless-dashboard-test-pool"
EVENT_BUS_NAME = "serverless-dashboard-test-bus"
WEBHOOK_API_KEY = "test-api-key"


@pytest.fixture(autouse=True)
def aws_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("TABLE_NAME", TABLE_NAME)
    monkeypatch.setenv("EVENT_BUS_NAME", EVENT_BUS_NAME)
    monkeypatch.setenv("WEBHOOK_API_KEY", WEBHOOK_API_KEY)


@pytest.fixture
def aws() -> Iterator[None]:
    with mock_aws():
        yield


@pytest.fixture
def dynamo_table(aws: None) -> Iterator[None]:
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName=TABLE_NAME,
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "GSI1",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    yield


@pytest.fixture
def cognito_pool(aws: None, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[str, str]]:
    client = boto3.client("cognito-idp", region_name="us-east-1")
    pool = client.create_user_pool(
        PoolName=USER_POOL_NAME,
        Policies={
            "PasswordPolicy": {
                "MinimumLength": 8,
                "RequireUppercase": False,
                "RequireLowercase": False,
                "RequireNumbers": False,
                "RequireSymbols": False,
            }
        },
        AutoVerifiedAttributes=["email"],
        UsernameAttributes=["email"],
        Schema=[
            {"Name": "email", "AttributeDataType": "String", "Required": True},
            {"Name": "name", "AttributeDataType": "String", "Required": False},
        ],
    )
    pool_id = pool["UserPool"]["Id"]
    pool_client = client.create_user_pool_client(
        UserPoolId=pool_id,
        ClientName="serverless-dashboard-test-client",
        ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"],
    )
    client_id = pool_client["UserPoolClient"]["ClientId"]
    monkeypatch.setenv("USER_POOL_ID", pool_id)
    monkeypatch.setenv("USER_POOL_CLIENT_ID", client_id)
    yield (pool_id, client_id)


@pytest.fixture
def event_bus(aws: None) -> Iterator[str]:
    client = boto3.client("events", region_name="us-east-1")
    client.create_event_bus(Name=EVENT_BUS_NAME)
    yield EVENT_BUS_NAME


def make_authed_event(sub: str, *, body: str | None = None, email: str = "user@example.com") -> dict:
    return {
        "body": body,
        "headers": {"Content-Type": "application/json"},
        "requestContext": {
            "authorizer": {"jwt": {"claims": {"sub": sub, "email": email, "name": "Test"}}}
        },
    }
