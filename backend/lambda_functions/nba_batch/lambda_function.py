from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from handlers.batch_handler import repair_box_scores, run_batch
from services.dynamo_write_service import recompute_player_stats

logger = Logger()


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """EventBridge からの定期実行または手動トリガーに対応する。

    通常バッチ（毎日自動実行）:
        {} または {"mode": "daily"}

    手動 backfill（指定期間のデータ取得）:
        {"mode": "backfill", "start_date": "2025-10-01", "end_date": "2025-10-31"}

    PlayerStats のみ再計算（backfill 後や game_type 付与後に実行）:
        {"mode": "recompute", "season": "2025-26"}

    既存 GameStats への team_id 補完（一回限り・シーズンごとに実行）:
        {"mode": "repair_box_scores", "season": "2025-26"}
        {"mode": "repair_box_scores", "season": "2024-25"}
    """
    mode: str = event.get("mode", "daily")

    if mode == "repair_box_scores":
        season: str = event.get("season", "")
        if not season:
            raise ValueError("repair_box_scores モードでは season が必須です (例: '2025-26')")
        return repair_box_scores(
            season=season,
            start_date=event.get("start_date"),
            end_date=event.get("end_date"),
        )

    if mode == "recompute":
        season = event.get("season", "")
        if not season:
            raise ValueError("recompute モードでは season が必須です (例: '2025-26')")
        recompute_player_stats(season=season)
        return {"mode": "recompute", "season": season}

    start_date: str | None = event.get("start_date")
    end_date: str | None = event.get("end_date")
    skip_game_stats: bool = bool(event.get("skip_game_stats", False))
    return run_batch(mode=mode, start_date=start_date, end_date=end_date, skip_game_stats=skip_game_stats)
