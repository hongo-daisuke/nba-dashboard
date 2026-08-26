import boto3
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Attr

from config.settings import EnvironmentConfig
from services.dynamo_write_service import (
    recompute_player_stats,
    update_game_stats_team_id,
    upsert_game_stats,
    upsert_games,
    upsert_player_stats,
    upsert_players,
    upsert_standings,
    upsert_teams,
)
from services.nba_fetch_service import (
    fetch_game_stats,
    fetch_games,
    fetch_player_season_stats,
    fetch_players,
    fetch_standings,
    fetch_team_map_for_game,
    fetch_teams,
)

logger = Logger()

_dynamodb = boto3.resource("dynamodb")


def repair_box_scores(
    season: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """既存 GameStats レコードに ESPN 再取得で team_id を補完する（一回限りの修復用）。

    通常は 1 シーズンまるごと処理できる（0.1s スリープ × ~1200 ゲーム ≈ 600s）。
    タイムアウトした場合は start_date / end_date で半期に分割して実行する:
        {"mode": "repair_box_scores", "season": "2025-26", "start_date": "2025-10-01", "end_date": "2026-01-31"}
        {"mode": "repair_box_scores", "season": "2025-26", "start_date": "2026-02-01", "end_date": "2026-07-01"}
    """
    games_table = _dynamodb.Table(EnvironmentConfig.get_games_table())

    # 指定シーズンの Final ゲームをスキャン（日付範囲フィルタは任意）
    filter_expr = Attr("season").eq(season) & Attr("status").eq("Final")
    if start_date:
        filter_expr = filter_expr & Attr("game_date").gte(start_date)
    if end_date:
        filter_expr = filter_expr & Attr("game_date").lte(end_date)

    game_ids: list[str] = []
    response = games_table.scan(FilterExpression=filter_expr, ProjectionExpression="game_id")
    game_ids.extend(str(item["game_id"]) for item in response.get("Items", []))
    while "LastEvaluatedKey" in response:
        response = games_table.scan(
            FilterExpression=filter_expr,
            ProjectionExpression="game_id",
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        game_ids.extend(str(item["game_id"]) for item in response.get("Items", []))

    logger.info(
        "repair_box_scores 開始",
        extra={"season": season, "start_date": start_date, "end_date": end_date, "total_games": len(game_ids)},
    )

    total_updated = 0
    skipped = 0
    for i, game_id in enumerate(game_ids):
        try:
            team_map = fetch_team_map_for_game(game_id)
            updated = update_game_stats_team_id(game_id, team_map)
            total_updated += updated
        except Exception as exc:
            logger.warning("repair スキップ", extra={"game_id": game_id, "error": str(exc)})
            skipped += 1

        if (i + 1) % 100 == 0:
            logger.info(
                "repair 進捗",
                extra={"processed": i + 1, "total": len(game_ids), "updated_so_far": total_updated},
            )

    logger.info(
        "repair_box_scores 完了",
        extra={"season": season, "total_games": len(game_ids), "total_updated": total_updated, "skipped": skipped},
    )
    return {"season": season, "total_games": len(game_ids), "total_updated": total_updated, "skipped": skipped}


def run_batch(
    mode: str = "daily",
    start_date: str | None = None,
    end_date: str | None = None,
    skip_game_stats: bool = False,
) -> dict:
    """NBA データを取得して DynamoDB へ書き込むメイン処理。

    Args:
        mode: "daily" (直近4日間) または "backfill" (指定日程全件)
        start_date: backfill 時の開始日 (YYYY-MM-DD)
        end_date: backfill 時の終了日 (YYYY-MM-DD)
        skip_game_stats: True の場合はボックススコア取得をスキップする
    """
    season = EnvironmentConfig.get_nba_current_season()
    logger.info("バッチ開始", extra={"season": season, "mode": mode})

    # 1. チーム
    teams = fetch_teams(season=season)
    upsert_teams(teams)

    # 2. 選手（ロスター）
    players = fetch_players(all_teams=teams, season=season)
    upsert_players(players)

    # 3. 選手シーズン平均（ESPN に直接エンドポイントなし → 空リスト）
    stats = fetch_player_season_stats(season=season)
    upsert_player_stats(stats)

    # 4. 試合スコア
    games = fetch_games(season=season, mode=mode, start_date=start_date, end_date=end_date)
    upsert_games(games)

    # 5. ボックススコア（完了した試合のみ、skip_game_stats=True の場合はスキップ）
    if skip_game_stats:
        logger.info("ボックススコア取得スキップ (skip_game_stats=True)")
        game_stats = []
    else:
        game_stats = fetch_game_stats(games=games)
        upsert_game_stats(game_stats)
        # ゲームスタッツ書き込み後、PlayerStats を再集計してリーダーボードを高速化する
        recompute_player_stats(season=season)

    # 6. 順位表
    standings = fetch_standings(season=season)
    upsert_standings(standings)

    summary = {
        "teams": len(teams),
        "players": len(players),
        "games": len(games),
        "game_stats": len(game_stats),
        "standings": len(standings),
    }
    logger.info("バッチ完了", extra=summary)
    return summary
