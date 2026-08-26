from decimal import Decimal
from typing import Optional

from boto3.dynamodb.conditions import Key

from config.settings import EnvironmentConfig
from infrastructure.dynamo_handler import get_table


def _sanitize(item: dict) -> dict:
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in item.items()}


def find_by_season(season: str, conference: Optional[str] = None) -> list[dict]:
    """シーズン順位表を取得する。conference 指定時は East / West に絞る。"""
    table = get_table(EnvironmentConfig.get_standings_table())
    response = table.query(
        KeyConditionExpression=Key("season").eq(season),
    )
    items = [_sanitize(item) for item in response.get("Items", [])]
    if conference:
        items = [item for item in items if item.get("conference") == conference]
    items.sort(key=lambda x: (x.get("conference", ""), x.get("seed", 99)))
    return items
