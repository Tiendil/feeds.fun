<template>
  <router-view />
</template>

<script setup lang="ts"></script>

<style scoped>
  .container {
    display: flex;
  }

  .nav-panel {
    width: 10rem;
    flex-shrink: 0;
    background-color: #f0f0f0;
    padding: 1rem;
  }

  .main-content {
    flex-grow: 1;
    padding: 1rem;
  }

  .config-menu {
    list-style-type: none;
    margin: 0;
    padding: 0;
  }

  .config-menu-item {
    margin-bottom: 1rem;
  }
</style>
