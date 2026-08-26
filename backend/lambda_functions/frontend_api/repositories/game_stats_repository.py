from decimal import Decimal

from boto3.dynamodb.conditions import Key

from config.settings import EnvironmentConfig
from infrastructure.dynamo_handler import get_table


def _sanitize(item: dict) -> dict:
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in item.items()}


def find_by_game(game_id: str) -> list[dict]:
    """試合のボックススコア（全選手）を得点降順で取得する。"""
    table = get_table(EnvironmentConfig.get_game_stats_table())
    response = table.query(
        KeyConditionExpression=Key("game_id").eq(game_id),
    )
    items = [_sanitize(item) for item in response.get("Items", [])]
    items.sort(key=lambda x: x.get("points", 0), reverse=True)
    return items


def find_by_player(player_id: str, limit: int = 20) -> list[dict]:
    """選手のゲームログを新しい順で取得する。"""
    table = get_table(EnvironmentConfig.get_game_stats_table())
    response = table.query(
        IndexName="player-index",
        KeyConditionExpression=Key("player_id").eq(player_id),
        ScanIndexForward=False,
        Limit=limit,
    )
    return [_sanitize(item) for item in response.get("Items", [])]


def scan_all() -> list[dict]:
    """リーダーボード集計用に全件スキャンする。"""
    table = get_table(EnvironmentConfig.get_game_stats_table())
    items: list[dict] = []
    response = table.scan()
    items.extend(_sanitize(item) for item in response.get("Items", []))
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(_sanitize(item) for item in response.get("Items", []))
    return items
