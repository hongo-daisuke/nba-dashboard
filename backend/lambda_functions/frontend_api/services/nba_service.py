from typing import Optional

from repositories import (
    game_stats_repository,
    games_repository,
    players_repository,
    standings_repository,
    teams_repository,
)

_LEADER_CATEGORIES = frozenset({"points", "rebounds", "assists", "steals", "blocks"})


class NbaService:
    def get_teams(self, conference: Optional[str] = None) -> dict:
        teams = teams_repository.find_all(conference=conference)
        return {"teams": teams, "total": len(teams)}

    def get_team(self, team_id: str) -> Optional[dict]:
        return teams_repository.find_by_id(team_id)

    def get_players(self, position: Optional[str] = None, team_id: Optional[str] = None) -> dict:
        players = players_repository.find_all(position=position, team_id=team_id)
        return {"players": players, "total": len(players)}

    def get_player(self, player_id: str) -> Optional[dict]:
        player = players_repository.find_by_id(player_id)
        if player is None:
            return None
        stats = players_repository.find_stats(player_id=player_id)
        return {**player, "stats": stats}

    def get_games(self, game_date: Optional[str] = None, team_id: Optional[str] = None) -> dict:
        if game_date:
            games = games_repository.find_by_date(game_date)
        elif team_id:
            games = games_repository.find_by_team(team_id)
        else:
            games = games_repository.find_recent()
        return {"games": games, "total": len(games)}

    def get_game_detail(self, game_id: str) -> Optional[dict]:
        """試合詳細とボックススコアを返す。"""
        game = games_repository.find_by_id(game_id)
        if game is None:
            return None
        box_score = game_stats_repository.find_by_game(game_id)
        return {**game, "box_score": box_score}

    def get_standings(self, season: str, conference: Optional[str] = None) -> dict:
        """シーズン順位表を返す。"""
        standings = standings_repository.find_by_season(season=season, conference=conference)
        return {"standings": standings, "total": len(standings)}

    def get_leaders(self, category: str, limit: int = 20, season: str = "") -> dict:
        """スタッツリーダーボードを返す。

        バッチが事前集計した PlayerStats テーブルを参照するため高速に応答できる。
        """
        if category not in _LEADER_CATEGORIES:
            category = "points"

        all_stats = players_repository.find_all_stats(season=season)

        leaders = []
        for stat in all_stats:
            gp = int(stat.get("games_played", 0)) or 1
            leaders.append({
                "player_id": stat.get("player_id", ""),
                "player_name": stat.get("player_name", ""),
                "games_played": gp,
                "points": stat.get("points", 0),
                "rebounds": stat.get("rebounds", 0),
                "assists": stat.get("assists", 0),
                "steals": stat.get("steals", 0),
                "blocks": stat.get("blocks", 0),
                "avg_points": round(float(stat.get("points", 0)) / gp, 1),
                "avg_rebounds": round(float(stat.get("rebounds", 0)) / gp, 1),
                "avg_assists": round(float(stat.get("assists", 0)) / gp, 1),
                "avg_steals": round(float(stat.get("steals", 0)) / gp, 1),
                "avg_blocks": round(float(stat.get("blocks", 0)) / gp, 1),
                "fg_pct": float(stat.get("fg_pct", 0)),
                "fg3_pct": float(stat.get("fg3_pct", 0)),
                "ft_pct": float(stat.get("ft_pct", 0)),
            })

        leaders.sort(key=lambda x: x.get(f"avg_{category}", 0), reverse=True)
        return {"leaders": leaders[:limit], "category": category, "total": len(leaders)}

    def get_player_game_log(self, player_id: str, limit: int = 20) -> dict:
        """選手のゲームログ（直近N試合）を返す。"""
        game_log = game_stats_repository.find_by_player(player_id=player_id, limit=limit)
        return {"game_log": game_log, "total": len(game_log)}
