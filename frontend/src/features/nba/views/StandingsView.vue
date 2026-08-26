<template>
  <div>
    <h2 style="margin: 0 0 24px;">順位表 — {{ currentSeason }}</h2>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      style="margin-bottom: 16px;"
    />

    <el-row v-loading="loading" :gutter="24" style="row-gap: 16px;">
      <el-col :xs="24" :md="12">
        <el-card>
          <template #header>
            <el-tag type="danger" style="font-size: 14px; padding: 4px 12px;">Eastern Conference</el-tag>
          </template>
          <el-table :data="east" size="small" :show-header="true">
            <el-table-column label="#" width="40">
              <template #default="{ row }">
                <span :style="row.seed <= 6 ? 'color:#409eff;font-weight:bold;' : row.seed <= 10 ? 'color:#e6a23c;' : 'color:#999;'">
                  {{ row.seed }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="チーム" min-width="100">
              <template #default="{ row }">
                <span style="font-weight: bold;">{{ row.teamAbbreviation }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="wins" label="W" width="48" align="right" />
            <el-table-column prop="losses" label="L" width="48" align="right" />
            <el-table-column prop="winPct" label="PCT" width="60" align="right" />
            <el-table-column prop="gamesBehind" label="GB" width="52" align="right" />
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="12">
        <el-card>
          <template #header>
            <el-tag type="primary" style="font-size: 14px; padding: 4px 12px;">Western Conference</el-tag>
          </template>
          <el-table :data="west" size="small" :show-header="true">
            <el-table-column label="#" width="40">
              <template #default="{ row }">
                <span :style="row.seed <= 6 ? 'color:#409eff;font-weight:bold;' : row.seed <= 10 ? 'color:#e6a23c;' : 'color:#999;'">
                  {{ row.seed }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="チーム" min-width="100">
              <template #default="{ row }">
                <span style="font-weight: bold;">{{ row.teamAbbreviation }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="wins" label="W" width="48" align="right" />
            <el-table-column prop="losses" label="L" width="48" align="right" />
            <el-table-column prop="winPct" label="PCT" width="60" align="right" />
            <el-table-column prop="gamesBehind" label="GB" width="52" align="right" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <div style="margin-top: 12px; font-size: 12px; color: #999;">
      <el-tag size="small" type="primary" style="margin-right: 6px;">青字</el-tag>プレーオフ確定（1〜6位）
      <el-tag size="small" type="warning" style="margin: 0 6px;">橙字</el-tag>プレーイン（7〜10位）
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { nbaService } from '../services/nbaService'
import type { Standing } from '../types/nba'

const standings = ref<Standing[]>([])
const loading = ref(false)
const error = ref('')

const east = computed(() => standings.value.filter((s) => s.conference === 'East'))
const west = computed(() => standings.value.filter((s) => s.conference === 'West'))
const currentSeason = computed(() => standings.value[0]?.season ?? '')

onMounted(async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await nbaService.getStandings()
    standings.value = res.standings
  } catch {
    error.value = '順位表の取得に失敗しました。'
  } finally {
    loading.value = false
  }
})
</script>
