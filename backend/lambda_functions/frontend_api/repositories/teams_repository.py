from decimal import Decimal
from typing import Optional

from boto3.dynamodb.conditions import Key

from config.settings import EnvironmentConfig
from infrastructure.dynamo_handler import get_table


def _sanitize(item: dict) -> dict:
    """DynamoDB の Decimal を float に変換する。"""
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in item.items()}


def find_all(conference: Optional[str] = None) -> list[dict]:
    table = get_table(EnvironmentConfig.get_teams_table())

    if conference:
        response = table.query(
            IndexName="conference-index",
            KeyConditionExpression=Key("conference").eq(conference),
        )
    else:
        response = table.scan()

    return [_sanitize(item) for item in response.get("Items", [])]


def find_by_id(team_id: str) -> Optional[dict]:
    table = get_table(EnvironmentConfig.get_teams_table())
    response = table.get_item(Key={"team_id": team_id})
    item = response.get("Item")
    return _sanitize(item) if item else None
