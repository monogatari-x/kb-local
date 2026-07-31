<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ page: number; page_size: number; total: number }>()
const emit = defineEmits<{ 'update:page': [number] }>()

const totalPages = computed(() =>
  Math.max(1, Math.ceil(props.total / props.page_size)),
)
const canPrev = computed(() => props.page > 1)
const canNext = computed(() => props.page < totalPages.value)

function go(n: number) {
  if (n < 1 || n > totalPages.value || n === props.page) return
  emit('update:page', n)
}
</script>

<template>
  <div class="pagination">
    <span class="info">第 {{ page }} 页 / {{ totalPages }} · 共 {{ total }} 条</span>
    <span class="buttons">
      <button data-testid="prev" :disabled="!canPrev" @click="go(page - 1)">上一页</button>
      <button data-testid="next" :disabled="!canNext" @click="go(page + 1)">下一页</button>
    </span>
  </div>
</template>

<style scoped>
.pagination {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 0; color: var(--text-dim); font-size: 12px;
}
.buttons { display: flex; gap: 8px; }
button {
  background: var(--panel-2); color: var(--text); border: 1px solid var(--border);
  padding: 4px 12px; border-radius: 4px; font-size: 12px; cursor: pointer;
}
button:disabled { opacity: 0.4; cursor: not-allowed; }
button:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
</style>
