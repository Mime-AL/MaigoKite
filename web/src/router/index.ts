/**
 * Vue Router 配置
 *
 * 定义所有页面路由和懒加载组件。
 */

import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    children: [
      {
        path: '',
        redirect: '/chat',
      },
      {
        path: 'overview',
        name: 'Overview',
        component: () => import('@/views/Overview.vue'),
        meta: { title: '概览' },
      },
      {
        path: 'chat/:id?',
        name: 'Chat',
        component: () => import('@/views/Chat.vue'),
        meta: { title: '对话' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/Settings.vue'),
        meta: { title: '设置' },
      },
      {
        path: 'audit',
        name: 'AuditLog',
        component: () => import('@/views/AuditLog.vue'),
        meta: { title: '审计日志' },
      },
      {
        path: 'memory',
        name: 'Memory',
        component: () => import('@/views/Memory.vue'),
        meta: { title: '它记得' },
      },
      {
        path: 'integrations',
        name: 'Integrations',
        component: () => import('@/views/Integrations.vue'),
        meta: { title: '扩展' },
      },
      {
        path: 'embedding-indexes',
        name: 'EmbeddingIndexes',
        component: () => import('@/views/EmbeddingIndexes.vue'),
        meta: { title: '知识库' },
      },
      {
        path: 'data',
        name: 'DataManagement',
        component: () => import('@/views/DataManagement.vue'),
        meta: { title: '数据概览' },
      },
    ],
  },
]

routes.push({
  path: '/capsule',
  name: 'Capsule',
  component: () => import('@/views/Capsule.vue'),
  meta: { title: '速记' },
})

const router = createRouter({
  history: location.protocol === 'file:' ? createWebHashHistory() : createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

export default router
