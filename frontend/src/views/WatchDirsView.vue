<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchWatchDirs, ApiError } from '../api'
import type { WatchDirItem } from '../types'
import ErrorBanner from '../components/ErrorBanner.vue'

const items = ref<WatchDirItem[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

onMounted(async () => {
  loading.value = true
  try {
    items.value = await fetchWatchDirs()
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page">
    <h2>监控目录</h2>
    <ErrorBanner v-if="error" :message="error" @dismiss="error = null" />
    <div v-if="loading" class="message">加载中...</div>
    <div v-else-if="items.length === 0" class="message">暂无监控目录</div>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th>路径</th>
          <th>项目</th>
          <th>策略</th>
          <th>递归</th>
          <th>创建时间</th>
          <th>最后扫描</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="d in items" :key="d.id">
          <td class="mono">{{ d.path }}</td>
          <td>{{ d.project_name }}</td>
          <td>{{ d.project_strategy }}</td>
          <td>{{ d.recursive ? '是' : '否' }}</td>
          <td class="dim">{{ d.created_at }}</td>
          <td class="dim">{{ d.last_scan_at || '从未' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.page { padding: 0 20px; }
h2 { margin: 0 0 16px; font-size: 18px; }
.message { text-align: center; padding: 40px; color: var(--text-dim); }
.data-table {
  width: 100%; border-collapse: collapse;
  background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
  overflow: hidden;
}
.data-table th, .data-table td {
  padding: 10px 12px; text-align: left; font-size: 13px;
  border-bottom: 1px solid var(--border);
}
.data-table th { color: var(--text-dim); font-weight: 500; background: var(--panel-2); }
.mono { font-family: ui-monospace, monospace; }
.dim { color: var(--text-dim); }
</style>
