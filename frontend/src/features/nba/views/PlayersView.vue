<template>
  <div>
    <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 24px;">
      <h2 style="margin: 0;">NBA 選手一覧</h2>
      <el-select
        v-model="selectedPosition"
        placeholder="ポジション絞り込み"
        clearable
        style="width: 180px;"
        @change="fetchPlayers"
      >
        <el-option v-for="pos in positions" :key="pos" :label="pos" :value="pos" />
      </el-select>
      <el-tag type="info">{{ players.length }} 選手</el-tag>
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      style="margin-bottom: 16px;"
    />

    <el-table
      v-loading="loading"
      :data="players"
      stripe
      style="width: 100%;"
      row-style="cursor: pointer;"
      @row-click="openGameLog"
    >
      <el-table-column prop="jerseyNumber" label="#" width="60" />
      <el-table-column prop="name" label="選手名" min-width="160" />
      <el-table-column prop="teamName" label="チーム" min-width="200" />
      <el-table-column prop="position" label="POS" width="80">
        <template #default="{ row }">
          <el-tag size="small">{{ row.position }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="height" label="身長" width="90" />
      <el-table-column prop="weight" label="体重(lbs)" width="100" />
      <el-table-column prop="age" label="年齢" width="70" />
      <el-table-column label="" width="80" align="center">
        <template #default>
          <el-text size="small" type="info">ゲームログ</el-text>
        </template>
      </el-table-column>
    </el-table>

    <!-- ゲームログ ドロワー -->
    <el-drawer
      v-model="drawerVisible"
      :title="`${selectedPlayer?.name} — ゲームログ`"
      size="80%"
      direction="btt"
    >
      <el-skeleton v-if="gameLogLoading" :rows="6" animated style="padding: 16px;" />
      <el-table v-else :data="gameLog" stripe size="small" style="width: 100%;">
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
      <el-empty v-if="!gameLogLoading && gameLog.length === 0" description="ゲームログがありません" />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { nbaService } from '../services/nbaService'
import type { Player, GameStat } from '../types/nba'

const players = ref<Player[]>([])
const loading = ref(false)
const error = ref('')
const selectedPosition = ref('')
const positions = ['PG', 'SG', 'SF', 'PF', 'C']

const drawerVisible = ref(false)
const selectedPlayer = ref<Player | null>(null)
const gameLog = ref<GameStat[]>([])
const gameLogLoading = ref(false)

const fetchPlayers = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await nbaService.getPlayers({
      position: selectedPosition.value || undefined,
    })
    players.value = response.players
  } catch {
    error.value = '選手データの取得に失敗しました。API URLが正しく設定されているか確認してください。'
  } finally {
    loading.value = false
  }
}

const openGameLog = async (player: Player) => {
  selectedPlayer.value = player
  drawerVisible.value = true
  gameLogLoading.value = true
  gameLog.value = []
  try {
    const res = await nbaService.getPlayerGameLog(player.playerId, 20)
    gameLog.value = res.gameLog
  } finally {
    gameLogLoading.value = false
  }
}

onMounted(fetchPlayers)
</script>
