import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ElementPlus from 'element-plus'
import TeamsView from '../views/TeamsView.vue'
import { nbaService } from '../services/nbaService'

vi.mock('../services/nbaService')

const mockTeams = [
  { teamId: '1610612747', fullName: 'Los Angeles Lakers', abbreviation: 'LAL', nickname: 'Lakers', city: 'Los Angeles', state: 'California', yearFounded: 1948, conference: 'West', division: 'Pacific' },
  { teamId: '1610612738', fullName: 'Boston Celtics', abbreviation: 'BOS', nickname: 'Celtics', city: 'Boston', state: 'Massachusetts', yearFounded: 1946, conference: 'East', division: 'Atlantic' },
]

beforeEach(() => {
  vi.mocked(nbaService.getTeams).mockResolvedValue({ teams: mockTeams, total: mockTeams.length })
})

describe('TeamsView', () => {
  it('チーム一覧が表示される', async () => {
    const wrapper = mount(TeamsView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    const cards = wrapper.findAll('.el-card')
    expect(cards).toHaveLength(2)
  })

  it('Lakers が表示されている', async () => {
    const wrapper = mount(TeamsView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('Los Angeles Lakers')
  })

  it('創設年が表示されている', async () => {
    const wrapper = mount(TeamsView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('1948年創設')
  })

  it('API エラー時にエラーメッセージが表示される', async () => {
    vi.mocked(nbaService.getTeams).mockRejectedValueOnce(new Error('Network Error'))
    const wrapper = mount(TeamsView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('取得に失敗しました')
  })
})
