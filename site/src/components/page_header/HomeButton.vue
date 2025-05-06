<template>
  <a
    :href="router.resolve({name: 'main', params: {}}).href"
    class="ffun-page-header-link"
    >Home</a
           >
</template>

<script lang="ts" setup>

  import {useRouter} from "vue-router";

    const router = useRouter();


</script>
