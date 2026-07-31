<script setup lang="ts">
import { RouterView } from 'vue-router'
import NavBar from './components/NavBar.vue'
import StatusBar from './components/StatusBar.vue'
</script>

<template>
  <div class="container">
    <header>
      <NavBar />
      <StatusBar />
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.container {
  max-width: 1100px; margin: 0 auto; padding: 16px 20px 60px;
}
header {
  display: flex; align-items: center; justify-content: space-between;
  padding-bottom: 16px; border-bottom: 1px solid var(--border);
  margin-bottom: 24px; flex-wrap: wrap; gap: 12px;
}
</style>
