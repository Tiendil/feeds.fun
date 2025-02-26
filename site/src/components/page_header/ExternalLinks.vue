<template>
  <a
    v-if="showApi"
    href="/api/docs"
    target="_blank"
    class="ffun-page-header-link"
    @click="events.socialLinkClicked({linkType: 'api'})"
    >API</a
  >

  <a
    v-if="settings.blog"
    :href="settings.blog"
    target="_blank"
    class="ffun-page-header-link"
    @click="events.socialLinkClicked({linkType: 'blog'})"
    >Blog</a
  >

  <a
    v-if="settings.redditSubreddit"
    :href="settings.redditSubreddit"
    target="_blank"
    class="ffun-page-header-link text-xl align-middle"
    title="Reddit"
    @click="events.socialLinkClicked({linkType: 'reddit'})"
    ><i class="ti ti-brand-reddit"></i
  ></a>

  <a
    v-if="settings.discordInvite"
    :href="settings.discordInvite"
    target="_blank"
    class="ffun-page-header-link text-xl align-middle"
    title="Discord"
    @click="events.socialLinkClicked({linkType: 'discord'})"
    ><i class="ti ti-brand-discord"></i
  ></a>

  <a
    v-if="settings.githubRepo"
    :href="settings.githubRepo"
    target="_blank"
    class="ffun-page-header-link text-xl align-middle"
    title="GitHub"
    @click="events.socialLinkClicked({linkType: 'github'})">
    <i class="ti ti-brand-github"></i
  ></a>
</template>

<script lang="ts" setup>
  import {ref, computed, useSlots, onMounted, watch, watchEffect} from "vue";

  import * as events from "@/logic/events";
  import * as settings from "@/logic/settings";

  const properties = defineProps<{showApi: boolean}>();
</script>
