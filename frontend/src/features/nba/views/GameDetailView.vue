<template>
  <div>
    <el-button :icon="ArrowLeft" style="margin-bottom: 20px;" @click="router.back()">
      試合一覧に戻る
    </el-button>

    <el-skeleton v-if="loading" :rows="8" animated />

    <el-alert
      v-else-if="error"
      :title="error"
      type="error"
      show-icon
    />

    <template v-else-if="game">
      <!-- スコアヘッダー -->
      <el-card style="margin-bottom: 24px;">
        <div style="text-align: center; padding: 16px 0;">
          <div style="font-size: 13px; color: #999; margin-bottom: 12px;">
            {{ game.gameDate }}
            <el-tag :type="game.status === 'Final' ? 'success' : 'warning'" size="small" style="margin-left: 8px;">
              {{ game.status }}
            </el-tag>
          </div>
          <div style="display: flex; align-items: center; justify-content: center; gap: 32px;">
            <div style="text-align: center;">
              <div style="font-size: 13px; color: #999;">AWAY</div>
              <div style="font-size: 36px; font-weight: bold;">{{ game.awayTeamAbbreviation }}</div>
              <div :style="`font-size: 48px; font-weight: bold; color: ${isAwayWin ? '#409eff' : '#999'};`">
                {{ game.awayScore }}
              </div>
            </div>
            <div style="font-size: 28px; color: #ccc; font-weight: 300;">VS</div>
            <div style="text-align: center;">
              <div style="font-size: 13px; color: #999;">HOME</div>
              <div style="font-size: 36px; font-weight: bold;">{{ game.homeTeamAbbreviation }}</div>
              <div :style="`font-size: 48px; font-weight: bold; color: ${isHomeWin ? '#409eff' : '#999'};`">
                {{ game.homeScore }}
              </div>
            </div>
          </div>
        </div>
      </el-card>

      <!-- ボックススコア -->
      <el-card>
        <template #header>
          <span style="font-weight: bold;">ボックススコア</span>
          <el-tag type="info" size="small" style="margin-left: 8px;">{{ game.boxScore.length }} 選手</el-tag>
        </template>

        <!-- HOMEチーム（上段） -->
        <div style="margin-bottom: 24px;">
          <div style="font-size: 13px; font-weight: bold; color: #666; margin-bottom: 8px; padding: 6px 0; border-bottom: 2px solid #eee;">
            HOME — {{ game.homeTeamAbbreviation }}
          </div>
          <el-table :data="homeStats" stripe size="small" style="width: 100%;">
            <el-table-column prop="playerName" label="選手" min-width="160" fixed />
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
            <el-table-column label="FT" width="72" align="right">
              <template #default="{ row }">{{ row.ftMade }}/{{ row.ftAttempted }}</template>
            </el-table-column>
            <el-table-column label="+/-" width="56" align="right">
              <template #default="{ row }">
                <span :style="row.plusMinus > 0 ? 'color:#67c23a;' : row.plusMinus < 0 ? 'color:#f56c6c;' : ''">
                  {{ row.plusMinus > 0 ? '+' : '' }}{{ row.plusMinus }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- AWAYチーム（下段） -->
        <div>
          <div style="font-size: 13px; font-weight: bold; color: #666; margin-bottom: 8px; padding: 6px 0; border-bottom: 2px solid #eee;">
            AWAY — {{ game.awayTeamAbbreviation }}
          </div>
          <el-table :data="awayStats" stripe size="small" style="width: 100%;">
            <el-table-column prop="playerName" label="選手" min-width="160" fixed />
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
            <el-table-column label="FT" width="72" align="right">
              <template #default="{ row }">{{ row.ftMade }}/{{ row.ftAttempted }}</template>
            </el-table-column>
            <el-table-column label="+/-" width="56" align="right">
              <template #default="{ row }">
                <span :style="row.plusMinus > 0 ? 'color:#67c23a;' : row.plusMinus < 0 ? 'color:#f56c6c;' : ''">
                  {{ row.plusMinus > 0 ? '+' : '' }}{{ row.plusMinus }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 未分類（チーム特定できなかった選手） -->
        <div v-if="unclassifiedStats.length > 0" style="margin-top: 24px;">
          <div style="font-size: 13px; font-weight: bold; color: #999; margin-bottom: 8px; padding: 6px 0; border-bottom: 2px solid #eee;">
            その他
          </div>
          <el-table :data="unclassifiedStats" stripe size="small" style="width: 100%;">
            <el-table-column prop="playerName" label="選手" min-width="160" fixed />
            <el-table-column prop="minutes" label="MIN" width="60" align="right" />
            <el-table-column prop="points" label="PTS" width="60" align="right" />
            <el-table-column prop="rebounds" label="REB" width="60" align="right" />
            <el-table-column prop="assists" label="AST" width="60" align="right" />
          </el-table>
        </div>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { nbaService } from '../services/nbaService'
import type { GameDetail, GameStat } from '../types/nba'

const router = useRouter()
const route = useRoute()

const game = ref<GameDetail | null>(null)
const loading = ref(false)
const error = ref('')

const isHomeWin = computed(
  () => game.value?.status === 'Final' && (game.value.homeScore ?? 0) > (game.value.awayScore ?? 0),
)
const isAwayWin = computed(
  () => game.value?.status === 'Final' && (game.value.awayScore ?? 0) > (game.value.homeScore ?? 0),
)

// GameStats に team_id が入っているレコードのみチーム別に分類する
// 古いレコード（team_id なし）は unclassifiedStats に入る
const homeStats = computed<GameStat[]>(() =>
  (game.value?.boxScore ?? [])
    .filter((s) => s.teamId === game.value?.homeTeamId)
    .sort((a, b) => b.points - a.points),
)

const awayStats = computed<GameStat[]>(() =>
  (game.value?.boxScore ?? [])
    .filter((s) => s.teamId === game.value?.awayTeamId)
    .sort((a, b) => b.points - a.points),
)

// team_id が付いていない既存レコードのフォールバック
const unclassifiedStats = computed<GameStat[]>(() =>
  (game.value?.boxScore ?? [])
    .filter((s) => !s.teamId)
    .sort((a, b) => b.points - a.points),
)

onMounted(async () => {
  const gameId = route.params.gameId as string
  loading.value = true
  error.value = ''
  try {
    game.value = await nbaService.getGameDetail(gameId)
  } catch {
    error.value = '試合データの取得に失敗しました。'
  } finally {
    loading.value = false
  }
})
</script>
