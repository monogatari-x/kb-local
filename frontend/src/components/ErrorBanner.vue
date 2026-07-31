<script setup lang="ts">
defineProps<{ message: string }>()
defineEmits<{ dismiss: [] }>()
</script>

<template>
  <div class="banner">
    <span>{{ message }}</span>
    <button @click="$emit('dismiss')">×</button>
  </div>
</template>

<style scoped>
.banner {
  background: rgba(248, 113, 113, 0.15); border: 1px solid var(--error);
  color: var(--error); padding: 10px 14px; border-radius: 6px;
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px; font-size: 13px;
}
.banner button {
  background: none; border: none; color: var(--error); cursor: pointer;
  font-size: 18px; padding: 0 4px;
}
</style>
