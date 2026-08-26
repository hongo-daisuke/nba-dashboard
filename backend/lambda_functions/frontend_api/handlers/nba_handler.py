from aws_lambda_powertools.event_handler.exceptions import NotFoundError
from aws_lambda_powertools.event_handler.router import APIGatewayRouter
from config.settings import EnvironmentConfig
from services.nba_service import NbaService

router = APIGatewayRouter()
_service = NbaService()


@router.get("/teams")
def get_teams() -> dict:
    conference = router.current_event.get_query_string_value(name="conference")
    return _service.get_teams(conference=conference)


@router.get("/teams/<team_id>")
def get_team(team_id: str) -> dict:
    team = _service.get_team(team_id=team_id)
    if team is None:
        raise NotFoundError(f"Team {team_id} not found")
    return team


@router.get("/players")
def get_players() -> dict:
    position = router.current_event.get_query_string_value(name="position")
    team_id = router.current_event.get_query_string_value(name="team_id")
    return _service.get_players(position=position, team_id=team_id)


@router.get("/players/<player_id>")
def get_player(player_id: str) -> dict:
    player = _service.get_player(player_id=player_id)
    if player is None:
        raise NotFoundError(f"Player {player_id} not found")
    return player


@router.get("/players/<player_id>/game-log")
def get_player_game_log(player_id: str) -> dict:
    limit_str = router.current_event.get_query_string_value(name="limit") or "20"
    limit = int(limit_str) if limit_str.isdigit() else 20
    return _service.get_player_game_log(player_id=player_id, limit=limit)


@router.get("/games")
def get_games() -> dict:
    game_date = router.current_event.get_query_string_value(name="date")
    team_id = router.current_event.get_query_string_value(name="team_id")
    return _service.get_games(game_date=game_date, team_id=team_id)


@router.get("/games/<game_id>")
def get_game_detail(game_id: str) -> dict:
    game = _service.get_game_detail(game_id=game_id)
    if game is None:
        raise NotFoundError(f"Game {game_id} not found")
    return game


@router.get("/standings")
def get_standings() -> dict:
    season = router.current_event.get_query_string_value(name="season") or EnvironmentConfig.get_nba_current_season()
    conference = router.current_event.get_query_string_value(name="conference")
    return _service.get_standings(season=season, conference=conference)


@router.get("/leaders")
def get_leaders() -> dict:
    category = router.current_event.get_query_string_value(name="category") or "points"
    limit_str = router.current_event.get_query_string_value(name="limit") or "20"
    limit = int(limit_str) if limit_str.isdigit() else 20
    season = router.current_event.get_query_string_value(name="season") or EnvironmentConfig.get_nba_current_season()
    return _service.get_leaders(category=category, limit=limit, season=season)
