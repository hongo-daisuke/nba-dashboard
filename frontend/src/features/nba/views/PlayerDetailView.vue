<template>
  <div>
    <div style="margin-bottom: 20px;">
      <el-button @click="router.back()">← 選手一覧へ</el-button>
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      style="margin-bottom: 16px;"
    />

    <el-skeleton v-if="loading" :rows="8" animated />

    <template v-else-if="player">
      <!-- プロフィールカード -->
      <el-card style="margin-bottom: 24px;">
        <div style="display: flex; align-items: center; gap: 24px; flex-wrap: wrap;">
          <div style="font-size: 48px; font-weight: bold; color: #409eff; min-width: 80px; text-align: center;">
            #{{ player.jerseyNumber }}
          </div>
          <div>
            <h2 style="margin: 0 0 12px;">{{ player.name }}</h2>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <el-tag size="large">{{ player.teamName }}</el-tag>
              <el-tag type="success">{{ player.position }}</el-tag>
              <el-tag type="info">{{ player.height }}</el-tag>
              <el-tag type="info">{{ player.weight }} lbs</el-tag>
              <el-tag type="info">{{ player.age }} 歳</el-tag>
            </div>
          </div>
        </div>
      </el-card>

      <!-- シーズンスタッツ -->
      <el-card v-if="player.stats" style="margin-bottom: 24px;">
        <template #header>
          シーズンスタッツ ({{ player.stats.season }}) — {{ player.stats.gamesPlayed }} 試合
        </template>
        <el-row :gutter="16" style="text-align: center;">
          <el-col v-for="stat in displayStats" :key="stat.label" :xs="8" :sm="4">
            <div style="padding: 12px 0;">
              <div style="font-size: 22px; font-weight: bold; color: #409eff;">{{ stat.value }}</div>
              <div style="font-size: 12px; color: #666; margin-top: 4px;">{{ stat.label }}</div>
            </div>
          </el-col>
        </el-row>
      </el-card>

      <!-- ゲームログ -->
      <el-card>
        <template #header>
          <div style="display: flex; align-items: center; gap: 12px;">
            <span>ゲームログ</span>
            <el-tag type="info" size="small">直近 {{ gameLog.length }} 試合</el-tag>
          </div>
        </template>
        <el-skeleton v-if="gameLogLoading" :rows="5" animated />
        <template v-else>
          <el-table :data="gameLog" stripe size="small" style="width: 100%;">
            <el-table-column prop="gameDate" label="日付" width="110" />
            <el-table-column prop="minutes" label="MIN" width="60" align="right" />
            <el-table-column prop="points" label="PTS" width="60" align="right">
              <template #default="{ row }">
                <span :style="row.points >= 20 ? 'font-weight:bold;color:#409eff;' : ''">{{ row.points }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="rebounds" label="REB" width="60" align="right" />
            <el-table-column prop="assists" label="AST" width="60" align="right" />
            <el-table-column prop="steals" label="STL" width="60" align="right" />
            <el-table-column prop="blocks" label="BLK" width="60" align="right" />
            <el-table-column prop="turnovers" label="TO" width="56" align="right" />
            <el-table-column label="FG" width="72" align="right">
              <template #default="{ row }">{{ row.fgMade }}/{{ row.fgAttempted }}</template>
            </el-table-column>
            <el-table-column label="3P" width="72" align="right">
              <template #default="{ row }">{{ row.fg3Made }}/{{ row.fg3Attempted }}</template>
            </el-table-column>
            <el-table-column label="+/-" width="56" align="right">
              <template #default="{ row }">
                <span :style="row.plusMinus > 0 ? 'color:#67c23a;' : row.plusMinus < 0 ? 'color:#f56c6c;' : ''">
                  {{ row.plusMinus > 0 ? '+' : '' }}{{ row.plusMinus }}
                </span>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="gameLog.length === 0" description="ゲームログがありません" />
        </template>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { nbaService } from '../services/nbaService'
import type { PlayerDetail, GameStat } from '../types/nba'

const router = useRouter()
const route = useRoute()
const playerId = route.params.playerId as string

const player = ref<PlayerDetail | null>(null)
const loading = ref(false)
const error = ref('')
const gameLog = ref<GameStat[]>([])
const gameLogLoading = ref(false)

const displayStats = computed(() => {
  if (!player.value?.stats) return []
  const s = player.value.stats
  return [
    { label: 'PTS', value: s.points },
    { label: 'REB', value: s.rebounds },
    { label: 'AST', value: s.assists },
    { label: 'STL', value: s.steals },
    { label: 'BLK', value: s.blocks },
    { label: 'FG%', value: `${(s.fgPct * 100).toFixed(1)}%` },
    { label: '3P%', value: `${(s.fg3Pct * 100).toFixed(1)}%` },
    { label: 'FT%', value: `${(s.ftPct * 100).toFixed(1)}%` },
  ]
})

onMounted(async () => {
  loading.value = true
  try {
    player.value = await nbaService.getPlayer(playerId)
  } catch {
    error.value = '選手データの取得に失敗しました。'
  } finally {
    loading.value = false
  }

  gameLogLoading.value = true
  try {
    const res = await nbaService.getPlayerGameLog(playerId, 20)
    gameLog.value = res.gameLog
  } finally {
    gameLogLoading.value = false
  }
})
</script>
