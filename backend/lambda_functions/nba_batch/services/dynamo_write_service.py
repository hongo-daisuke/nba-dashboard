from decimal import Decimal

import boto3
from aws_lambda_powertools import Logger

from config.settings import EnvironmentConfig

logger = Logger()

_dynamodb = boto3.resource("dynamodb")


def _table(name: str):  # type: ignore[return]
    return _dynamodb.Table(name)


def upsert_teams(teams: list[dict]) -> None:
    """チームデータを一括書き込みする。"""
    table = _table(EnvironmentConfig.get_teams_table())
    with table.batch_writer() as batch:
        for team in teams:
            batch.put_item(Item=team)
    logger.info("チーム書き込み完了", extra={"count": len(teams)})


def upsert_players(players: list[dict]) -> None:
    """選手データを一括書き込みする。"""
    table = _table(EnvironmentConfig.get_players_table())
    with table.batch_writer() as batch:
        for player in players:
            batch.put_item(Item=player)
    logger.info("選手書き込み完了", extra={"count": len(players)})


def upsert_player_stats(stats: list[dict]) -> None:
    """選手シーズン平均スタッツを一括書き込みする。"""
    if not stats:
        return
    table = _table(EnvironmentConfig.get_player_stats_table())
    with table.batch_writer() as batch:
        for stat in stats:
            batch.put_item(Item=stat)
    logger.info("スタッツ書き込み完了", extra={"count": len(stats)})


def upsert_games(games: list[dict]) -> None:
    """試合データを一括書き込みする。"""
    table = _table(EnvironmentConfig.get_games_table())
    with table.batch_writer() as batch:
        for game in games:
            batch.put_item(Item=game)
    logger.info("試合書き込み完了", extra={"count": len(games)})


def upsert_game_stats(game_stats: list[dict]) -> None:
    """試合ごとの選手スタッツ（ボックススコア）を一括書き込みする。"""
    if not game_stats:
        return
    table = _table(EnvironmentConfig.get_game_stats_table())
    with table.batch_writer() as batch:
        for stat in game_stats:
            batch.put_item(Item=stat)
    logger.info("ボックススコア書き込み完了", extra={"count": len(game_stats)})


def upsert_standings(standings: list[dict]) -> None:
    """順位表を一括書き込みする。"""
    if not standings:
        return
    table = _table(EnvironmentConfig.get_standings_table())
    with table.batch_writer() as batch:
        for standing in standings:
            batch.put_item(Item=standing)
    logger.info("順位表書き込み完了", extra={"count": len(standings)})


def update_game_stats_team_id(game_id: str, team_map: dict[str, str]) -> int:
    """指定ゲームの GameStats レコードに team_id を書き込む（repair_box_scores から呼ばれる）。

    Args:
        game_id: 対象ゲーム ID
        team_map: {player_id: team_id} のマッピング（ESPN 取得済み）
    Returns:
        更新したレコード数
    """
    from boto3.dynamodb.conditions import Key  # ローカルインポートで循環回避

    table = _table(EnvironmentConfig.get_game_stats_table())
    response = table.query(KeyConditionExpression=Key("game_id").eq(game_id))
    items = response.get("Items", [])

    updated = 0
    with table.batch_writer() as batch:
        for item in items:
            player_id = str(item.get("player_id", ""))
            team_id = team_map.get(player_id)
            if team_id:
                item["team_id"] = team_id
                batch.put_item(Item=item)
                updated += 1
    return updated


def recompute_player_stats(season: str) -> None:
    """GameStats を集計して PlayerStats テーブルへ書き込む。

    GameStats には season フィールドがないため game_date の範囲で対象シーズンを特定する。
    例: "2025-26" → 2025-10-01 〜 2026-07-01
    レギュラーシーズンのみ集計する（プレーイン・プレーオフは除外）。
    """
    year_start = int(season.split("-")[0])
    date_from = f"{year_start}-10-01"
    date_to = f"{year_start + 1}-07-01"

    from boto3.dynamodb.conditions import Attr  # ローカルインポートで循環回避

    # Games テーブルから game_id → game_type マップを構築
    games_table = _table(EnvironmentConfig.get_games_table())
    game_type_map: dict[str, str] = {}
    response = games_table.scan(
        FilterExpression=Attr("game_date").gte(date_from) & Attr("game_date").lt(date_to),
        ProjectionExpression="game_id, game_type",
    )
    for item in response.get("Items", []):
        gid = str(item.get("game_id", ""))
        if gid:
            game_type_map[gid] = str(item.get("game_type", "regular"))
    while "LastEvaluatedKey" in response:
        response = games_table.scan(
            FilterExpression=Attr("game_date").gte(date_from) & Attr("game_date").lt(date_to),
            ProjectionExpression="game_id, game_type",
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        for item in response.get("Items", []):
            gid = str(item.get("game_id", ""))
            if gid:
                game_type_map[gid] = str(item.get("game_type", "regular"))

    logger.info("Games テーブル読み込み完了", extra={"season": season, "games": len(game_type_map)})

    game_stats_table = _table(EnvironmentConfig.get_game_stats_table())
    logger.info("PlayerStats 再計算開始", extra={"season": season, "date_from": date_from, "date_to": date_to})

    # GameStats を全件スキャン（game_date でフィルタ）
    items: list[dict] = []
    response = game_stats_table.scan(
        FilterExpression=Attr("game_date").gte(date_from) & Attr("game_date").lt(date_to),
    )
    items.extend(response.get("Items", []))
    while "LastEvaluatedKey" in response:
        response = game_stats_table.scan(
            FilterExpression=Attr("game_date").gte(date_from) & Attr("game_date").lt(date_to),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    logger.info("GameStats スキャン完了", extra={"count": len(items)})

    # 選手単位で集計（レギュラーシーズンのみ）
    aggregated: dict[str, dict] = {}
    for stat in items:
        game_id = str(stat.get("game_id", ""))
        # games テーブルに game_type がある場合のみ除外判定。ない場合は regular 扱い
        if game_type_map.get(game_id, "regular") != "regular":
            continue
        pid = str(stat.get("player_id", ""))
        if not pid:
            continue
        if pid not in aggregated:
            aggregated[pid] = {
                "player_id": pid,
                "season": season,
                "player_name": stat.get("player_name", ""),
                "games_played": 0,
                "points": 0,
                "rebounds": 0,
                "assists": 0,
                "steals": 0,
                "blocks": 0,
                "turnovers": 0,
                "fg_made": 0,
                "fg_attempted": 0,
                "fg3_made": 0,
                "fg3_attempted": 0,
                "ft_made": 0,
                "ft_attempted": 0,
            }
        agg = aggregated[pid]
        agg["games_played"] += 1
        for key in ("points", "rebounds", "assists", "steals", "blocks", "turnovers"):
            agg[key] += int(stat.get(key, 0) or 0)
        for key in ("fg_made", "fg_attempted", "fg3_made", "fg3_attempted", "ft_made", "ft_attempted"):
            agg[key] += int(stat.get(key, 0) or 0)

    # 割合を計算して Decimal 変換（DynamoDB に float は書き込めない）
    player_stats_table = _table(EnvironmentConfig.get_player_stats_table())
    records: list[dict] = []
    for agg in aggregated.values():
        fa = agg["fg_attempted"]
        f3a = agg["fg3_attempted"]
        fta = agg["ft_attempted"]
        record = {
            "player_id": agg["player_id"],
            "season": agg["season"],
            "player_name": agg["player_name"],
            "games_played": Decimal(agg["games_played"]),
            "points": Decimal(agg["points"]),
            "rebounds": Decimal(agg["rebounds"]),
            "assists": Decimal(agg["assists"]),
            "steals": Decimal(agg["steals"]),
            "blocks": Decimal(agg["blocks"]),
            "turnovers": Decimal(agg["turnovers"]),
            "fg_made": Decimal(agg["fg_made"]),
            "fg_attempted": Decimal(fa),
            "fg3_made": Decimal(agg["fg3_made"]),
            "fg3_attempted": Decimal(f3a),
            "ft_made": Decimal(agg["ft_made"]),
            "ft_attempted": Decimal(fta),
            "fg_pct": Decimal(str(round(agg["fg_made"] / fa * 100, 1))) if fa else Decimal("0"),
            "fg3_pct": Decimal(str(round(agg["fg3_made"] / f3a * 100, 1))) if f3a else Decimal("0"),
            "ft_pct": Decimal(str(round(agg["ft_made"] / fta * 100, 1))) if fta else Decimal("0"),
        }
        records.append(record)

    with player_stats_table.batch_writer() as batch:
        for record in records:
            batch.put_item(Item=record)

    logger.info("PlayerStats 再計算完了", extra={"season": season, "players": len(records)})
