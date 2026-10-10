<script setup lang="ts">
import { computed, ref } from 'vue'
import { api, type MCPConfiguration, type ManagedSkill } from '@/api/client'
import { useExtensions } from '@/composables/useExtensions'
import { t } from '@/i18n'

const { snapshot, busy, error, notice, perform, refresh, save, apply, restore } = useExtensions()
const tab = ref<'mcp' | 'skills'>('mcp')
const editable = computed(() => !!snapshot.value && snapshot.value.management_available !== false && !busy.value && !snapshot.value.reloading)
const server = ref<MCPConfiguration | null>(null)
const editingServer = ref(false)
const argumentsText = ref('')
const inheritedEnv = ref('')
const credentialNames = ref('')
const credentialName = ref('')
const credentialValue = ref('')
const credentialServer = ref('')
const skill = ref<ManagedSkill | null>(null)
const editingSkill = ref(false)
const directories = ref<string | null>(null)
const removed = ref<{ kind: 'mcp' | 'skill'; name: string } | null>(null)
const splitLines = (value: string) => value.split('\n').map((line) => line.trim()).filter(Boolean)
function editServer(item?: MCPConfiguration) {
  server.value = item ? JSON.parse(JSON.stringify(item)) : {
    namespace: '', transport: 'stdio', command: '', args: [], cwd: '', enabled: true,
    env_allowlist: [], secret_env: [], enabled_tools: null, disabled_tools: [],
  }
  editingServer.value = !!item
  argumentsText.value = item?.args.join('\n') || ''
  inheritedEnv.value = item?.env_allowlist.join('\n') || ''
  credentialNames.value = item?.secret_env.join('\n') || ''
}
async function saveServer() {
  const current = server.value
  if (!current) return
  const item = { ...current, args: argumentsText.value.split('\n').filter((line) => line.length > 0),
    env_allowlist: splitLines(inheritedEnv.value), secret_env: splitLines(credentialNames.value) }
  if (await save((config) => {
    const index = config.mcp_servers.findIndex((row) => row.namespace === item.namespace)
    if (!editingServer.value && index >= 0) throw new Error(t('扩展名称已存在。'))
    if (index < 0) config.mcp_servers.push(item)
    else config.mcp_servers[index] = item
  })) server.value = null
}
function editSkill(item?: ManagedSkill) {
  editingSkill.value = !!item
  skill.value = item ? { ...item } : { name: 'my-workflow', enabled: true,
    content: '---\nname: my-workflow\ndescription: Describe the use case and deliverable\n---\nDefine steps, required tools, and stop conditions.\n' }
}
async function importSkill(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !skill.value) return
  await perform(async () => {
    if (file.size > 256 * 1024) throw new Error(t('技能文件不能超过 256 KiB。'))
    if (skill.value) skill.value.content = await file.text()
  })
  input.value = ''
}
async function saveSkill() {
  const item = skill.value
  if (!item) return
  if (await save((config) => {
    const index = config.skills.findIndex((row) => row.name === item.name)
    if (!editingSkill.value && index >= 0) throw new Error(t('扩展名称已存在。'))
    if (index < 0) config.skills.push({ ...item })
    else config.skills[index] = { ...item }
  })) skill.value = null
}
async function saveDirectories() {
  if (await save((config) => { config.skill_directories = splitLines(directories.value || '') })) directories.value = null
}
async function remove() {
  const target = removed.value
  if (!target) return
  if (await save((config) => {
    if (target.kind === 'mcp') config.mcp_servers = config.mcp_servers.filter((row) => row.namespace !== target.name)
    else config.skills = config.skills.filter((row) => row.name !== target.name)
  })) {
    removed.value = null
    if (target.kind === 'mcp' && credentialServer.value === target.name) {
      credentialServer.value = credentialValue.value = ''
    }
  }
}
function toggleServer(namespace: string) {
  void save((config) => { const row = config.mcp_servers.find((item) => item.namespace === namespace); if (row) row.enabled = !row.enabled })
}
function toggleSkill(name: string, managed: boolean) {
  void save((config) => {
    if (managed) { const row = config.skills.find((item) => item.name === name); if (row) row.enabled = !row.enabled }
    else config.disabled_skills = config.disabled_skills.includes(name) ? config.disabled_skills.filter((item) => item !== name) : [...config.disabled_skills, name]
  })
}
function state(namespace: string) {
  const value = snapshot.value?.servers.find((item) => item.namespace === namespace)?.status
  const labels: Record<string, string> = {
    running: '运行中', disabled: '已停用', connecting: '正在连接',
    error: '连接失败，请检查命令和环境', needs_credentials: '需要凭证，请配置后连接',
    timeout: '连接超时', invalid_cwd: '工作目录不可用', disconnected: '连接已断开，请重新连接',
  }
  return t(labels[value || ''] || '尚未加载')
}
function openCredentials(namespace: string, names: string[]) {
  credentialServer.value = namespace
  credentialName.value = names[0] || ''
  credentialValue.value = ''
}
async function saveCredential(removeValue = false) {
  await perform(async () => {
    const reference = `mcp.${credentialServer.value}.${credentialName.value}`
    if (removeValue) await api.deleteCredential(reference)
    else await api.saveCredential(reference, credentialValue.value)
    credentialValue.value = ''
    notice.value = t('凭证已更新，重新连接后生效。')
  })
}
const directorySkills = computed(() => snapshot.value?.skills.filter((row) => !row.source_path.startsWith('managed:')) || [])
const selectedCredentialNames = computed(() => snapshot.value?.config.mcp_servers.find((item) => item.namespace === credentialServer.value)?.secret_env || [])
</script>

<template>
  <main class="page-shell extensions-page">
    <header class="section-heading">
      <div><h1 class="page-title">{{ $t('扩展') }}</h1><p>{{ $t('用 MCP 接入工具，用 Skill 定制自己的工作方式。') }}</p></div>
      <div class="actions"><button class="secondary-button" :disabled="busy" @click="refresh">{{ $t('刷新') }}</button><button v-if="snapshot?.active_config" class="secondary-button" :disabled="!editable" @click="restore">{{ $t('恢复已有连接') }}</button><button class="primary-button" :disabled="!editable" @click="apply">{{ $t('应用并检查连接') }}</button></div>
    </header>
    <p class="help">{{ $t('保存不会打断当前任务。应用时会重新扫描技能、重连外部工具；请先结束任务与待处理审批。') }}</p>
    <p class="help">{{ $t('有待处理审批时可恢复已有连接，不应用新配置。运行中的任务仍须先结束。') }}</p>
    <p v-if="snapshot?.management_available === false" class="notice">{{ $t('演示模式不启动进程或安装扩展，请连接实际服务。') }}</p>
    <p v-if="snapshot?.reloading" role="status">{{ $t('正在应用扩展，可刷新查看结果，请勿重复提交。') }}</p>
    <p v-else-if="snapshot?.reload_required" class="notice">{{ $t('有已保存但尚未应用的更改。') }}</p>
    <p v-if="snapshot && !snapshot.runtime_ready && !snapshot.reloading" class="error-banner">{{ $t('运行时尚未就绪，请重新应用或重启服务。') }}</p>
    <p v-if="error" class="error-banner" role="alert">{{ error }}</p>
    <p v-if="snapshot?.extension_error" class="error-banner" role="alert">{{ snapshot.extension_error }}</p>
    <p v-if="notice" class="notice" role="status">{{ notice }}</p>
    <nav class="actions" :aria-label="$t('扩展分类')"><button class="secondary-button" :aria-pressed="tab === 'mcp'" @click="tab = 'mcp'">MCP</button><button class="secondary-button" :aria-pressed="tab === 'skills'" @click="tab = 'skills'">Skills</button></nav>

    <section v-if="tab === 'mcp'">
      <div class="section-heading"><h2>{{ $t('外部工具服务') }}</h2><button class="secondary-button" :disabled="!editable" @click="editServer()">{{ $t('添加 MCP') }}</button></div>
      <p class="help">{{ $t('目前支持本地 stdio 服务。添加服务意味着允许运行该程序，请只使用可信来源；不要在启动参数中填写密钥。') }}</p>
      <form v-if="server" class="glass-card editor" @submit.prevent="saveServer"><fieldset :disabled="!editable">
        <label>{{ $t('名称标识') }}<input v-model="server.namespace" required pattern="[a-z][a-z0-9_-]{0,47}" :disabled="editingServer" placeholder="my-tools" /></label>
        <label>{{ $t('可执行程序') }}<input v-model="server.command" required placeholder="uvx / npx / python" /></label>
        <label>{{ $t('启动参数，每行一个') }}<textarea v-model="argumentsText" rows="3" /></label>
        <label>{{ $t('工作目录（留空使用默认工作区）') }}<input v-model="server.cwd" /></label>
        <label>{{ $t('继承的环境变量名，每行一个') }}<textarea v-model="inheritedEnv" rows="2" /></label>
        <label>{{ $t('凭证环境变量名，每行一个') }}<textarea v-model="credentialNames" rows="2" placeholder="API_KEY" /></label>
        <label class="check"><input v-model="server.enabled" type="checkbox" />{{ $t('启用') }}</label>
        <div class="actions"><button class="primary-button" type="submit">{{ $t('保存配置') }}</button><button class="secondary-button" type="button" @click="server = null">{{ $t('取消') }}</button></div>
      </fieldset></form>
      <p v-if="snapshot && !snapshot.config.mcp_servers.length">{{ $t('还没有连接外部工具') }}</p>
      <article v-for="item in snapshot?.config.mcp_servers" :key="item.namespace" class="glass-card extension-item">
        <div class="section-heading"><strong>{{ item.namespace }}</strong><span>{{ state(item.namespace) }}</span></div>
        <p class="help">{{ item.command }} · {{ item.enabled ? $t('配置：启用') : $t('配置：停用') }}</p>
        <p class="tools">{{ snapshot?.servers.find((row) => row.namespace === item.namespace)?.tool_names.join(' · ') }}</p>
        <div class="actions"><button class="secondary-button" :disabled="!editable" @click="editServer(item)">{{ $t('编辑') }}</button><button class="secondary-button" :disabled="!editable" @click="toggleServer(item.namespace)">{{ item.enabled ? $t('停用') : $t('启用') }}</button><button v-if="item.secret_env.length" class="secondary-button" :disabled="!editable" @click="openCredentials(item.namespace, item.secret_env)">{{ $t('配置凭证') }}</button><button class="secondary-button" :disabled="!editable" @click="removed = { kind: 'mcp', name: item.namespace }">{{ $t('移除') }}</button></div>
      </article>
      <form v-if="credentialServer" class="glass-card editor" @submit.prevent="saveCredential()"><fieldset :disabled="!editable">
        <h3>{{ $t('配置凭证') }} · {{ credentialServer }}</h3>
        <label>{{ $t('环境变量名') }}<select v-model="credentialName"><option v-for="name in selectedCredentialNames" :key="name">{{ name }}</option></select></label>
        <label>{{ $t('新的凭证值') }}<input v-model="credentialValue" type="password" autocomplete="new-password" /></label>
        <p class="help">{{ $t('凭证不会回显；保存或清除后，请点击应用以重新连接。') }}</p>
        <div class="actions"><button class="primary-button" type="submit" :disabled="!credentialValue || !credentialName">{{ $t('保存凭证') }}</button><button class="secondary-button" type="button" :disabled="!credentialName" @click="saveCredential(true)">{{ $t('清除凭证') }}</button><button class="secondary-button" type="button" @click="credentialServer = ''; credentialValue = ''">{{ $t('关闭') }}</button></div>
      </fieldset></form>
    </section>

    <section v-else>
      <div class="section-heading"><h2>{{ $t('个人技能') }}</h2><div class="actions"><button class="secondary-button" :disabled="!editable" @click="editSkill()">{{ $t('添加或导入技能') }}</button><button class="secondary-button" :disabled="!editable" @click="directories = snapshot?.config.skill_directories.join('\n') || ''">{{ $t('扫描目录') }}</button></div></div>
      <p class="help">{{ $t('导入 SKILL.md 指令，或扫描已有技能目录。不自动执行包内脚本，也不安装第三方依赖。') }}</p>
      <form v-if="directories !== null" class="glass-card editor" @submit.prevent="saveDirectories"><fieldset :disabled="!editable"><label>{{ $t('技能目录，每行一个') }}<textarea v-model="directories" rows="3" /></label><div class="actions"><button type="submit" class="primary-button">{{ $t('保存配置') }}</button><button type="button" class="secondary-button" @click="directories = null">{{ $t('取消') }}</button></div></fieldset></form>
      <form v-if="skill" class="glass-card editor" @submit.prevent="saveSkill"><fieldset :disabled="!editable">
        <label>{{ $t('名称标识（与 SKILL.md 的 name 一致）') }}<input v-model="skill.name" required :disabled="editingSkill" pattern="[a-z0-9][a-z0-9._-]{0,63}" /></label>
        <label>{{ $t('导入文件') }}<input type="file" accept=".md,text/markdown,text/plain" @change="importSkill" /></label>
        <label>SKILL.md<textarea v-model="skill.content" rows="12" required spellcheck="false" /></label>
        <label class="check"><input v-model="skill.enabled" type="checkbox" />{{ $t('启用') }}</label>
        <div class="actions"><button type="submit" class="primary-button">{{ $t('保存技能') }}</button><button type="button" class="secondary-button" @click="skill = null">{{ $t('取消') }}</button></div>
      </fieldset></form>
      <article v-for="item in snapshot?.config.skills" :key="item.name" class="glass-card extension-item">
        <div class="section-heading"><strong>{{ item.name }}</strong><span>{{ snapshot?.skills.some((row) => row.name === item.name && row.source_path.startsWith('managed:') && row.enabled) ? $t('已加载') : $t('未加载或已停用') }}</span></div>
        <p>{{ item.enabled ? $t('配置：启用') : $t('配置：停用') }}</p>
        <div class="actions"><button class="secondary-button" :disabled="!editable" @click="editSkill(item)">{{ $t('查看与编辑') }}</button><button class="secondary-button" :disabled="!editable" @click="toggleSkill(item.name, true)">{{ item.enabled ? $t('停用') : $t('启用') }}</button><button class="secondary-button" :disabled="!editable" @click="removed = { kind: 'skill', name: item.name }">{{ $t('移除') }}</button></div>
      </article>
      <article v-for="item in directorySkills" :key="item.source_path" class="glass-card extension-item">
        <strong>{{ item.name }}</strong><p>{{ item.description }}</p><small>{{ item.source_path }}</small><p>{{ item.enabled ? $t('已加载') : $t('已停用') }}</p>
        <button class="secondary-button" :disabled="!editable" @click="toggleSkill(item.name, false)">{{ snapshot?.config.disabled_skills.includes(item.name) ? $t('启用') : $t('停用') }}</button>
      </article>
      <p v-if="snapshot && !snapshot.skills.length && !snapshot.config.skills.length">{{ $t('还没有可用技能') }}</p>
      <p v-for="message in snapshot?.skill_errors" :key="message" class="error-banner">{{ message }}</p>
    </section>
    <section v-if="removed" class="glass-card editor" role="alert"><p>{{ $t('移除扩展 {0}？应用后停止加载；不会删除源目录或系统密钥链中的凭证。', [removed.name]) }}</p><div class="actions"><button class="primary-button" :disabled="!editable" @click="remove">{{ $t('确认移除') }}</button><button class="secondary-button" @click="removed = null">{{ $t('取消') }}</button></div></section>
  </main>
</template>

<style scoped lang="scss">
.extensions-page { display: grid; gap: 18px; }
.section-heading, .actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.actions { justify-content: flex-start; }
h2 { font-size: var(--text-sm); }
.help, small { color: var(--text-secondary); line-height: 1.6; overflow-wrap: anywhere; }
.extension-item, .editor { padding: 18px; margin-block: 14px; }
fieldset { border: 0; padding: 0; margin: 0; display: grid; gap: 14px; min-width: 0; }
label { display: grid; gap: 6px; font-size: var(--text-sm); }
input:not([type='checkbox']), textarea, select { width: 100%; box-sizing: border-box; border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 9px; color: var(--text-primary); background: var(--surface); font: inherit; }
textarea, .tools { font-family: var(--font-mono); overflow-wrap: anywhere; }
textarea { resize: vertical; }
.check { display: flex; align-items: center; }
.error-banner { color: var(--danger); padding: 12px; background: var(--danger-soft); border-radius: var(--radius-md); }
.notice { color: var(--text-secondary); }
button[aria-pressed='true'] { border-color: var(--accent); }
</style>
