import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ElementPlus from 'element-plus'
import StandingsView from '../views/StandingsView.vue'
import { nbaService } from '../services/nbaService'
import type { Standing } from '../types/nba'

vi.mock('../services/nbaService')

const makeStanding = (
  teamAbbreviation: string,
  conference: 'East' | 'West',
  seed: number,
  wins: number,
  losses: number,
): Standing => ({
  season: '2025-26',
  'conference#seed': `${conference}#${seed}`,
  teamId: `team-${teamAbbreviation}`,
  teamAbbreviation,
  wins,
  losses,
  winPct: (wins / (wins + losses)).toFixed(3),
  gamesBehind: seed === 1 ? '-' : String(seed - 1),
  conference,
  seed,
})

const mockStandings: Standing[] = [
  makeStanding('BOS', 'East', 1, 40, 10),
  makeStanding('MIL', 'East', 2, 35, 15),
  makeStanding('NYK', 'East', 3, 32, 18),
  makeStanding('OKC', 'West', 1, 42, 8),
  makeStanding('DEN', 'West', 2, 36, 14),
  makeStanding('LAL', 'West', 3, 30, 20),
]

beforeEach(() => {
  vi.mocked(nbaService.getStandings).mockResolvedValue({
    standings: mockStandings,
    total: mockStandings.length,
  })
})

describe('StandingsView', () => {
  it('順位表が表示される', async () => {
    const wrapper = mount(StandingsView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('順位表')
  })

  it('Eastern Conference のチームが表示される', async () => {
    const wrapper = mount(StandingsView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('BOS')
    expect(wrapper.text()).toContain('MIL')
    expect(wrapper.text()).toContain('NYK')
  })

  it('Western Conference のチームが表示される', async () => {
    const wrapper = mount(StandingsView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('OKC')
    expect(wrapper.text()).toContain('DEN')
    expect(wrapper.text()).toContain('LAL')
  })

  it('Eastern / Western の両カンファレンスヘッダーが表示される', async () => {
    const wrapper = mount(StandingsView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('Eastern Conference')
    expect(wrapper.text()).toContain('Western Conference')
  })

  it('シーズンが表示される', async () => {
    const wrapper = mount(StandingsView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('2025-26')
  })

  it('East チームが West テーブルに混入しない', async () => {
    const wrapper = mount(StandingsView, { global: { plugins: [ElementPlus] } })
    await flushPromises()

    // Western Conference の el-card を特定
    const cards = wrapper.findAll('.el-card')
    // Eastern が 0 番目、Western が 1 番目
    const westCard = cards[1]
    expect(westCard.text()).toContain('OKC')
    expect(westCard.text()).not.toContain('BOS')
  })

  it('API エラー時にエラーメッセージが表示される', async () => {
    vi.mocked(nbaService.getStandings).mockRejectedValueOnce(new Error('Network Error'))
    const wrapper = mount(StandingsView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('取得に失敗しました')
  })
})
