<template>
    <header>
        <div class="wrapper">
            <nav>
              <router-link :to="{ name: 'main' }">FeedsFun</router-link> |
              <router-link :to="{ name: 'feeds' }">feeds</router-link> |
              <router-link :to="{ name: 'entries' }">entries</router-link>
            </nav>
        </div>
    </header>

    <router-view />
</template>


<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<style scoped></style>
