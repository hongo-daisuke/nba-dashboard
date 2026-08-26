import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from aws_lambda_powertools import Logger

from config.constants import ESPN_BASE_URL, ESPN_REQUEST_SLEEP_SEC, ESPN_STANDINGS_URL, TEAM_STATIC

logger = Logger()

_ET = ZoneInfo("America/New_York")


def _get(url: str, params: dict | None = None) -> dict:
    time.sleep(ESPN_REQUEST_SLEEP_SEC)
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()  # type: ignore[no-any-return]


def _resolve_dates(
    mode: str,
    start_date: str | None,
    end_date: str | None,
) -> list[str]:
    """バッチモードに応じて処理する日付リスト (YYYYMMDD) を返す。"""
    if mode == "backfill":
        if not start_date or not end_date:
            raise ValueError("backfill モードでは start_date と end_date が必須です")
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        dates: list[str] = []
        cur = start
        while cur <= end:
            dates.append(cur.strftime("%Y%m%d"))
            cur += timedelta(days=1)
        return dates
    else:
        # daily: ET 基準で直近4日間（深夜ゲームの取りこぼし防止）
        today_et = datetime.now(_ET).date()
        return [(today_et - timedelta(days=i)).strftime("%Y%m%d") for i in range(3, -1, -1)]


def fetch_teams(season: str) -> list[dict]:
    """全 30 チームの基本情報を取得する。"""
    logger.info("チームデータ取得中", extra={"season": season})
    data = _get(f"{ESPN_BASE_URL}/teams", {"limit": 100})
    raw_teams = data["sports"][0]["leagues"][0]["teams"]

    result: list[dict] = []
    for t in raw_teams:
        team = t["team"]
        abbr = team["abbreviation"]
        static = TEAM_STATIC.get(abbr, {})
        if not static:
            logger.warning("TEAM_STATIC に未登録の abbreviation", extra={"abbreviation": abbr, "full_name": team.get("displayName", "")})

        item: dict = {
            "team_id": str(team["id"]),
            "full_name": team["displayName"],
            "abbreviation": abbr,
            "nickname": team["name"],
            "city": team["location"],
            "year_founded": static.get("year_founded", 0),
        }
        # conference / division / state は GSI キーになりうるため、空文字を書かない
        for field in ("conference", "division", "state"):
            value = static.get(field, "")
            if value:
                item[field] = value

        result.append(item)

    logger.info("チームデータ取得完了", extra={"count": len(result)})
    return result


def fetch_players(all_teams: list[dict], season: str) -> list[dict]:
    """全チームのロスターを取得する。"""
    logger.info("選手データ取得中", extra={"season": season})
    result: list[dict] = []

    for i, team in enumerate(all_teams):
        logger.info("ロスター取得中", extra={"team": team["full_name"], "index": i + 1, "total": len(all_teams)})
        data = _get(f"{ESPN_BASE_URL}/teams/{team['team_id']}/roster")

        for athlete in data.get("athletes", []):
            pos = athlete.get("position") or {}
            result.append({
                "player_id": str(athlete["id"]),
                "name": athlete["displayName"],
                "jersey_number": str(athlete.get("jersey") or "N/A"),
                "position": str(pos.get("abbreviation") or "N/A"),
                "height": str(athlete.get("displayHeight") or "N/A"),
                "weight": str(athlete.get("displayWeight") or "N/A"),
                "age": int(athlete.get("age") or 0),
                "team_id": team["team_id"],
                "team_name": team["full_name"],
                "team_abbreviation": team["abbreviation"],
            })

    logger.info("選手データ取得完了", extra={"count": len(result)})
    return result


def fetch_player_season_stats(season: str) -> list[dict]:
    """ESPN に直接のシーズン平均エンドポイントがないため空リストを返す。
    PlayerStatsTable は GameStatsTable の積み上げ集計で別途実装予定。"""
    logger.info("選手シーズン平均: 今フェーズではスキップ", extra={"season": season})
    return []


def fetch_games(
    season: str,
    mode: str = "daily",
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """試合スコアを取得する。"""
    dates = _resolve_dates(mode, start_date, end_date)
    logger.info("試合結果取得中", extra={"mode": mode, "dates": len(dates)})

    result: list[dict] = []
    for date_str in dates:
        data = _get(f"{ESPN_BASE_URL}/scoreboard", {"dates": date_str})
        for event in data.get("events", []):
            comp = event["competitions"][0]
            competitors = comp.get("competitors", [])
            home = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away = next((c for c in competitors if c.get("homeAway") == "away"), {})
            status = comp.get("status", {}).get("type", {}).get("description", "")
            # "2026-01-18T17:00Z" → "2026-01-18"
            game_date = str(event.get("date", ""))[:10]

            # season.type: 2 = レギュラーシーズン, それ以外 = プレーイン/プレーオフ
            season_type = event.get("season", {}).get("type", 2)
            game_type = "regular" if season_type == 2 else "postseason"

            result.append({
                "game_date": game_date,
                "game_id": str(event["id"]),
                "season": season,
                "game_type": game_type,
                "status": "Final" if status == "Final" else status,
                "home_team_id": str(home.get("team", {}).get("id", "")),
                "home_team_abbreviation": str(home.get("team", {}).get("abbreviation", "")),
                "home_score": int(home.get("score") or 0),
                "away_team_id": str(away.get("team", {}).get("id", "")),
                "away_team_abbreviation": str(away.get("team", {}).get("abbreviation", "")),
                "away_score": int(away.get("score") or 0),
            })

    logger.info("試合結果取得完了", extra={"count": len(result)})
    return result


def fetch_game_stats(games: list[dict]) -> list[dict]:
    """完了した試合のボックススコアを取得する。"""
    final_games = [g for g in games if g["status"] == "Final"]
    logger.info("ボックススコア取得中", extra={"games": len(final_games)})

    result: list[dict] = []
    skipped = 0
    for game in final_games:
        game_id = game["game_id"]
        game_date = game["game_date"]

        try:
            data = _get(f"{ESPN_BASE_URL}/summary", {"event": game_id})
        except Exception as exc:
            logger.warning("ボックススコア取得スキップ", extra={"game_id": game_id, "error": str(exc)})
            skipped += 1
            continue
        players_data = data.get("boxscore", {}).get("players", [])

        for team_data in players_data:
            team_id = str(team_data.get("team", {}).get("id", ""))
            statistics = team_data.get("statistics", [])
            if not statistics:
                continue
            # statistics[0] がフルスタッツグループ。keys 配列から名前引きする
            stat_group = statistics[0]
            keys = stat_group.get("keys", [])
            seen_player_ids: set[str] = set()

            for athlete in stat_group.get("athletes", []):
                stats_arr = athlete.get("stats", [])
                # DNP 選手は空配列または先頭が '--'
                if not stats_arr or stats_arr[0] == "--":
                    continue
                athlete_obj = athlete.get("athlete", {})
                player_id = str(athlete_obj.get("id", ""))
                if player_id in seen_player_ids:
                    continue
                seen_player_ids.add(player_id)

                stats = dict(zip(keys, stats_arr))
                result.append(_parse_game_stat(game_id, game_date, team_id, athlete_obj, stats))

    logger.info("ボックススコア取得完了", extra={"count": len(result), "skipped": skipped})
    return result


def _parse_game_stat(
    game_id: str,
    game_date: str,
    team_id: str,
    athlete: dict,
    stats: dict[str, str],
) -> dict:
    def _int(key: str) -> int:
        try:
            return int(stats.get(key, "0"))
        except (ValueError, TypeError):
            return 0

    def _split(key: str) -> tuple[int, int]:
        """'7-20' → (7, 20)"""
        v = stats.get(key, "0-0")
        parts = str(v).split("-")
        if len(parts) == 2:
            try:
                return int(parts[0]), int(parts[1])
            except (ValueError, TypeError):
                pass
        return 0, 0

    fg_made, fg_att = _split("fieldGoalsMade-fieldGoalsAttempted")
    fg3_made, fg3_att = _split("threePointFieldGoalsMade-threePointFieldGoalsAttempted")
    ft_made, ft_att = _split("freeThrowsMade-freeThrowsAttempted")

    return {
        "game_id": game_id,
        "player_id": str(athlete.get("id", "")),
        "team_id": team_id,
        "game_date": game_date,
        "player_name": athlete.get("displayName", ""),
        "minutes": stats.get("minutes", "0"),
        "points": _int("points"),
        "rebounds": _int("rebounds"),
        "offensive_rebounds": _int("offensiveRebounds"),
        "defensive_rebounds": _int("defensiveRebounds"),
        "assists": _int("assists"),
        "steals": _int("steals"),
        "blocks": _int("blocks"),
        "turnovers": _int("turnovers"),
        "fouls": _int("fouls"),
        "plus_minus": _int("plusMinus"),
        "fg_made": fg_made,
        "fg_attempted": fg_att,
        "fg3_made": fg3_made,
        "fg3_attempted": fg3_att,
        "ft_made": ft_made,
        "ft_attempted": ft_att,
    }


def fetch_team_map_for_game(game_id: str) -> dict[str, str]:
    """repair_box_scores 用: 1 ゲーム分の player_id → team_id マップを ESPN から取得する。

    大量ゲームを連続処理するため 0.1s の短いスリープを使う。
    エラーは呼び出し元の try-except で吸収する。
    """
    time.sleep(0.1)
    resp = requests.get(f"{ESPN_BASE_URL}/summary", params={"event": game_id}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    team_map: dict[str, str] = {}
    for team_data in data.get("boxscore", {}).get("players", []):
        team_id = str(team_data.get("team", {}).get("id", ""))
        statistics = team_data.get("statistics", [])
        if not statistics or not team_id:
            continue
        for athlete in statistics[0].get("athletes", []):
            stats_arr = athlete.get("stats", [])
            if not stats_arr or stats_arr[0] == "--":
                continue
            player_id = str(athlete.get("athlete", {}).get("id", ""))
            if player_id:
                team_map[player_id] = team_id
    return team_map


def fetch_standings(season: str) -> list[dict]:
    """カンファレンス順位表を取得する。"""
    logger.info("順位表取得中", extra={"season": season})
    data = _get(ESPN_STANDINGS_URL)

    result: list[dict] = []
    for conf in data.get("children", []):
        conf_name = str(conf.get("name", ""))
        conference = "East" if "Eastern" in conf_name else "West"
        entries = conf.get("standings", {}).get("entries", [])

        for entry in entries:
            team = entry.get("team", {})
            stats = {s["name"]: s["displayValue"] for s in entry.get("stats", [])}
            seed_str = stats.get("playoffSeed", "0")
            seed = int(seed_str) if str(seed_str).isdigit() else 0

            result.append({
                "season": season,
                "conference#seed": f"{conference}#{seed:02d}",
                "team_id": str(team.get("id", "")),
                "team_abbreviation": str(team.get("abbreviation", "")),
                "wins": int(stats.get("wins", 0) or 0),
                "losses": int(stats.get("losses", 0) or 0),
                "win_pct": str(stats.get("winPercent", "0")),
                "games_behind": str(stats.get("gamesBehind", "-")),
                "conference": conference,
                "seed": seed,
            })

    logger.info("順位表取得完了", extra={"count": len(result)})
    return result
