import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ElementPlus from 'element-plus'
import GamesView from '../views/GamesView.vue'
import { nbaService } from '../services/nbaService'
import type { Game } from '../types/nba'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('../services/nbaService')

const makeGame = (
  gameId: string,
  homeAbbr: string,
  awayAbbr: string,
  homeScore: number,
  awayScore: number,
  status = 'Final',
): Game => ({
  gameId,
  gameDate: '2025-11-01',
  season: '2025-26',
  status,
  homeTeamId: `team-${homeAbbr}`,
  homeTeamAbbreviation: homeAbbr,
  homeScore,
  awayTeamId: `team-${awayAbbr}`,
  awayTeamAbbreviation: awayAbbr,
  awayScore,
})

const mockGames: Game[] = [
  makeGame('g001', 'LAL', 'BOS', 110, 105),
  makeGame('g002', 'GSW', 'MIA', 120, 98),
  makeGame('g003', 'NYK', 'CHI', 95, 100),
]

beforeEach(() => {
  vi.mocked(nbaService.getGames).mockResolvedValue({
    games: mockGames,
    total: mockGames.length,
  })
})

describe('GamesView', () => {
  it('試合一覧が表示される', async () => {
    const wrapper = mount(GamesView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('LAL')
    expect(wrapper.text()).toContain('BOS')
    expect(wrapper.text()).toContain('GSW')
  })

  it('試合数が表示される', async () => {
    const wrapper = mount(GamesView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('3 試合')
  })

  it('スコアが表示される', async () => {
    const wrapper = mount(GamesView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('110')
    expect(wrapper.text()).toContain('105')
  })

  it('Final ステータスが表示される', async () => {
    const wrapper = mount(GamesView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('Final')
  })

  it('試合データがない場合に空状態が表示される', async () => {
    vi.mocked(nbaService.getGames).mockResolvedValueOnce({ games: [], total: 0 })
    const wrapper = mount(GamesView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('試合データがありません')
  })

  it('API エラー時にエラーメッセージが表示される', async () => {
    vi.mocked(nbaService.getGames).mockRejectedValueOnce(new Error('Network Error'))
    const wrapper = mount(GamesView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('取得に失敗しました')
  })
})
