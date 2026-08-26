<template>
  <div>
    <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 24px;">
      <h2 style="margin: 0;">試合結果</h2>
      <el-date-picker
        v-model="selectedDate"
        type="date"
        placeholder="日付で絞り込み"
        format="YYYY-MM-DD"
        value-format="YYYY-MM-DD"
        clearable
        style="width: 180px;"
        @change="fetchGames"
      />
      <el-tag type="info">{{ games.length }} 試合</el-tag>
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      style="margin-bottom: 16px;"
    />

    <el-row v-loading="loading" :gutter="16">
      <el-col
        v-for="game in games"
        :key="game.gameId"
        :xs="24"
        :sm="12"
        :md="8"
        style="margin-bottom: 16px;"
      >
        <el-card shadow="hover" style="cursor: pointer;" @click="router.push(`/games/${game.gameId}`)">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span style="font-size: 13px; color: #666;">{{ game.gameDate }}</span>
              <el-tag :type="game.status === 'Final' ? 'success' : 'warning'" size="small">
                {{ game.status }}
              </el-tag>
            </div>
          </template>

          <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 0;">
            <div style="text-align: center; flex: 1;">
              <div style="font-size: 20px; font-weight: bold;">{{ game.awayTeamAbbreviation }}</div>
              <div style="font-size: 13px; color: #666; margin-top: 4px;">AWAY</div>
            </div>

            <div style="text-align: center; padding: 0 16px;">
              <div style="font-size: 26px; font-weight: bold; line-height: 1.2;">
                <span :style="isAwayWin(game) ? 'color: #409eff;' : 'color: #999;'">{{ game.awayScore }}</span>
                <span style="color: #ccc; margin: 0 8px;">-</span>
                <span :style="isHomeWin(game) ? 'color: #409eff;' : 'color: #999;'">{{ game.homeScore }}</span>
              </div>
              <div style="font-size: 11px; color: #bbb; margin-top: 4px;">タップで詳細</div>
            </div>

            <div style="text-align: center; flex: 1;">
              <div style="font-size: 20px; font-weight: bold;">{{ game.homeTeamAbbreviation }}</div>
              <div style="font-size: 13px; color: #666; margin-top: 4px;">HOME</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="!loading && games.length === 0" description="試合データがありません" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { nbaService } from '../services/nbaService'
import type { Game } from '../types/nba'

const router = useRouter()
const games = ref<Game[]>([])
const loading = ref(false)
const error = ref('')
const selectedDate = ref<string | null>(null)

const isHomeWin = (game: Game) => game.status === 'Final' && game.homeScore > game.awayScore
const isAwayWin = (game: Game) => game.status === 'Final' && game.awayScore > game.homeScore

const fetchGames = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await nbaService.getGames({
      date: selectedDate.value ?? undefined,
    })
    games.value = response.games
  } catch {
    error.value = '試合データの取得に失敗しました。API URLが正しく設定されているか確認してください。'
  } finally {
    loading.value = false
  }
}

onMounted(fetchGames)
</script>
