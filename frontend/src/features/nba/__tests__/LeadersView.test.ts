import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ElementPlus from 'element-plus'
import LeadersView from '../views/LeadersView.vue'
import { nbaService } from '../services/nbaService'
import type { Leader } from '../types/nba'

vi.mock('../services/nbaService')

const makeLeader = (playerId: string, playerName: string, avgPoints: number): Leader => ({
  playerId,
  playerName,
  gamesPlayed: 50,
  points: avgPoints * 50,
  rebounds: 400,
  assists: 300,
  steals: 80,
  blocks: 50,
  avgPoints,
  avgRebounds: 8.0,
  avgAssists: 6.0,
  avgSteals: 1.5,
  avgBlocks: 1.0,
  fgPct: 52.3,
  fg3Pct: 35.1,
  ftPct: 80.0,
})

const mockLeaders: Leader[] = [
  makeLeader('p1', 'LeBron James', 30.0),
  makeLeader('p2', 'Kevin Durant', 29.2),
]

beforeEach(() => {
  vi.mocked(nbaService.getLeaders).mockResolvedValue({
    leaders: mockLeaders,
    category: 'points',
    total: mockLeaders.length,
  })
})

describe('LeadersView', () => {
  it('リーダーボードが表示される', async () => {
    const wrapper = mount(LeadersView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('LeBron James')
    expect(wrapper.text()).toContain('Kevin Durant')
  })

  it('初回ロードで points カテゴリが取得される', async () => {
    mount(LeadersView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(vi.mocked(nbaService.getLeaders)).toHaveBeenCalledWith('points', 30)
  })

  it('得点タブが初期選択されている', async () => {
    const wrapper = mount(LeadersView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('得点')
  })

  it('平均得点が表示される', async () => {
    const wrapper = mount(LeadersView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('30')
  })

  it('FG% カラムが得点タブで表示される', async () => {
    const wrapper = mount(LeadersView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('FG%')
  })

  it('API エラー時にエラーメッセージが表示される', async () => {
    vi.mocked(nbaService.getLeaders).mockRejectedValueOnce(new Error('Network Error'))
    const wrapper = mount(LeadersView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('取得に失敗しました')
  })

  it('リバウンドタブをクリックすると rebounds カテゴリで再取得される', async () => {
    vi.mocked(nbaService.getLeaders).mockResolvedValue({
      leaders: [makeLeader('p1', 'Nikola Jokic', 12.5)],
      category: 'rebounds',
      total: 1,
    })

    const wrapper = mount(LeadersView, { global: { plugins: [ElementPlus] } })
    await flushPromises()

    const tabItems = wrapper.findAll('.el-tabs__item')
    const reboundsTab = tabItems.find((t) => t.text().includes('リバウンド'))
    if (reboundsTab) {
      await reboundsTab.trigger('click')
      await flushPromises()
    }

    expect(vi.mocked(nbaService.getLeaders)).toHaveBeenCalledWith('rebounds', 30)
  })
})
