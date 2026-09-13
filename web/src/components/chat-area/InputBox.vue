/**
 * 输入框组件
 *
 * 对话输入区域，支持发送消息和取消操作。
 */

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  sessionId: string
}>()

const emit = defineEmits<{
  (e: 'send', content: string): void
  (e: 'cancel'): void
}>()

const inputValue = ref('')

function handleSend() {
  if (!inputValue.value.trim()) return
  emit('send', inputValue.value.trim())
  inputValue.value = ''
}

function handleCancel() {
  emit('cancel')
}
</script>

<template>
  <div class="input-box">
    <textarea
      v-model="inputValue"
      placeholder="输入消息..."
      rows="1"
      @keydown.enter.ctrl="handleSend"
    />
    <div class="input-actions">
      <button @click="handleSend">发送</button>
      <button @click="handleCancel">取消</button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.input-box {
  padding: 12px 16px;
  border-top: 1px solid #e0e0e0;
  background-color: #fafafa;
}

textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  resize: none;
  font-family: inherit;
  font-size: 14px;
}

.input-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  justify-content: flex-end;
}

button {
  padding: 6px 16px;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;

  &:first-child {
    background-color: #0066cc;
    color: #fff;
    border-color: #0066cc;
  }
}
</style>
