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
        name: 'Overview',
        component: () => import('@/views/Overview.vue'),
        meta: { title: '总览' }
      },
      {
        path: 'chat/:id',
        name: 'Chat',
        component: () => import('@/views/Chat.vue'),
        meta: { title: '对话' }
      },
      {
        path: 'inspector',
        name: 'Inspector',
        component: () => import('@/views/Inspector.vue'),
        meta: { title: 'Inspector' }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/Settings.vue'),
        meta: { title: '设置' }
      },
      {
        path: 'audit',
        name: 'AuditLog',
        component: () => import('@/views/AuditLog.vue'),
        meta: { title: '审计日志' }
      },
      {
        path: 'search',
        name: 'Search',
        component: () => import('@/views/Search.vue'),
        meta: { title: '搜索' }
      },
      {
        path: 'scheduled-tasks',
        name: 'ScheduledTasks',
        component: () => import('@/views/ScheduledTasks.vue'),
        meta: { title: '定时任务' }
      },
      {
        path: 'browser',
        name: 'Browser',
        component: () => import('@/views/Browser.vue'),
        meta: { title: '浏览器控制' }
      },
      {
        path: 'packages',
        name: 'PackageManager',
        component: () => import('@/views/PackageManager.vue'),
        meta: { title: '包管理' }
      },
      {
        path: 'skills',
        name: 'SkillManager',
        component: () => import('@/views/SkillManager.vue'),
        meta: { title: 'Skill 管理' }
      },
      {
        path: 'daily-review',
        name: 'DailyReview',
        component: () => import('@/views/DailyReview.vue'),
        meta: { title: '每日回顾' }
      },
      {
        path: 'long-term-plan',
        name: 'LongTermPlan',
        component: () => import('@/views/LongTermPlan.vue'),
        meta: { title: '长期计划' }
      },
      {
        path: 'archive',
        name: 'Archive',
        component: () => import('@/views/Archive.vue'),
        meta: { title: '归档' }
      }
    ]
  }
]

const router = createRouter({
  history: location.protocol === 'file:' ? createWebHashHistory() : createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

export default router
