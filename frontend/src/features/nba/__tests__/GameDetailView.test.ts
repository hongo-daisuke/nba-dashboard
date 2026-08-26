import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ElementPlus from 'element-plus'
import GameDetailView from '../views/GameDetailView.vue'
import { nbaService } from '../services/nbaService'
import type { GameDetail, GameStat } from '../types/nba'

vi.mock('vue-router', () => ({
  useRouter: () => ({ back: vi.fn() }),
  useRoute: () => ({ params: { gameId: 'game001' } }),
}))

vi.mock('../services/nbaService')

const makeStat = (
  playerId: string,
  playerName: string,
  teamId: string | undefined,
  points: number,
): GameStat => ({
  gameId: 'game001',
  playerId,
  teamId,
  gameDate: '2025-11-01',
  playerName,
  minutes: '32:00',
  points,
  rebounds: 5,
  offensiveRebounds: 1,
  defensiveRebounds: 4,
  assists: 3,
  steals: 1,
  blocks: 1,
  turnovers: 2,
  fouls: 2,
  plusMinus: 5,
  fgMade: 10,
  fgAttempted: 20,
  fg3Made: 2,
  fg3Attempted: 5,
  ftMade: 8,
  ftAttempted: 8,
})

const mockGame: GameDetail = {
  gameId: 'game001',
  gameDate: '2025-11-01',
  season: '2025-26',
  status: 'Final',
  homeTeamId: 'team1',
  homeTeamAbbreviation: 'LAL',
  homeScore: 110,
  awayTeamId: 'team2',
  awayTeamAbbreviation: 'BOS',
  awayScore: 105,
  boxScore: [
    makeStat('p1', 'LeBron James', 'team1', 30),
    makeStat('p2', 'Anthony Davis', 'team1', 22),
    makeStat('p3', 'Jayson Tatum', 'team2', 35),
    makeStat('p4', 'Jaylen Brown', 'team2', 25),
  ],
}

beforeEach(() => {
  vi.mocked(nbaService.getGameDetail).mockResolvedValue(mockGame)
})

describe('GameDetailView', () => {
  it('試合スコアが表示される', async () => {
    const wrapper = mount(GameDetailView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('LAL')
    expect(wrapper.text()).toContain('BOS')
    expect(wrapper.text()).toContain('110')
    expect(wrapper.text()).toContain('105')
  })

  it('HOME セクションヘッダーに homeTeam の略称が表示される', async () => {
    const wrapper = mount(GameDetailView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('HOME — LAL')
  })

  it('AWAY セクションヘッダーに awayTeam の略称が表示される', async () => {
    const wrapper = mount(GameDetailView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('AWAY — BOS')
  })

  it('HOME チームの選手が表示される', async () => {
    const wrapper = mount(GameDetailView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('LeBron James')
    expect(wrapper.text()).toContain('Anthony Davis')
  })

  it('AWAY チームの選手が表示される', async () => {
    const wrapper = mount(GameDetailView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('Jayson Tatum')
    expect(wrapper.text()).toContain('Jaylen Brown')
  })

  it('全選手に teamId がある場合「その他」セクションは表示されない', async () => {
    const wrapper = mount(GameDetailView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).not.toContain('その他')
  })

  it('teamId のない選手は「その他」セクションに表示される', async () => {
    vi.mocked(nbaService.getGameDetail).mockResolvedValueOnce({
      ...mockGame,
      boxScore: [
        ...mockGame.boxScore,
        makeStat('p5', 'Unknown Player', undefined, 10),
      ],
    })
    const wrapper = mount(GameDetailView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('その他')
    expect(wrapper.text()).toContain('Unknown Player')
  })

  it('API エラー時にエラーメッセージが表示される', async () => {
    vi.mocked(nbaService.getGameDetail).mockRejectedValueOnce(new Error('Network Error'))
    const wrapper = mount(GameDetailView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('取得に失敗しました')
  })

  it('homeScore > awayScore のとき Final ステータスが表示される', async () => {
    const wrapper = mount(GameDetailView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('Final')
  })
})
