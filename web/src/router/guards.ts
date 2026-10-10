/**
 * 路由守卫
 *
 * 统一处理页面标题更新。当前本地主体访问由 Gateway 校验。
 */

import type { Router } from 'vue-router'
import { watch } from 'vue'
import { i18n, t } from '@/i18n'

export function setupGuards(router: Router) {
  watch(
    [router.currentRoute, i18n.global.locale],
    ([route]) => {
      const title = route.meta.title as string | undefined
      if (title) {
        document.title = `${t(title)} - MaigoKite`
      }
    },
    { immediate: true },
  )
}
