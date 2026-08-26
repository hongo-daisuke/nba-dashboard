import apiClient from '@/plugins/axios'
import type {
  GameDetail,
  GamesResponse,
  LeadersResponse,
  PlayerDetail,
  PlayerGameLog,
  PlayersResponse,
  StandingsResponse,
  TeamsResponse,
} from '../types/nba'

export const nbaService = {
  async getTeams(conference?: string): Promise<TeamsResponse> {
    const params = conference ? { conference } : {}
    const { data } = await apiClient.get<TeamsResponse>('/teams', { params })
    return data
  },

  async getTeam(teamId: string): Promise<PlayerDetail> {
    const { data } = await apiClient.get<PlayerDetail>(`/teams/${teamId}`)
    return data
  },

  async getPlayers(params?: { position?: string; teamId?: string }): Promise<PlayersResponse> {
    const { data } = await apiClient.get<PlayersResponse>('/players', { params })
    return data
  },

  async getPlayer(playerId: string): Promise<PlayerDetail> {
    const { data } = await apiClient.get<PlayerDetail>(`/players/${playerId}`)
    return data
  },

  async getPlayerGameLog(playerId: string, limit = 20): Promise<PlayerGameLog> {
    const { data } = await apiClient.get<PlayerGameLog>(`/players/${playerId}/game-log`, {
      params: { limit },
    })
    return data
  },

  async getGames(params?: { date?: string; teamId?: string }): Promise<GamesResponse> {
    const { data } = await apiClient.get<GamesResponse>('/games', { params })
    return data
  },

  async getGameDetail(gameId: string): Promise<GameDetail> {
    const { data } = await apiClient.get<GameDetail>(`/games/${gameId}`)
    return data
  },

  async getStandings(season?: string, conference?: string): Promise<StandingsResponse> {
    const params: Record<string, string> = {}
    if (season) params.season = season
    if (conference) params.conference = conference
    const { data } = await apiClient.get<StandingsResponse>('/standings', { params })
    return data
  },

  async getLeaders(category = 'points', limit = 20): Promise<LeadersResponse> {
    const { data } = await apiClient.get<LeadersResponse>('/leaders', {
      params: { category, limit },
    })
    return data
  },
}
