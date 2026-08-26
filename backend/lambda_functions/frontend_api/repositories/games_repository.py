from decimal import Decimal
from typing import Optional

from boto3.dynamodb.conditions import Key

from config.settings import EnvironmentConfig
from infrastructure.dynamo_handler import get_table


def _sanitize(item: dict) -> dict:
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in item.items()}


def find_by_id(game_id: str) -> Optional[dict]:
    """game-id-index GSI を使って game_id で 1 件取得する。"""
    table = get_table(EnvironmentConfig.get_games_table())
    response = table.query(
        IndexName="game-id-index",
        KeyConditionExpression=Key("game_id").eq(game_id),
        Limit=1,
    )
    items = response.get("Items", [])
    return _sanitize(items[0]) if items else None


def find_by_date(game_date: str) -> list[dict]:
    """指定日付の試合一覧を返す。"""
    table = get_table(EnvironmentConfig.get_games_table())
    response = table.query(
        KeyConditionExpression=Key("game_date").eq(game_date),
    )
    return [_sanitize(item) for item in response.get("Items", [])]


def find_recent(limit: int = 10) -> list[dict]:
    """最近の試合を新しい順で返す（scan + 日付降順ソート）。"""
    table = get_table(EnvironmentConfig.get_games_table())
    response = table.scan()
    items = [_sanitize(item) for item in response.get("Items", [])]
    items.sort(key=lambda x: x.get("game_date", ""), reverse=True)
    return items[:limit]


def find_by_team(team_id: str, limit: int = 10) -> list[dict]:
    """チームの試合をホーム・アウェイ両方の GSI から取得してマージする。"""
    table = get_table(EnvironmentConfig.get_games_table())

    home_resp = table.query(
        IndexName="home-team-index",
        KeyConditionExpression=Key("home_team_id").eq(team_id),
        ScanIndexForward=False,
        Limit=limit,
    )
    away_resp = table.query(
        IndexName="away-team-index",
        KeyConditionExpression=Key("away_team_id").eq(team_id),
        ScanIndexForward=False,
        Limit=limit,
    )

    seen: set[str] = set()
    games: list[dict] = []
    for item in home_resp.get("Items", []) + away_resp.get("Items", []):
        game_id = item["game_id"]
        if game_id not in seen:
            seen.add(game_id)
            games.append(_sanitize(item))

    games.sort(key=lambda x: x.get("game_date", ""), reverse=True)
    return games[:limit]
