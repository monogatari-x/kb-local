<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchDocuments, fetchChunks, fetchProjects, ApiError } from '../api'
import type { DocumentItem, ChunkListItem } from '../types'
import Pagination from '../components/Pagination.vue'
import ErrorBanner from '../components/ErrorBanner.vue'

const route = useRoute()
const router = useRouter()

const project = ref((route.query.project as string) || '')
const status = ref((route.query.status as string) || '')
const q = ref((route.query.q as string) || '')
const sort = ref((route.query.sort as string) || 'ingested_at')
const order = ref((route.query.order as 'asc' | 'desc') || 'desc')
const page = ref(Number(route.query.page) || 1)
const pageSize = ref(50)

const items = ref<DocumentItem[]>([])
const total = ref(0)
const projects = ref<string[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const expandedDocId = ref<string | null>(null)
const expandedChunks = ref<ChunkListItem[]>([])
const chunksLoading = ref(false)

const sortOptions = [
  { value: 'ingested_at', label: '入库时间' },
  { value: 'size_bytes', label: '大小' },
  { value: 'project', label: '项目' },
  { value: 'file_type', label: '类型' },
]
const statusOptions = ['', 'active', 'archived', 'error', 'deleted']

async function load() {
  loading.value = true
  error.value = null
  try {
    const r = await fetchDocuments({
      project: project.value || undefined,
      status: status.value || undefined,
      q: q.value || undefined,
      sort: sort.value,
      order: order.value,
      page: page.value,
      page_size: pageSize.value,
    })
    items.value = r.items
    total.value = r.total
    router.replace({
      query: {
        ...(project.value && { project: project.value }),
        ...(status.value && { status: status.value }),
        ...(q.value && { q: q.value }),
        sort: sort.value,
        order: order.value,
        page: String(page.value),
      },
    })
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function toggleExpand(docId: string) {
  if (expandedDocId.value === docId) {
    expandedDocId.value = null
    expandedChunks.value = []
    return
  }
  expandedDocId.value = docId
  chunksLoading.value = true
  try {
    const r = await fetchChunks({ doc_id: docId, page_size: 20 })
    expandedChunks.value = r.items
  } catch (e) {
    expandedChunks.value = []
  } finally {
    chunksLoading.value = false
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
    <h2>文档</h2>

    <div class="filter-bar">
      <select v-model="project" @change="applyFilters">
        <option value="">全部项目</option>
        <option v-for="p in projects" :key="p" :value="p">{{ p }}</option>
      </select>
      <select v-model="status" @change="applyFilters">
        <option v-for="s in statusOptions" :key="s" :value="s">
          {{ s || '全部状态' }}
        </option>
      </select>
      <input
        v-model="q"
        type="text"
        placeholder="搜索路径..."
        @keydown.enter="applyFilters"
      />
      <select v-model="sort" @change="applyFilters">
        <option v-for="o in sortOptions" :key="o.value" :value="o.value">
          {{ o.label }}
        </option>
      </select>
      <select v-model="order" @change="applyFilters">
        <option value="desc">降序</option>
        <option value="asc">升序</option>
      </select>
    </div>

    <ErrorBanner v-if="error" :message="error" @dismiss="error = null" />

    <div v-if="loading" class="message">加载中...</div>
    <div v-else-if="items.length === 0" class="message">暂无文档</div>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th>项目</th>
          <th>路径</th>
          <th>类型</th>
          <th>大小</th>
          <th>状态</th>
          <th>入库时间</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="d in items" :key="d.doc_id">
          <tr
            class="row"
            :class="{ expanded: expandedDocId === d.doc_id }"
            @click="toggleExpand(d.doc_id)"
          >
            <td>{{ d.project }}</td>
            <td class="mono">{{ d.rel_path }}</td>
            <td>{{ d.file_type }}</td>
            <td>{{ d.size_bytes }}</td>
            <td><span class="status" :class="`status-${d.status}`">{{ d.status }}</span></td>
            <td class="dim">{{ d.ingested_at }}</td>
          </tr>
          <tr v-if="expandedDocId === d.doc_id" class="expand-row">
            <td colspan="6">
              <div v-if="chunksLoading" class="msg">加载切片中...</div>
              <div v-else-if="expandedChunks.length === 0" class="msg">无切片</div>
              <div v-else class="chunks-list">
                <div v-for="c in expandedChunks" :key="c.chunk_id" class="chunk-item">
                  <span class="badge">{{ c.chunk_type }}</span>
                  <span class="lines">L{{ c.start_line }}-{{ c.end_line }}</span>
                  <code>{{ c.text_truncated?.slice(0, 100) }}</code>
                </div>
              </div>
            </td>
          </tr>
        </template>
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
.filter-bar input { flex: 1; min-width: 200px; }
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
.row { cursor: pointer; }
.row:hover { background: var(--panel-2); }
.row.expanded { background: var(--panel-2); }
.mono { font-family: ui-monospace, monospace; }
.dim { color: var(--text-dim); }
.status {
  padding: 2px 8px; border-radius: 10px; font-size: 11px;
  background: var(--panel-2); border: 1px solid var(--border);
}
.status-active { color: var(--score-high); border-color: var(--score-high); }
.status-error { color: var(--error); border-color: var(--error); }
.expand-row td { background: var(--code-bg); padding: 12px; }
.msg { color: var(--text-dim); padding: 8px; }
.chunks-list { display: flex; flex-direction: column; gap: 6px; }
.chunk-item {
  display: flex; gap: 8px; align-items: center; padding: 4px 0;
  font-size: 12px;
}
.chunk-item code {
  flex: 1; color: var(--text-dim);
  font-family: ui-monospace, monospace; font-size: 11px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.badge {
  padding: 1px 6px; border-radius: 8px; font-size: 10px;
  background: var(--panel-2); color: var(--text-dim); border: 1px solid var(--border);
}
.lines { color: var(--text-dim); font-family: ui-monospace, monospace; }
</style>
