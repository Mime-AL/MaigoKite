<script setup lang="ts">
import { onMounted } from 'vue'
import IconSymbol from '@/components/common/IconSymbol.vue'
import { usePhase2Store } from '@/stores/phase2'

const phase2 = usePhase2Store()
onMounted(() => { void phase2.loadMCPServers() })
</script>

<template>
  <main class="page-shell integrations-page">
    <header>
      <h1 class="page-title">扩展</h1>
      <p class="page-subtitle">查看当前可用的技能和外部工具。</p>
    </header>

    <section class="boundary glass-card">
      <IconSymbol name="shield" :size="19" />
      <div><strong>权限保护</strong><p>使用扩展时仍会遵循当前对话的权限设置。</p></div>
    </section>

    <section class="next-slice">
      <h2>技能 · {{ phase2.skills.length }}</h2>
      <div v-if="!phase2.skills.length" class="empty rich-empty glass-card"><span><IconSymbol name="sparkles" :size="25" /></span><strong>还没有可用技能</strong></div>
      <div v-else class="next-grid">
        <article v-for="skill in phase2.skills" :key="skill.name"><strong>{{ skill.name }}</strong><span>{{ skill.description }}</span><small>版本 {{ skill.version }}</small></article>
      </div>
    </section>

    <p v-if="phase2.mcpError" class="error-banner" role="alert">{{ phase2.mcpError }}</p>
    <section class="server-list glass-card">
      <div v-if="phase2.mcpLoading" class="empty">正在读取外部工具…</div>
      <div v-else-if="!phase2.mcpServers.length" class="empty rich-empty"><span><IconSymbol name="cube" :size="25" /></span><strong>还没有连接外部工具</strong></div>
      <template v-else>
        <article v-for="server in phase2.mcpServers" :key="server.namespace">
          <span class="server-icon"><IconSymbol name="cube" :size="19" /></span>
          <div><strong>{{ server.namespace }}</strong><small>{{ server.tool_names.length }} 个工具</small><p v-if="server.tool_names.length">{{ server.tool_names.join(' · ') }}</p></div>
          <span class="status" :class="server.status"><i />{{ server.status === 'running' ? '运行中' : '已停用' }}</span>
        </article>
      </template>
    </section>

  </main>
</template>

<style scoped lang="scss">
.integrations-page { display: flex; flex-direction: column; gap: 20px; }
.boundary { display: flex; align-items: center; gap: 12px; padding: 16px 18px; color: var(--primary-color); }
.boundary div { min-width: 0; flex: 1; color: var(--text-primary); }
.boundary strong { font-size: 12px; }
.boundary p { margin: 4px 0 0; color: var(--text-secondary); font-size: 10px; }
.server-list { overflow: hidden; }
.server-list article { display: flex; align-items: flex-start; gap: 12px; padding: 16px 18px; border-bottom: 1px solid var(--border-color); }
.server-list article:last-child { border-bottom: 0; }
.server-icon { display: grid; width: 38px; height: 38px; flex: none; place-items: center; border-radius: 11px; color: #8a63d2; background: rgba(138, 99, 210, .13); }
.server-list article > div { min-width: 0; flex: 1; }
.server-list strong { font-size: 12px; }
.server-list small { display: block; margin-top: 4px; color: var(--text-tertiary); font-size: 9px; }
.server-list p { margin: 9px 0 0; color: var(--text-secondary); font-family: var(--font-mono); font-size: 9px; line-height: 1.5; }
.status { display: flex; align-items: center; gap: 5px; color: var(--text-tertiary); font-size: 9.5px; }
.status i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.status.running { color: var(--success); }
.empty { display: grid; min-height: 210px; place-items: center; color: var(--text-tertiary); }
.rich-empty { align-content: center; justify-items: center; gap: 6px; text-align: center; }
.rich-empty span { display: grid; width: 50px; height: 50px; place-items: center; border-radius: 15px; color: #8a63d2; background: rgba(138, 99, 210, .13); }
.rich-empty strong { color: var(--text-primary); }
.rich-empty p { max-width: 470px; margin: 0; font-size: 10px; }
.error-banner { margin: 0; padding: 11px 13px; border-radius: 12px; color: var(--danger); background: var(--danger-soft); }
.next-slice h2 { margin: 0 0 11px; font-size: 13px; }
.next-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.next-grid article { display: flex; flex-direction: column; padding: 14px; border: 1px solid var(--border-color); border-radius: 13px; background: var(--surface); }
.next-grid strong { font-size: 11px; }
.next-grid span { margin-top: 5px; color: var(--text-tertiary); font-size: 9.5px; line-height: 1.45; }
.next-grid small { margin-top: 8px; overflow: hidden; color: var(--text-tertiary); font-family: var(--font-mono); font-size: 8px; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 850px) { .next-grid { grid-template-columns: 1fr; } }
</style>
