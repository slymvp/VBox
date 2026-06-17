<template>
  <div class="pc-layout">
    <main class="content">
      <slot />
    </main>
  </div>
</template>

<style lang="scss">
.pc-layout {
  min-height: 100vh;
  background: var(--background);
}
</style>
