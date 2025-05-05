<template>
  <a
    v-if="showApi"
    href="/api/docs"
    target="_blank"
    class="ffun-page-header-link"
    @click="events.socialLinkClicked({linkType: 'api', view: eventsView})"
    >API</a
  >

  <a
    v-if="settings.blog"
    :href="settings.blog"
    target="_blank"
    class="ffun-page-header-link"
    @click="events.socialLinkClicked({linkType: 'blog', view: eventsView})"
    >Blog</a
  >

  <a
    v-if="settings.redditSubreddit"
    :href="settings.redditSubreddit"
    target="_blank"
    class="ffun-page-header-link py-2 flex items-center justify-center"
    title="Reddit"
    @click="events.socialLinkClicked({linkType: 'reddit', view: eventsView})">
    <icon icon="reddit" />
  </a>

  <a
    v-if="settings.discordInvite"
    :href="settings.discordInvite"
    target="_blank"
    class="ffun-page-header-link py-2 flex items-center justify-center"
    title="Discord"
    @click="events.socialLinkClicked({linkType: 'discord', view: eventsView})">
    <icon icon="discord" />
  </a>

  <a
    v-if="settings.githubRepo"
    :href="settings.githubRepo"
    target="_blank"
    class="ffun-page-header-link py-2 flex items-center justify-center"
    title="GitHub"
    @click="events.socialLinkClicked({linkType: 'github', view: eventsView})">
    <icon icon="github" />
  </a>
</template>

<script lang="ts" setup>
  import {inject} from "vue";

  import * as events from "@/logic/events";
  import * as settings from "@/logic/settings";
  import * as asserts from "@/logic/asserts";

  const properties = defineProps<{showApi: boolean}>();

  const eventsView = inject<events.EventsViewName>("eventsViewName");

  asserts.defined(eventsView);
</script>
