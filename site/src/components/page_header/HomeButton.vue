<template>
  <a
    :href="router.resolve({name: 'main'}).href"
    class="ffun-page-header-link"
    @click.prevent="router.push({name: 'main'})">
    Home</a
           >
</template>

<script lang="ts" setup>

  import {useRouter} from "vue-router";

    const router = useRouter();


</script>
