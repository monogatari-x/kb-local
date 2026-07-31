<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<template>
  <div class="page">
    <h2>页面不存在</h2>
    <button @click="router.push('/')">回到搜索</button>
  </div>
</template>

<style scoped>
.page { padding: 40px; text-align: center; }
button {
  background: var(--accent); color: #fff; border: none;
  padding: 8px 16px; border-radius: 6px; cursor: pointer; margin-top: 12px;
}
</style>
