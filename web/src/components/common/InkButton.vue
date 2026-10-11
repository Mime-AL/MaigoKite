<script setup lang="ts">
withDefaults(
  defineProps<{ tone?: 'plain' | 'primary' | 'danger'; disabled?: boolean; loading?: boolean }>(),
  {
    tone: 'plain',
    disabled: false,
    loading: false,
  },
)
</script>
<template>
  <button
    type="button"
    class="ink-button"
    :class="[tone, tone === 'plain' ? 'secondary-button' : `${tone}-button`]"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
  >
    <slot />
  </button>
</template>
<style scoped lang="scss">
.ink-button {
  min-height: var(--space-8);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
}
</style>
