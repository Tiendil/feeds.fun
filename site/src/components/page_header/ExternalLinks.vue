<template>
  <social-link
    kind="blog"
    mode="text"
    class="ffun-page-header-link" />

  <social-link
    kind="roadmap"
    mode="text"
    class="ffun-page-header-link" />

  <social-link
    kind="reddit"
    mode="icon"
    class="ffun-page-header-link py-2 flex items-center justify-center" />

  <social-link
    kind="discord"
    mode="icon"
    class="ffun-page-header-link py-2 flex items-center justify-center" />

  <social-link
    kind="github"
    mode="icon"
    class="ffun-page-header-link py-2 flex items-center justify-center" />
</template>

<script lang="ts" setup>
  import {inject} from "vue";

  import * as events from "@/logic/events";
  import * as settings from "@/logic/settings";
  import * as asserts from "@/logic/asserts";

  const properties = defineProps<{}>();

  const eventsView = inject<events.EventsViewName>("eventsViewName");

  asserts.defined(eventsView);
</script>
