// DynamoDB / ESPN 由来のデータ構造
// axios インターセプターが snake_case → camelCase に自動変換する

export interface Team {
  teamId: string
  fullName: string
  abbreviation: string
  nickname: string
  city: string
  state: string
  yearFounded: number
  conference: string
  division: string
}

export interface Player {
  playerId: string
  name: string
  jerseyNumber: string
  position: string
  height: string
  weight: string
  age: number
  teamId: string
  teamName: string
  teamAbbreviation: string
}

export interface PlayerSeasonStats {
  playerId: string
  season: string
  playerName: string
  teamId: string
  teamAbbreviation: string
  gamesPlayed: number
  minutes: number
  points: number
  rebounds: number
  assists: number
  steals: number
  blocks: number
  turnovers: number
  fgPct: number
  fg3Pct: number
  ftPct: number
}

export interface PlayerDetail extends Player {
  stats: PlayerSeasonStats | null
}

export interface Game {
  gameId: string
  gameDate: string
  season: string
  status: string
  homeTeamId: string
  homeTeamAbbreviation: string
  homeScore: number
  awayTeamId: string
  awayTeamAbbreviation: string
  awayScore: number
}

export interface GameStat {
  gameId: string
  playerId: string
  teamId?: string
  gameDate: string
  playerName: string
  minutes: string
  points: number
  rebounds: number
  offensiveRebounds: number
  defensiveRebounds: number
  assists: number
  steals: number
  blocks: number
  turnovers: number
  fouls: number
  plusMinus: number
  fgMade: number
  fgAttempted: number
  fg3Made: number
  fg3Attempted: number
  ftMade: number
  ftAttempted: number
}

export interface GameDetail extends Game {
  boxScore: GameStat[]
}

export interface Standing {
  season: string
  'conference#seed': string
  teamId: string
  teamAbbreviation: string
  wins: number
  losses: number
  winPct: string
  gamesBehind: string
  conference: string
  seed: number
}

export interface Leader {
  playerId: string
  playerName: string
  gamesPlayed: number
  points: number
  rebounds: number
  assists: number
  steals: number
  blocks: number
  avgPoints: number
  avgRebounds: number
  avgAssists: number
  avgSteals: number
  avgBlocks: number
  fgPct: number
  fg3Pct: number
  ftPct: number
}

export interface PlayerGameLog {
  gameLog: GameStat[]
  total: number
}

export interface TeamsResponse {
  teams: Team[]
  total: number
}

export interface PlayersResponse {
  players: Player[]
  total: number
}

export interface GamesResponse {
  games: Game[]
  total: number
}

export interface StandingsResponse {
  standings: Standing[]
  total: number
}

export interface LeadersResponse {
  leaders: Leader[]
  category: string
  total: number
}
