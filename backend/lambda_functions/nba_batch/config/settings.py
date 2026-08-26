import os


class EnvironmentConfig:
    """環境変数を集約管理するクラス。

    すべての環境変数アクセスはこのクラス経由で行うこと。
    デフォルト値は設定しない (Fail-Fast)。
    """

    @staticmethod
    def get_teams_table() -> str:
        """Teams DynamoDB テーブル名を返す。"""
        return os.environ["TEAMS_TABLE"]

    @staticmethod
    def get_players_table() -> str:
        """Players DynamoDB テーブル名を返す。"""
        return os.environ["PLAYERS_TABLE"]

    @staticmethod
    def get_player_stats_table() -> str:
        """PlayerStats DynamoDB テーブル名を返す。"""
        return os.environ["PLAYER_STATS_TABLE"]

    @staticmethod
    def get_games_table() -> str:
        """Games DynamoDB テーブル名を返す。"""
        return os.environ["GAMES_TABLE"]

    @staticmethod
    def get_game_stats_table() -> str:
        """GameStats DynamoDB テーブル名を返す。"""
        return os.environ["GAME_STATS_TABLE"]

    @staticmethod
    def get_standings_table() -> str:
        """Standings DynamoDB テーブル名を返す。"""
        return os.environ["STANDINGS_TABLE"]

    @staticmethod
    def get_nba_current_season() -> str:
        """NBA カレントシーズン識別子を返す (例: '2024-25')。"""
        return os.environ["NBA_CURRENT_SEASON"]
