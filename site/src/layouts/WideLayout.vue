<template>
  <div class="container">
    <div class="main-content">
      <header>
        <h1>
          <slot name="header"></slot>
        </h1>
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

<script lang="ts" setup></script>

<style scoped>
  .container {
    display: flex;
    justify-content: center;
    /* align-items: center; */
    height: 100vh;
  }

  .main-content {
    /* flex-grow: 1; */

    display: flex;
    flex-direction: column;
    justify-content: start;
    align-items: center;
    text-align: center;
    width: 50%;
    /* margin-bottom: 50vh; */
    padding: 1rem;
    max-width: 960px;
  }
</style>
