import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', component: () => import('./views/SearchView.vue') },
  { path: '/documents', component: () => import('./views/DocumentsView.vue') },
  { path: '/chunks', component: () => import('./views/ChunksView.vue') },
  { path: '/watch-dirs', component: () => import('./views/WatchDirsView.vue') },
  { path: '/jobs', component: () => import('./views/JobsView.vue') },
  { path: '/:pathMatch(.*)*', component: () => import('./views/NotFoundView.vue') },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
