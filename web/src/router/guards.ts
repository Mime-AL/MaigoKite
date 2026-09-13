/**
 * 路由守卫
 *
 * 处理页面标题更新和未登录跳转（预留）。
 */

import type { Router } from 'vue-router'

export function setupGuards(router: Router) {
  router.beforeEach((to, _from, next) => {
    // 更新页面标题
    const title = to.meta.title as string | undefined
    if (title) {
      document.title = `${title} - NanamiGopher`
    }

    // TODO: 在此添加认证守卫
    // if (!isAuthenticated && to.path !== '/login') {
    //   next('/login')
    //   return
    // }

    next()
  })

  router.afterEach((_to, _from) => {
    // TODO: 可在此记录页面访问统计
  })
}
