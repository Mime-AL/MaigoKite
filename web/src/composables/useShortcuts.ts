import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUIStore } from '@/stores/ui'
import { useSessionStore } from '@/stores/session'
import { useInboxStore } from '@/stores/inbox'

export function useShortcuts() {
  const ui = useUIStore(),
    session = useSessionStore(),
    inbox = useInboxStore(),
    router = useRouter()
  let nodeIndex = -1
  async function newPage() {
    const item = await session.createSession('新对话')
    await router.push(`/chat/${item.id}`)
  }
  function onKey(event: KeyboardEvent) {
    if (event.isComposing) return
    const target = event.target as HTMLElement | null
    const editing = Boolean(target?.closest('input,textarea,select,[contenteditable="true"]'))
    const modifier = event.ctrlKey || event.metaKey
    const key = event.key.toLowerCase()
    const modal = document.querySelector<HTMLDialogElement>('dialog[open]')
    if (modal) {
      // Native dialogs handle Tab and Escape; do not operate the inert chat behind them.
      if (
        modal.classList.contains('inbox-shade') &&
        !editing &&
        !modifier &&
        !event.altKey &&
        ['y', 'n'].includes(key)
      ) {
        const pending = inbox.items[0]
        if (pending?.mode === 'approval')
          modal
            .querySelector<HTMLButtonElement>(
              `[data-await="${CSS.escape(pending.id)}"] [data-verdict="${key === 'y' ? 'allow' : 'deny'}"]:not(:disabled)`,
            )
            ?.click()
        event.preventDefault()
      }
      return
    }
    if (modifier && ['k', 'j', 'n', 'b', '.', '/'].includes(key)) {
      event.preventDefault()
      if (key === 'k') ui.commandOpen = !ui.commandOpen
      if (key === 'j') ui.inboxOpen = !ui.inboxOpen
      if (key === 'n') void newPage().catch(() => undefined)
      if (key === 'b') ui.layout.toggleSidebar()
      if (key === '.') ui.drawerOpen = !ui.drawerOpen
      if (key === '/') ui.shortcutsOpen = !ui.shortcutsOpen
      return
    }
    if (key === 'escape') {
      if (ui.drawerOpen || ui.inboxOpen || ui.commandOpen || ui.shortcutsOpen) ui.closeOverlays()
      else void session.cancelActiveTask().catch(() => undefined)
      return
    }
    if (editing || modifier || event.altKey) return
    if (['y', 'n'].includes(key)) {
      const pending = inbox.items.find(
        (a) => ui.inboxOpen || a.sessionId === session.activeSessionId,
      )
      if (pending?.mode === 'approval') {
        event.preventDefault()
        document
          .querySelector('main.main-content')
          ?.querySelector<HTMLElement>(
            `[data-await="${CSS.escape(pending.id)}"] [data-verdict="${key === 'y' ? 'allow' : 'deny'}"]`,
          )
          ?.click()
      }
    }
    if (key === '[' || key === ']') {
      const nodes = Array.from(document.querySelectorAll<HTMLButtonElement>('[data-rail-node]'))
      nodeIndex = Math.max(0, Math.min(nodes.length - 1, nodeIndex + (key === ']' ? 1 : -1)))
      nodes[nodeIndex]?.focus({ preventScroll: true })
      nodes[nodeIndex]?.scrollIntoView({ block: 'center' })
      event.preventDefault()
    }
  }
  onMounted(() => window.addEventListener('keydown', onKey))
  onUnmounted(() => window.removeEventListener('keydown', onKey))
}
