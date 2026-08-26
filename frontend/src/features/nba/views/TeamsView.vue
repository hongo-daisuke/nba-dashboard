<template>
  <div>
    <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 24px;">
      <h2 style="margin: 0;">NBA チーム一覧</h2>
      <el-select
        v-model="selectedConference"
        placeholder="カンファレンス絞り込み"
        clearable
        style="width: 180px;"
        @change="fetchTeams"
      >
        <el-option label="Eastern" value="East" />
        <el-option label="Western" value="West" />
      </el-select>
      <el-tag type="info">{{ teams.length }} チーム</el-tag>
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
        v-for="team in teams"
        :key="team.teamId"
        :xs="24"
        :sm="12"
        :md="8"
        :lg="6"
        style="margin-bottom: 16px;"
      >
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <div style="display: flex; align-items: center; gap: 8px;">
                <el-tag :type="team.conference === 'East' ? 'danger' : 'primary'" size="small">
                  {{ team.conference }}
                </el-tag>
                <span style="font-weight: bold;">{{ team.abbreviation }}</span>
              </div>
              <span style="font-size: 12px; color: #999;">{{ team.yearFounded }}年創設</span>
            </div>
          </template>
          <div style="font-size: 16px; font-weight: bold; margin-bottom: 8px;">
            {{ team.fullName }}
          </div>
          <div style="color: #666; font-size: 14px;">
            <div>都市: {{ team.city }}, {{ team.state }}</div>
            <div>地区: {{ team.division }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { nbaService } from '../services/nbaService'
import type { Team } from '../types/nba'

const teams = ref<Team[]>([])
const loading = ref(false)
const error = ref('')
const selectedConference = ref('')

const fetchTeams = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await nbaService.getTeams(selectedConference.value || undefined)
    teams.value = response.teams
  } catch {
    error.value = 'チームデータの取得に失敗しました。API URLが正しく設定されているか確認してください。'
  } finally {
    loading.value = false
  }
}

onMounted(fetchTeams)
</script>
