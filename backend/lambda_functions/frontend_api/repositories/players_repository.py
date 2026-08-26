from decimal import Decimal
from typing import Optional

from boto3.dynamodb.conditions import Key

from config.settings import EnvironmentConfig
from infrastructure.dynamo_handler import get_table


def _sanitize(item: dict) -> dict:
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in item.items()}


def find_all(position: Optional[str] = None, team_id: Optional[str] = None) -> list[dict]:
    table = get_table(EnvironmentConfig.get_players_table())

    if team_id:
        response = table.query(
            IndexName="team-index",
            KeyConditionExpression=Key("team_id").eq(team_id),
        )
    elif position:
        response = table.query(
            IndexName="position-index",
            KeyConditionExpression=Key("position").eq(position.upper()),
        )
    else:
        response = table.scan()

    return [_sanitize(item) for item in response.get("Items", [])]


def find_by_id(player_id: str) -> Optional[dict]:
    table = get_table(EnvironmentConfig.get_players_table())
    response = table.get_item(Key={"player_id": player_id})
    item = response.get("Item")
    return _sanitize(item) if item else None


def find_stats(player_id: str, season: Optional[str] = None) -> Optional[dict]:
    """選手の今シーズンスタッツを取得する。season 省略時は最新 1 件を返す。"""
    table = get_table(EnvironmentConfig.get_player_stats_table())

    if season:
        response = table.get_item(Key={"player_id": player_id, "season": season})
        item = response.get("Item")
        return _sanitize(item) if item else None
    else:
        response = table.query(
            KeyConditionExpression=Key("player_id").eq(player_id),
            ScanIndexForward=False,
            Limit=1,
        )
        items = response.get("Items", [])
        return _sanitize(items[0]) if items else None


def find_all_stats(season: str) -> list[dict]:
    """指定シーズンの全選手スタッツをリーダーボード用に返す。

    PlayerStats テーブルは選手数（〜500件）が少ないためスキャン+フィルタで十分高速。
    """
    from boto3.dynamodb.conditions import Attr  # ローカルインポートで循環回避

    table = get_table(EnvironmentConfig.get_player_stats_table())
    items: list[dict] = []
    response = table.scan(FilterExpression=Attr("season").eq(season))
    items.extend(_sanitize(item) for item in response.get("Items", []))
    while "LastEvaluatedKey" in response:
        response = table.scan(
            FilterExpression=Attr("season").eq(season),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(_sanitize(item) for item in response.get("Items", []))
    return items
