<script setup lang="ts">
import { ref, watch } from 'vue'
import { fetchChunk, ApiError } from '../api'
import type { ChunkDetail } from '../types'

const props = defineProps<{ chunkId: string | null }>()
const emit = defineEmits<{ close: [] }>()

const data = ref<ChunkDetail | null>(null)
const errorMsg = ref<string | null>(null)
const loading = ref(false)

watch(
  () => props.chunkId,
  async (id) => {
    if (!id) {
      data.value = null
      return
    }
    loading.value = true
    errorMsg.value = null
    try {
      data.value = await fetchChunk(id)
    } catch (e) {
      errorMsg.value = e instanceof ApiError ? e.message : '加载失败'
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)
</script>

<template>
  <div v-if="chunkId" class="overlay" @click.self="emit('close')">
    <div class="modal">
      <div class="modal-header">
        <span v-if="data" class="citation">{{ data.chunk_id }}</span>
        <button class="close-btn" @click="emit('close')">×</button>
      </div>
      <div class="modal-body">
        <div v-if="loading" class="msg">加载中...</div>
        <div v-else-if="errorMsg" class="msg error">{{ errorMsg }}</div>
        <template v-else-if="data">
          <div class="meta">
            <span>type: {{ data.chunk_type }}</span>
            <span v-if="data.language">lang: {{ data.language }}</span>
            <span v-if="data.start_line !== null">
              lines: {{ data.start_line }}-{{ data.end_line }}
            </span>
          </div>
          <pre class="full-text">{{ data.text }}</pre>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal {
  background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
  width: min(800px, 90vw); max-height: 80vh; display: flex; flex-direction: column;
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px; border-bottom: 1px solid var(--border);
}
.citation { color: var(--accent); font-family: ui-monospace, monospace; }
.close-btn {
  background: none; border: none; color: var(--text-dim); font-size: 20px;
  cursor: pointer; padding: 0 8px;
}
.close-btn:hover { color: var(--text); }
.modal-body { padding: 16px; overflow: auto; }
.meta { display: flex; gap: 12px; color: var(--text-dim); font-size: 12px; margin-bottom: 8px; }
.full-text {
  background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px;
  padding: 12px; margin: 0;
  font-family: ui-monospace, monospace; font-size: 12.5px;
  white-space: pre-wrap; word-break: break-word; color: var(--text);
}
.msg { padding: 20px; text-align: center; color: var(--text-dim); }
.msg.error { color: var(--error); }
</style>
