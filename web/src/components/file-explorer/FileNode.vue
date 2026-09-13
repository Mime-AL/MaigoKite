/**
 * 单个文件节点组件
 *
 * 渲染文件树中的一个节点，支持展开/收起目录。
 */

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  node: {
    name: string
    path: string
    type: 'file' | 'directory'
    children?: any[]
  }
  depth: number
}>()

const emit = defineEmits<{
  (e: 'expand', node: any): void
  (e: 'select', node: any): void
}>()

const isExpanded = ref(false)

watch(
  () => props.node.type,
  (type) => {
    if (type === 'directory') {
      // 默认展开第一层
      if (props.depth < 1) isExpanded.value = true
    }
  }
)

function handleClick() {
  emit('select', props.node)
  if (props.node.type === 'directory') {
    emit('expand', props.node)
  }
}
</script>

<template>
  <div class="file-node" :style="{ paddingLeft: depth * 16 + 'px' }">
    <div class="node-content" :class="node.type" @click="handleClick">
      <span class="node-icon">
        {{ node.type === 'directory' ? (isExpanded ? '📂' : '📁') : '📄' }}
      </span>
      <span class="node-name">{{ node.name }}</span>
    </div>
    <template v-if="node.type === 'directory' && isExpanded && node.children">
      <FileNode
        v-for="child in node.children"
        :key="child.path"
        :node="child"
        :depth="depth + 1"
        @expand="$emit('expand', $event)"
        @select="$emit('select', $event)"
      />
    </template>
  </div>
</template>

<style scoped lang="scss">
.file-node {
  user-select: none;
}

.node-content {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  cursor: pointer;
  border-radius: 4px;

  &:hover {
    background-color: #f0f0f0;
  }
}

.node-icon {
  font-size: 14px;
}

.node-name {
  font-size: 13px;
}
</style>
