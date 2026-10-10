<script setup lang="ts">
import { ref } from 'vue'
import type { AwaitItem } from '@/api/events'
import { useInboxStore } from '@/stores/inbox'
import InkButton from '@/components/common/InkButton.vue'
const props = defineProps<{ item: AwaitItem }>()
const inbox = useInboxStore()
const answer = ref(''), failure = ref('')
async function submit() {
  if (!answer.value.trim() || inbox.busy.includes(props.item.id)) return
  failure.value = ''
  try {
    await inbox.answer(props.item, answer.value)
  } catch (reason) {
    failure.value = reason instanceof Error ? reason.message : String(reason)
  }
}
</script>
<template>
  <article class="question-card">
    <strong>{{ item.title }}</strong>
    <p v-if="item.detail">{{ item.detail }}</p>
    <form @submit.prevent="submit">
      <div v-if="item.options?.length" class="options">
        <button v-for="option in item.options" :key="option.label" type="button"
          class="secondary-button" :aria-pressed="answer === option.label"
          :disabled="inbox.busy.includes(item.id)" @click="answer = option.label">
          {{ option.label }}{{ option.recommended ? $t(' · 推荐') : '' }}
        </button>
      </div>
      <label>{{ $t('你的回答') }}<textarea v-model="answer" rows="3" maxlength="10000"
        :disabled="inbox.busy.includes(item.id)" :placeholder="$t('选择建议答案，或输入自己的回答')" /></label>
      <p v-if="failure" role="alert">{{ failure }}</p>
      <InkButton tone="primary" :loading="inbox.busy.includes(item.id)"
        :disabled="!answer.trim() || inbox.busy.includes(item.id)" @click="submit">
        {{ inbox.busy.includes(item.id) ? $t('正在提交…') : $t('回答并继续') }}
      </InkButton>
    </form>
  </article>
</template>
<style scoped lang="scss">
.question-card {
  border-left: 2px solid var(--wait);
  padding: 12px 16px;
  color: var(--ink);
  background: var(--paper-2);
  font-size: var(--text-sm);
}
form, label {
  display: grid;
  gap: 8px;
  margin-top: 8px;
}
.options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
textarea {
  width: 100%;
}
button[aria-pressed='true'] {
  color: var(--accent);
}
</style>
