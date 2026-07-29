<script setup lang="ts">
const props = defineProps<{ score: number }>()
function cls(s: number): string {
  if (s >= 0.7) return 'score-high'
  if (s >= 0.4) return 'score-mid'
  return 'score-low'
}
</script>

<template>
  <span class="badge" :class="cls(props.score)">
    score {{ props.score.toFixed(3) }}
  </span>
</template>

<style scoped>
.badge {
  padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500;
  background: var(--panel-2); color: var(--text-dim); border: 1px solid var(--border);
}
.score-high { color: var(--score-high); border-color: var(--score-high); }
.score-mid { color: var(--score-mid); border-color: var(--score-mid); }
.score-low { color: var(--score-low); border-color: var(--score-low); }
</style>
