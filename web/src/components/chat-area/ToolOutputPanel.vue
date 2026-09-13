/**
 * 工具输出面板组件
 *
 * 展示 Agent 工具调用的输出结果。
 */

<script setup lang="ts">
import TerminalOutput from './TerminalOutput.vue'
import CollapseCard from '../common/CollapseCard.vue'

defineProps<{
  outputs?: Array<{
    tool_name: string
    output: string
    error?: string
    duration_ms?: number
  }>
}>()
</script>

<template>
  <CollapseCard title="工具输出">
    <TerminalOutput
      v-for="(output, index) in outputs"
      :key="index"
      :content="output.error || output.output"
      :title="output.tool_name"
    />
  </CollapseCard>
</template>
