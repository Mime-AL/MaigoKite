<template>
  <span
    class="ink-loader"
    role="status"
    :aria-label="$t('正在读取')"
  ><i /></span>
</template>
<style scoped lang="scss">
.ink-loader {
  display: block;
  height: var(--hairline);
  overflow: hidden;
  background: var(--rule);
}
.ink-loader i {
  display: block;
  width: 40%;
  height: 100%;
  background: var(--accent);
  animation: ink-load var(--motion-pulse) var(--ease) infinite;
}
</style>
