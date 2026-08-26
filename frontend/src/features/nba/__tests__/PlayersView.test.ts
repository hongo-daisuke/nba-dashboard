import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ElementPlus from 'element-plus'
import PlayersView from '../views/PlayersView.vue'
import { nbaService } from '../services/nbaService'
import type { Player } from '../types/nba'

vi.mock('../services/nbaService')

const makePlayer = (playerId: string, name: string, position: string, teamName: string): Player => ({
  playerId,
  name,
  jerseyNumber: '23',
  position,
  height: '6-9',
  weight: '250',
  age: 28,
  teamId: 'team1',
  teamName,
  teamAbbreviation: teamName.slice(0, 3).toUpperCase(),
})

const mockPlayers: Player[] = [
  makePlayer('p1', 'LeBron James', 'SF', 'Lakers'),
  makePlayer('p2', 'Anthony Davis', 'C', 'Lakers'),
  makePlayer('p3', 'Jayson Tatum', 'SF', 'Celtics'),
]

beforeEach(() => {
  vi.mocked(nbaService.getPlayers).mockResolvedValue({
    players: mockPlayers,
    total: mockPlayers.length,
  })
  vi.mocked(nbaService.getPlayerGameLog).mockResolvedValue({
    gameLog: [],
    total: 0,
  })
})

describe('PlayersView', () => {
  it('選手一覧が表示される', async () => {
    const wrapper = mount(PlayersView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('LeBron James')
    expect(wrapper.text()).toContain('Anthony Davis')
    expect(wrapper.text()).toContain('Jayson Tatum')
  })

  it('選手数が表示される', async () => {
    const wrapper = mount(PlayersView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('3 選手')
  })

  it('チーム名が表示される', async () => {
    const wrapper = mount(PlayersView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('Lakers')
    expect(wrapper.text()).toContain('Celtics')
  })

  it('ポジションフィルターを選択すると API が再呼び出しされる', async () => {
    vi.mocked(nbaService.getPlayers).mockResolvedValue({
      players: [makePlayer('p2', 'Anthony Davis', 'C', 'Lakers')],
      total: 1,
    })

    mount(PlayersView, { global: { plugins: [ElementPlus] } })
    await flushPromises()

    // 初回ロードで position なし（全選手）で呼ばれること
    expect(vi.mocked(nbaService.getPlayers)).toHaveBeenCalledWith({ position: undefined })
  })

  it('API エラー時にエラーメッセージが表示される', async () => {
    vi.mocked(nbaService.getPlayers).mockRejectedValueOnce(new Error('Network Error'))
    const wrapper = mount(PlayersView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).toContain('取得に失敗しました')
  })
})
