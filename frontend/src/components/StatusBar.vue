<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchStatus, ApiError } from '../api'
import type { StatusInfo } from '../types'

const router = useRouter()
const info = ref<StatusInfo | null>(null)
const errorMsg = ref<string | null>(null)

const items = [
  { key: 'documents', label: '文档', route: '/documents' },
  { key: 'chunks', label: '切片', route: '/chunks' },
  { key: 'watch_dirs', label: '监控目录', route: '/watch-dirs' },
  { key: 'jobs', label: '任务', route: '/jobs' },
] as const

onMounted(async () => {
  try {
    info.value = await fetchStatus()
  } catch (e) {
    errorMsg.value = e instanceof ApiError ? e.message : '状态获取失败'
  }
})
</script>

<template>
  <div class="status-bar">
    <template v-if="errorMsg">
      <span class="stat error">{{ errorMsg }}</span>
    </template>
    <template v-else-if="info">
      <button
        v-for="it in items"
        :key="it.key"
        class="stat"
        @click="router.push(it.route)"
      >
        <span class="num">{{ info[it.key] }}</span> {{ it.label }}
      </button>
    </template>
    <template v-else>
      <span class="stat">加载中...</span>
    </template>
  </div>
</template>

<style scoped>
.status-bar { display: flex; gap: 18px; font-size: 12px; color: var(--text-dim); }
.stat {
  display: inline-flex; align-items: baseline; gap: 4px;
  background: none; border: none; color: inherit;
  font: inherit; cursor: pointer; padding: 0;
}
.stat:hover { color: var(--text); }
.stat .num {
  color: var(--text); font-weight: 600; font-variant-numeric: tabular-nums;
}
.stat.error { color: var(--error); cursor: default; }
</style>
