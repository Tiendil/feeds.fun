<template>
  <div class="container">
    <div class="main-content">
      <header>
        <slot name="header"></slot>
      </header>

      <main>
        <slot></slot>
      </main>

      <footer>
        <slot name="footer"></slot>
      </footer>

    </div>
  </div>
</template>

<script lang="ts" setup>
</script>

<style scoped>

  .container {
    display: flex;
  }

  .main-content {
    flex-grow: 1;
    padding: 1rem;
  }

</style>
