<template>
<footer class="border-t border-gray-200">
  <div class="mx-auto max-w-max px-4 py-2 grid grid-cols-2 sm:grid-cols-3 gap-8">

    <div class="flex flex-col items-center sm:items-start">
      <h3 class="text-lg font-semibold mb-4">Community</h3>
      <div class="flex flex-col space-y-2">
        <social-link kind="blog"    mode="text" class="hover:underline"/>
        <social-link kind="reddit"  mode="text" class="hover:underline"/>
        <social-link kind="discord" mode="text" class="hover:underline"/>
        <social-link kind="github"  mode="text" class="hover:underline"/>
      </div>
    </div>

    <div class="flex flex-col items-center sm:items-start">
      <h3 class="text-lg font-semibold mb-4">Feeds Fun</h3>
      <!-- extra links or info here -->
    </div>
  </div>
</footer>

</template>

<script lang="ts" setup>
  import {inject} from "vue";

  import * as events from "@/logic/events";
  import * as settings from "@/logic/settings";
  import * as asserts from "@/logic/asserts";

  const eventsView = inject<events.EventsViewName>("eventsViewName");

  asserts.defined(eventsView);
</script>
