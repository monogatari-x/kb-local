<script setup lang="ts">
const props = defineProps<{ text: string; truncate?: number }>()
const truncated = ((): string => {
  if (!props.truncate) return props.text
  return props.text.length > props.truncate
    ? props.text.slice(0, props.truncate) + '…'
    : props.text
})()
</script>

<template>
  <pre class="code">{{ truncated }}</pre>
</template>

<style scoped>
.code {
  background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px;
  padding: 10px 12px; margin: 0; overflow-x: auto;
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 12.5px; line-height: 1.55; color: var(--text);
  white-space: pre-wrap; word-break: break-word;
}
</style>
