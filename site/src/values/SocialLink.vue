<template>
  <a
    v-if="link.enabled"
    :href="link.url"
    target="_blank"
    @click="events.socialLinkClicked({linkType: link.eventType, view: eventsView})">
    <span v-if="mode === 'text'">
      {{ link.text }}

      <icon
        icon="external-link"
        size="small" />
    </span>

    <icon
      v-else
      :icon="link.icon" />
  </a>
</template>

<script lang="ts" setup>
  import {inject, computed} from "vue";

  import * as events from "@/logic/events";
  import * as settings from "@/logic/settings";
  import * as asserts from "@/logic/asserts";

  import {useGlobalState} from "@/stores/globalState";

  const globalState = useGlobalState();

  const links = {
    roadmap: {
      enabled: true,
      url: settings.roadmap,
      text: "Roadmap",
      icon: null,
      eventType: "roadmap"
    },
    blog: {
      enabled: settings.blog !== null,
      url: settings.blog,
      text: "Blog",
      icon: null,
      eventType: "blog"
    },
    reddit: {
      enabled: settings.redditSubreddit !== null,
      url: settings.redditSubreddit,
      text: "Reddit",
      icon: "reddit",
      eventType: "reddit"
    },
    discord: {
      enabled: settings.discordInvite !== null,
      url: settings.discordInvite,
      text: "Discord",
      icon: "discord",
      eventType: "discord"
    },
    github: {
      enabled: settings.githubRepo !== null,
      url: settings.githubRepo,
      text: "GitHub",
      icon: "github",
      eventType: "github"
    }
  };

  type LinkKind = keyof typeof links;

  const properties = defineProps<{kind: LinkKind; mode: "icon" | "text"}>();

  const eventsView = inject<events.EventsViewName>("eventsViewName");

  asserts.defined(eventsView);

  const link = computed(() => {
    if (properties.kind in links) {
      return links[properties.kind];
    }

    throw new Error(`Link kind "${properties.kind}" not found`);
  });
</script>
