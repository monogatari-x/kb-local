<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchJobs, ApiError } from '../api'
import type { JobItem } from '../types'
import ErrorBanner from '../components/ErrorBanner.vue'

const items = ref<JobItem[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const statusFilter = ref('')

const statusOptions = ['', 'running', 'succeeded', 'failed', 'cancelled']

async function load() {
  loading.value = true
  error.value = null
  try {
    items.value = await fetchJobs({ status: statusFilter.value || undefined, limit: 100 })
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)

function statusClass(s: string): string {
  if (s === 'succeeded') return 'status-active'
  if (s === 'failed') return 'status-error'
  return ''
}
</script>

<template>
  <div class="page">
    <h2>任务</h2>

    <div class="filter-bar">
      <select v-model="statusFilter" @change="load">
        <option v-for="s in statusOptions" :key="s" :value="s">
          {{ s || '全部状态' }}
        </option>
      </select>
    </div>

    <ErrorBanner v-if="error" :message="error" @dismiss="error = null" />

    <div v-if="loading" class="message">加载中...</div>
    <div v-else-if="items.length === 0" class="message">暂无任务</div>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th>类型</th>
          <th>状态</th>
          <th>开始</th>
          <th>结束</th>
          <th>处理/失败</th>
          <th>触发</th>
          <th>错误</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="j in items" :key="j.job_id">
          <td>{{ j.type }}</td>
          <td><span class="status" :class="statusClass(j.status)">{{ j.status }}</span></td>
          <td class="dim">{{ j.started_at }}</td>
          <td class="dim">{{ j.finished_at || '—' }}</td>
          <td class="mono">{{ j.processed_files }}/{{ j.failed_files }}</td>
          <td>{{ j.trigger || '' }}</td>
          <td class="error-cell">{{ j.error_log || '' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.page { padding: 0 20px; }
h2 { margin: 0 0 16px; font-size: 18px; }
.filter-bar { display: flex; gap: 8px; margin-bottom: 16px; }
.filter-bar select {
  background: var(--panel-2); border: 1px solid var(--border); border-radius: 6px;
  color: var(--text); padding: 6px 10px; font-size: 13px; outline: none;
}
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
.error-cell {
  color: var(--error); font-size: 11px;
  max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.status {
  padding: 2px 8px; border-radius: 10px; font-size: 11px;
  background: var(--panel-2); border: 1px solid var(--border);
}
.status-active { color: var(--score-high); border-color: var(--score-high); }
.status-error { color: var(--error); border-color: var(--error); }
</style>
