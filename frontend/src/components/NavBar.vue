<script setup lang="ts">
import { RouterLink } from 'vue-router'
const links = [
  { to: '/', label: '搜索' },
  { to: '/documents', label: '文档' },
  { to: '/chunks', label: '切片' },
  { to: '/watch-dirs', label: '监控目录' },
  { to: '/jobs', label: '任务' },
]
</script>

<template>
  <nav class="nav">
    <div class="brand"><span class="accent">kb-local</span> · 本地知识库</div>
    <div class="links">
      <RouterLink v-for="l in links" :key="l.to" :to="l.to" active-class="active">
        {{ l.label }}
      </RouterLink>
    </div>
  </nav>
</template>

<style scoped>
.nav {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 24px; border-bottom: 1px solid var(--border); flex-wrap: wrap; gap: 12px;
}
.brand { font-size: 16px; font-weight: 600; }
.brand .accent { color: var(--accent); }
.links { display: flex; gap: 16px; }
.links a {
  color: var(--text-dim); text-decoration: none; font-size: 13px;
  padding: 4px 8px; border-radius: 4px; transition: color 0.15s;
}
.links a:hover { color: var(--text); }
.links a.active { color: var(--accent); }
</style>
