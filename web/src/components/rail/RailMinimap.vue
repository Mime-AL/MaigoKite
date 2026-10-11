<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, shallowRef, watch } from 'vue'
import { inkBuckets, type PositionedNode } from '@/utils/rail-minimap'
const props = defineProps<{
  nodes: { id: string; turnId: string }[]
  scrollRoot?: HTMLElement | null
}>()
const emit = defineEmits<{ (event: 'jump', node: { id: string; turnId: string }): void }>()
const buckets = shallowRef<ReturnType<typeof inkBuckets>>([])
let alive = true, observation = 0
let frame = 0,
  resize: ResizeObserver | undefined,
  mutations: MutationObserver | undefined
function measure() {
  frame = 0
  const root = props.scrollRoot
  if (!root) {
    buckets.value = []
    return
  }
  const bounds = root.getBoundingClientRect()
  const buttons = new Map(
    Array.from(root.querySelectorAll<HTMLElement>('[data-rail-node]')).map((element) => [
      element.dataset.railNode,
      element,
    ]),
  )
  const positioned: PositionedNode[] = []
  for (const node of props.nodes) {
    let element = buttons.get(node.turnId + ':' + node.id)
    if (!element) continue // Paginated history is not assigned a fabricated position.
    let parent = element.parentElement
    while (parent && parent !== root) {
      if (parent instanceof HTMLDetailsElement && !parent.open)
        element = parent.querySelector<HTMLElement>(':scope > summary') || element
      parent = parent.parentElement
    }
    const rect = element.getBoundingClientRect()
    if (!rect.height) continue
    positioned.push({
      node,
      position:
        (rect.top + rect.height / 2 - bounds.top + root.scrollTop) /
        Math.max(root.scrollHeight, root.clientHeight, 1),
    })
  }
  buckets.value = inkBuckets(positioned)
}
function schedule() {
  if (alive && !frame) frame = requestAnimationFrame(measure)
}
function disconnect() {
  resize?.disconnect()
  mutations?.disconnect()
  if (frame) cancelAnimationFrame(frame)
  frame = 0
}
async function observe() {
  const current = ++observation
  disconnect()
  await nextTick()
  if (!alive || current !== observation) return
  const root = props.scrollRoot
  if (!root) return
  resize = new ResizeObserver(schedule)
  resize.observe(root)
  let content = root.querySelector('.messages-inner')
  if (content) resize.observe(content)
  mutations = new MutationObserver(() => {
    const next = root.querySelector('.messages-inner')
    if (next !== content) {
      if (content) resize?.unobserve(content)
      content = next
      if (content) resize?.observe(content)
    }
    schedule()
  })
  // Text deltas don't need a mutation callback; resize tracks real content height.
  mutations.observe(root, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: ['open', 'aria-expanded'],
  })
  schedule()
}
watch(() => props.scrollRoot, observe, { flush: 'post' })
// Stream deltas replace Turn identities, not node positions. Measure only when
// identities/layout change, never rescan the DOM for every text delta.
watch(() => props.nodes.map(node => node.turnId + ':' + node.id).join('|'), schedule, { flush: 'post' })
onMounted(observe)
onBeforeUnmount(() => { alive = false; observation++; disconnect() })
</script>
<template>
  <nav
    v-if="buckets.length"
    class="rail-minimap"
    :aria-label="$t('墨线缩略图')"
  >
    <button
      v-for="bucket in buckets"
      :key="bucket.slot"
      :style="{ top: bucket.top + '%', '--ink-density': bucket.density }"
      :aria-label="$t('跳到步骤 {0}', [bucket.slot + 1])"
      @click="emit('jump', bucket.node)"
    >
      <span />
    </button>
  </nav>
</template>
<style scoped lang="scss">
.rail-minimap {
  position: absolute;
  inset-block: var(--space-5);
  inset-inline-end: var(--space-1);
  width: var(--minimap-width);
  z-index: 3;
}
button {
  position: absolute;
  display: grid;
  place-items: center;
  width: var(--minimap-width);
  height: var(--minimap-mark-height);
  border: 0;
  padding: 0;
  background: var(--transparent);
  border-radius: var(--radius-sm);
}
button span {
  width: calc(var(--minimap-width) - var(--space-2));
  height: var(--minimap-mark-height);
  border-radius: var(--radius-sm);
  background: var(--ink-2);
  opacity: calc(var(--minimap-low-opacity) + var(--ink-density) * (1 - var(--minimap-low-opacity)));
}
button:hover span,
button:focus-visible span {
  opacity: 1;
  background: var(--accent);
}
</style>
