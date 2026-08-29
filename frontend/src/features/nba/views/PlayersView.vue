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
      @row-click="(row: Player) => router.push(`/players/${row.playerId}`)"
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
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { nbaService } from '../services/nbaService'
import type { Player } from '../types/nba'

const router = useRouter()
const players = ref<Player[]>([])
const loading = ref(false)
const error = ref('')
const selectedPosition = ref('')
const positions = ['PG', 'SG', 'SF', 'PF', 'C']

const fetchPlayers = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await nbaService.getPlayers({
      position: selectedPosition.value || undefined,
    })
    players.value = response.players
  } catch {
    players.value = []
    error.value = '選手データの取得に失敗しました。API URLが正しく設定されているか確認してください。'
  } finally {
    loading.value = false
  }
}

onMounted(fetchPlayers)
</script>
