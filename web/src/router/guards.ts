/**
 * 路由守卫
 *
 * 统一处理页面标题更新。当前本地主体访问由 Gateway 校验。
 */

import type { Router } from 'vue-router'

export function setupGuards(router: Router) {
  router.beforeEach((to, _from, next) => {
    // 更新页面标题
    const title = to.meta.title as string | undefined
    if (title) {
      document.title = `${title} - 助手`
    }
    next()
  })
}
