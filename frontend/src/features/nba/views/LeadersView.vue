<template>
  <div>
    <h2 style="margin: 0 0 24px;">スタッツリーダーボード</h2>

    <el-tabs v-model="activeCategory" @tab-change="fetchLeaders">
      <el-tab-pane label="得点" name="points" />
      <el-tab-pane label="リバウンド" name="rebounds" />
      <el-tab-pane label="アシスト" name="assists" />
      <el-tab-pane label="スティール" name="steals" />
      <el-tab-pane label="ブロック" name="blocks" />
    </el-tabs>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      style="margin-bottom: 16px;"
    />

    <el-table v-loading="loading" :data="leaders" stripe style="width: 100%;">
      <el-table-column label="順位" width="64" align="center">
        <template #default="{ $index }">
          <span :style="$index === 0 ? 'color:#ffd600;font-weight:bold;font-size:16px;' : $index === 1 ? 'color:#b0bec5;font-weight:bold;' : $index === 2 ? 'color:#bf8c56;font-weight:bold;' : 'color:#999;'">
            {{ $index + 1 }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="playerName" label="選手" min-width="180" />
      <el-table-column prop="gamesPlayed" label="GP" width="60" align="right" />
      <el-table-column :label="categoryLabel" width="90" align="right">
        <template #default="{ row }">
          <span style="font-weight: bold; font-size: 16px; color: #409eff;">
            {{ currentAvg(row) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column v-if="activeCategory === 'points'" label="FG%" width="72" align="right">
        <template #default="{ row }">{{ row.fgPct }}%</template>
      </el-table-column>
      <el-table-column v-if="activeCategory === 'points'" label="3P%" width="72" align="right">
        <template #default="{ row }">{{ row.fg3Pct }}%</template>
      </el-table-column>
      <el-table-column v-if="activeCategory === 'points'" label="FT%" width="72" align="right">
        <template #default="{ row }">{{ row.ftPct }}%</template>
      </el-table-column>
      <el-table-column v-if="activeCategory !== 'points'" label="PTS" width="72" align="right">
        <template #default="{ row }">{{ row.avgPoints }}</template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { nbaService } from '../services/nbaService'
import type { Leader } from '../types/nba'

const activeCategory = ref<'points' | 'rebounds' | 'assists' | 'steals' | 'blocks'>('points')
const leaders = ref<Leader[]>([])
const loading = ref(false)
const error = ref('')

const categoryLabel = computed(() => {
  const labels: Record<string, string> = {
    points: '平均得点',
    rebounds: '平均REB',
    assists: '平均AST',
    steals: '平均STL',
    blocks: '平均BLK',
  }
  return labels[activeCategory.value] ?? '平均'
})

const currentAvg = (row: Leader): number => {
  const map: Record<string, keyof Leader> = {
    points: 'avgPoints',
    rebounds: 'avgRebounds',
    assists: 'avgAssists',
    steals: 'avgSteals',
    blocks: 'avgBlocks',
  }
  return row[map[activeCategory.value]] as number
}

const fetchLeaders = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await nbaService.getLeaders(activeCategory.value, 30)
    leaders.value = res.leaders
  } catch {
    error.value = 'リーダーボードの取得に失敗しました。'
  } finally {
    loading.value = false
  }
}

onMounted(fetchLeaders)
</script>
