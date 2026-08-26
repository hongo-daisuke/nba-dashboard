<template>
  <el-container style="min-height: 100vh;">
    <el-header
      style="
        background-color: #1a237e;
        color: white;
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 0 24px;
      "
    >
      <el-icon :size="24"><Trophy /></el-icon>
      <span style="font-size: 20px; font-weight: bold;">{{ appTitle }}</span>
      <el-menu
        mode="horizontal"
        router
        style="background-color: transparent; border: none; flex: 1;"
        text-color="rgba(255,255,255,0.75)"
        active-text-color="#ffd600"
        :default-active="$route.path"
      >
        <el-menu-item index="/teams">チーム一覧</el-menu-item>
        <el-menu-item index="/players">選手一覧</el-menu-item>
        <el-menu-item index="/games">試合結果</el-menu-item>
        <el-menu-item index="/standings">順位表</el-menu-item>
        <el-menu-item index="/leaders">リーダーボード</el-menu-item>
      </el-menu>
      <el-tag v-if="envBadge" :type="envBadge.type" size="small" style="margin-left: auto;">
        {{ envBadge.label }}
      </el-tag>
    </el-header>
    <el-main style="background-color: #f5f5f5;">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const appTitle = import.meta.env.VITE_APP_TITLE

const envBadge = computed(() => {
  const mode = import.meta.env.MODE
  if (mode === 'development') return { label: 'LOCAL', type: 'info' as const }
  if (mode === 'dev') return { label: 'DEV', type: 'warning' as const }
  return null
})
</script>
