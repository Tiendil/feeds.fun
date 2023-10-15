<template>
  <wide-layout>
    <template #header>
      Feeds Fun
      <small class="block text-lg font-normal">Personalized news for professionals</small>
    </template>

    <div class="max-w-md mx-auto">
      <div class="ffun-info-good">
        <supertokens-login />
      </div>

      <h2>News reader with tags</h2>

      <ul class="list-disc list-inside text-left">
        <li>Reader automatically assigns tags to news.</li>
        <li>You create rules to score news by tags.</li>
        <li>Filter and sort news how you want ⇒ read only what you want.</li>
      </ul>

      <h2>You are in control</h2>

      <ul class="list-disc list-inside text-left">
        <li
          ><a
            class="ffun-normal-link"
            :href="settings.githubRepo"
            target="_blank"
            >Open source</a
          >, self-hosted.</li
        >
        <li>No black box recommendation algorithms.</li>
        <li>No "smart" reordering.</li>
        <li>No ads.</li>
        <li>No selling of your data.</li>
      </ul>

      <h2>How it looks like</h2>
    </div>

    <img
      src="/news-filtering-example.png"
      alt="News filtering example" />
  </wide-layout>
</template>

<script lang="ts" setup>
  import * as settings from "@/logic/settings";
</script>
