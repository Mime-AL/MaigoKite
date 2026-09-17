/**
 * Vue 应用入口
 *
 * 创建 Vue 应用实例，挂载 Pinia 和 Router，挂载到 #app。
 */

import { createApp } from 'vue'
import App from './App.vue'
import pinia from './stores'
import router from './router'
import { setupGuards } from './router/guards'
import './assets/styles/globals.scss'

const app = createApp(App)

app.use(pinia)
app.use(router)
setupGuards(router)

app.mount('#app')
