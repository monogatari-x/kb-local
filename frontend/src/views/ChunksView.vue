<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { fetchChunks, fetchProjects, ApiError } from '../api'
import type { ChunkListItem } from '../types'
import Pagination from '../components/Pagination.vue'
import ErrorBanner from '../components/ErrorBanner.vue'
import ChunkDetailModal from '../components/ChunkDetailModal.vue'

const route = useRoute()
const docId = ref((route.query.doc_id as string) || '')
const project = ref((route.query.project as string) || '')
const chunkType = ref((route.query.chunk_type as string) || '')
const q = ref((route.query.q as string) || '')
const page = ref(1)
const pageSize = ref(50)

const items = ref<ChunkListItem[]>([])
const total = ref(0)
const projects = ref<string[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const modalChunkId = ref<string | null>(null)

const chunkTypeOptions = [
  '', 'paragraph', 'heading', 'code_function', 'code_class',
  'code_statement', 'table', 'list', 'image_caption', 'mixed',
]

async function load() {
  loading.value = true
  error.value = null
  try {
    const r = await fetchChunks({
      doc_id: docId.value || undefined,
      project: project.value || undefined,
      chunk_type: chunkType.value || undefined,
      q: q.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    items.value = r.items
    total.value = r.total
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  page.value = 1
  load()
}

onMounted(async () => {
  try {
    projects.value = await fetchProjects()
  } catch {
    // optional
  }
  await load()
})

watch([page], () => load())
</script>

<template>
  <div class="page">
    <h2>切片</h2>

    <div class="filter-bar">
      <input v-model="docId" type="text" placeholder="doc_id" @keydown.enter="applyFilters" />
      <select v-model="project" @change="applyFilters">
        <option value="">全部项目</option>
        <option v-for="p in projects" :key="p" :value="p">{{ p }}</option>
      </select>
      <select v-model="chunkType" @change="applyFilters">
        <option v-for="c in chunkTypeOptions" :key="c" :value="c">
          {{ c || '全部类型' }}
        </option>
      </select>
      <input v-model="q" type="text" placeholder="搜索文本..." @keydown.enter="applyFilters" />
    </div>

    <ErrorBanner v-if="error" :message="error" @dismiss="error = null" />

    <div v-if="loading" class="message">加载中...</div>
    <div v-else-if="items.length === 0" class="message">暂无切片</div>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th>类型</th>
          <th>文本预览</th>
          <th>语言</th>
          <th>行</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in items" :key="c.chunk_id">
          <td><span class="badge">{{ c.chunk_type }}</span></td>
          <td class="preview">{{ c.text_truncated || '(空)' }}</td>
          <td>{{ c.language || '' }}</td>
          <td class="mono">L{{ c.start_line }}-{{ c.end_line }}</td>
          <td>
            <button class="view-btn" @click="modalChunkId = c.chunk_id">查看</button>
          </td>
        </tr>
      </tbody>
    </table>

    <Pagination
      v-if="!loading && total > 0"
      :page="page"
      :page_size="pageSize"
      :total="total"
      @update:page="page = $event"
    />
  </div>

  <ChunkDetailModal :chunk-id="modalChunkId" @close="modalChunkId = null" />
</template>

<style scoped>
.page { padding: 0 20px; }
h2 { margin: 0 0 16px; font-size: 18px; }
.filter-bar {
  display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;
}
.filter-bar select, .filter-bar input {
  background: var(--panel-2); border: 1px solid var(--border); border-radius: 6px;
  color: var(--text); padding: 6px 10px; font-size: 13px; outline: none;
}
.filter-bar input { min-width: 160px; }
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
.preview {
  font-family: ui-monospace, monospace; font-size: 12px;
  max-width: 500px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.mono { font-family: ui-monospace, monospace; color: var(--text-dim); }
.badge {
  padding: 2px 8px; border-radius: 10px; font-size: 11px;
  background: var(--panel-2); color: var(--text-dim); border: 1px solid var(--border);
}
.view-btn {
  background: var(--panel-2); color: var(--accent); border: 1px solid var(--accent);
  padding: 4px 10px; border-radius: 4px; font-size: 11px; cursor: pointer;
}
.view-btn:hover { background: var(--accent); color: #fff; }
</style>
