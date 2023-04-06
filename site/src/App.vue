<template>
<div class="container">
  <div class="nav-panel">
    <h2>Feeds For Fun</h2>
    <nav>
      <router-link :to="{ name: 'feeds' }">feeds</router-link> |
      <router-link :to="{ name: 'entries' }">entries</router-link>
    </nav>
  </div>

  <div class="main-content">
    <h1>Main Content</h1>
    <router-view />
  </div>
</div>
</template>


<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<style scoped>

.container {
    display: flex;
    height: 100vh;
  }

  .nav-panel {
    width: 10em;
    flex-shrink: 0;
    background-color: #f0f0f0;
    padding: 1rem;
  }

  .main-content {
    flex-grow: 1;
    padding: 1rem;
}

</style>
