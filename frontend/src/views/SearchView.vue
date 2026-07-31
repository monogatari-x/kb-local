<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { search, fetchProjects, ApiError } from '../api'
import type { SearchResult } from '../types'
import ScoreBadge from '../components/ScoreBadge.vue'
import CodeBlock from '../components/CodeBlock.vue'
import ChunkDetailModal from '../components/ChunkDetailModal.vue'
import ErrorBanner from '../components/ErrorBanner.vue'

const query = ref('')
const topK = ref(10)
const project = ref('')
const threshold = ref(0.3)
const projects = ref<string[]>([])

const results = ref<SearchResult[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const elapsedMs = ref(0)
const modalChunkId = ref<string | null>(null)

onMounted(async () => {
  try {
    projects.value = await fetchProjects()
  } catch {
    projects.value = []
  }
})

async function doSearch() {
  const q = query.value.trim()
  if (!q) return
  loading.value = true
  error.value = null
  const t0 = performance.now()
  try {
    results.value = await search({
      query: q,
      top_k: topK.value,
      project: project.value || null,
      threshold: threshold.value,
    })
    elapsedMs.value = performance.now() - t0
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '检索失败'
    results.value = []
  } finally {
    loading.value = false
  }
}

const thresholdLabel = computed(() => threshold.value.toFixed(2))
</script>

<template>
  <div class="search-page">
    <div class="search-card">
      <div class="search-row">
        <input
          v-model="query"
          type="text"
          placeholder="输入查询(1-3 个关键词效果最佳),回车搜索"
          autocomplete="off"
          @keydown.enter="doSearch"
        />
        <button :disabled="loading" @click="doSearch">
          {{ loading ? '搜索中...' : '搜索' }}
        </button>
      </div>
      <div class="filters">
        <label>
          项目
          <select v-model="project">
            <option value="">全部</option>
            <option v-for="p in projects" :key="p" :value="p">{{ p }}</option>
          </select>
        </label>
        <label>
          top_k
          <input v-model.number="topK" type="number" min="1" max="50" />
        </label>
        <label class="threshold">
          <span>阈值 {{ thresholdLabel }}</span>
          <input v-model.number="threshold" type="range" min="0" max="1" step="0.05" />
        </label>
      </div>
    </div>

    <ErrorBanner v-if="error" :message="error" @dismiss="error = null" />

    <div v-if="loading" class="message">检索中...</div>
    <div v-else-if="results.length === 0 && query" class="message">
      未找到匹配结果<br />尝试降低阈值或更换关键词
    </div>

    <template v-else-if="results.length > 0">
      <div class="results-header">
        <span>{{ results.length }} 条结果</span>
        <span>{{ elapsedMs.toFixed(0) }} ms</span>
      </div>
      <div v-for="(r, idx) in results" :key="idx" class="result-card">
        <div class="result-meta">
          <span class="citation">{{ r.citation }}</span>
          <span class="badges">
            <span class="badge">{{ r.chunk_type }}</span>
            <span v-if="r.project" class="badge">{{ r.project }}</span>
            <ScoreBadge :score="r.score" />
            <button class="view-btn" @click="modalChunkId = r.chunk_id">
              查看完整切片
            </button>
          </span>
        </div>
        <CodeBlock :text="r.text" :truncate="500" />
      </div>
    </template>
  </div>

  <ChunkDetailModal :chunk-id="modalChunkId" @close="modalChunkId = null" />
</template>

<style scoped>
.search-page { display: flex; flex-direction: column; }
.search-card {
  background: var(--panel); border: 1px solid var(--border);
  border-radius: 8px; padding: 16px; margin-bottom: 20px;
}
.search-row { display: flex; gap: 10px; margin-bottom: 12px; }
.search-row input[type="text"] {
  flex: 1; background: var(--panel-2); border: 1px solid var(--border);
  border-radius: 6px; color: var(--text); padding: 9px 12px; font-size: 14px; outline: none;
}
.search-row input[type="text"]:focus { border-color: var(--accent); }
.search-row button {
  background: var(--accent); color: #fff; border: none; border-radius: 6px;
  padding: 9px 18px; font-size: 14px; font-weight: 500; cursor: pointer;
}
.search-row button:disabled { opacity: 0.6; cursor: not-allowed; }
.filters {
  display: grid; grid-template-columns: 1fr 1fr 2fr;
  gap: 12px; align-items: center;
}
.filters label {
  display: flex; flex-direction: column; gap: 4px;
  font-size: 12px; color: var(--text-dim);
}
.filters select, .filters input[type="number"] {
  background: var(--panel-2); border: 1px solid var(--border); border-radius: 6px;
  color: var(--text); padding: 6px 10px; font-size: 13px; outline: none;
}
.filters .threshold input[type="range"] { width: 100%; margin-top: 4px; accent-color: var(--accent); }
.message { text-align: center; padding: 40px 20px; color: var(--text-dim); font-size: 13px; }
.results-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px; color: var(--text-dim); font-size: 13px;
}
.result-card {
  background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
  padding: 14px 16px; margin-bottom: 10px;
}
.result-card:hover { border-color: #3a4351; }
.result-meta {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 8px; font-size: 12px; flex-wrap: wrap; gap: 6px;
}
.citation {
  color: var(--accent); font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  word-break: break-all;
}
.badges { display: flex; gap: 6px; align-items: center; }
.badge {
  padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500;
  background: var(--panel-2); color: var(--text-dim); border: 1px solid var(--border);
}
.view-btn {
  background: var(--panel-2); color: var(--accent); border: 1px solid var(--accent);
  padding: 2px 10px; border-radius: 10px; font-size: 11px; cursor: pointer;
}
.view-btn:hover { background: var(--accent); color: #fff; }
@media (max-width: 640px) {
  .filters { grid-template-columns: 1fr; }
}
</style>
