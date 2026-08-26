import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ElementPlus from 'element-plus'
import PlayerDetailView from '../views/PlayerDetailView.vue'
import { nbaService } from '../services/nbaService'
import type { PlayerDetail, GameStat } from '../types/nba'

vi.mock('vue-router', () => ({
  useRouter: () => ({ back: vi.fn() }),
  useRoute: () => ({ params: { playerId: 'p1' } }),
}))

vi.mock('../services/nbaService')

const mockPlayer: PlayerDetail = {
  playerId: 'p1',
  name: 'LeBron James',
  jerseyNumber: '23',
  position: 'SF',
  height: '6-9',
  weight: '250',
  age: 38,
  teamId: 'team-lal',
  teamName: 'Lakers',
  teamAbbreviation: 'LAL',
  stats: {
    playerId: 'p1',
    season: '2024-25',
    playerName: 'LeBron James',
    teamId: 'team-lal',
    teamAbbreviation: 'LAL',
    gamesPlayed: 71,
    minutes: 2200,
    points: 1820,
    rebounds: 567,
    assists: 695,
    steals: 78,
    blocks: 45,
    turnovers: 250,
    fgPct: 0.54,
    fg3Pct: 0.41,
    ftPct: 0.75,
  },
}

const mockGameStat: GameStat = {
  gameId: 'g1',
  playerId: 'p1',
  gameDate: '2025-11-01',
  playerName: 'LeBron James',
  minutes: '35',
  points: 28,
  rebounds: 8,
  offensiveRebounds: 2,
  defensiveRebounds: 6,
  assists: 10,
  steals: 1,
  blocks: 1,
  turnovers: 3,
  fouls: 2,
  plusMinus: 12,
  fgMade: 11,
  fgAttempted: 20,
  fg3Made: 2,
  fg3Attempted: 5,
  ftMade: 4,
  ftAttempted: 5,
}

beforeEach(() => {
  vi.mocked(nbaService.getPlayer).mockResolvedValue(mockPlayer)
  vi.mocked(nbaService.getPlayerGameLog).mockResolvedValue({
    gameLog: [mockGameStat],
    total: 1,
  })
})

describe('PlayerDetailView', () => {
  it('選手名が表示される', async () => {
    const wrapper = mount(PlayerDetailView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('LeBron James')
  })

  it('チーム名とポジションが表示される', async () => {
    const wrapper = mount(PlayerDetailView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('Lakers')
    expect(wrapper.text()).toContain('SF')
  })

  it('平均スタッツが表示される', async () => {
    const wrapper = mount(PlayerDetailView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('2024-25')
    expect(wrapper.text()).toContain('71 試合')
    expect(wrapper.text()).toContain('PTS')
    expect(wrapper.text()).toContain('REB')
    expect(wrapper.text()).toContain('AST')
    // 1820 / 71 = 25.6
    expect(wrapper.text()).toContain('25.6')
  })

  it('ゲームログが表示される', async () => {
    const wrapper = mount(PlayerDetailView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('2025-11-01')
    expect(wrapper.text()).toContain('28')
  })

  it('stats が null の場合シーズンスタッツカードが表示されない', async () => {
    vi.mocked(nbaService.getPlayer).mockResolvedValueOnce({ ...mockPlayer, stats: null })
    const wrapper = mount(PlayerDetailView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).not.toContain('シーズンスタッツ')
  })

  it('API エラー時にエラーメッセージが表示される', async () => {
    vi.mocked(nbaService.getPlayer).mockRejectedValueOnce(new Error('Network Error'))
    const wrapper = mount(PlayerDetailView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('取得に失敗しました')
  })
})
