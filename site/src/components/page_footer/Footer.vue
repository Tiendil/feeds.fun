<template>
<footer class="border-t border-gray-200">
  <div class="mx-auto max-w-max px-4 py-2 grid grid-cols-2 sm:grid-cols-4 gap-8">
    <div class="flex flex-col col-span-2 items-center sm:items-start">
      <h3 class="text-lg font-semibold mb-4">Feeds Fun</h3>
      <div class="flex flex-col space-y-2">
        <div class="font-medium"> The project is in demo mode and free of charge </div>

        <div>
          © 2023‑{{ year }} Aliaksei Yaletski (<external-url
                                                 url="https://github.com/Tiendil"
                                                 text="Tiendil"
                                                 class="ffun-normal-link" />) and Feeds Fun contributors
        </div>

        <div>
          Site uses
          <external-url
            url="https://github.com/tabler/tabler-icons"
            text="Tabler Icons"
            class="ffun-normal-link" />, licensed under the
          <external-url
            url="https://github.com/tabler/tabler-icons/blob/main/LICENSE"
            text="MIT License"
            class="ffun-normal-link" />
        </div>
      </div>
    </div>

    <div class="flex flex-col items-center sm:items-start max-w-28">
      <h3 class="text-lg font-semibold mb-4">Community</h3>
      <div class="flex flex-col space-y-2">
        <social-link
          kind="blog"
          mode="text"
          class="hover:underline ffun-normal-link" />
        <social-link
          kind="reddit"
          mode="text"
          class="hover:underline ffun-normal-link" />
        <social-link
          kind="discord"
          mode="text"
          class="hover:underline ffun-normal-link" />
        <social-link
          kind="github"
          mode="text"
          class="hover:underline ffun-normal-link" />
      </div>
    </div>

    <div class="flex flex-col items-center sm:items-start">
      <h3 class="text-lg font-semibold mb-4">For Users</h3>

      <div class="flex flex-col space-y-2">
        <div>You can ask for help on Discord, Reddit, or GitHub</div>

        <a
          v-if="settings.crmTerms"
          :href="router.resolve({name: 'terms'}).href"
          class="ffun-normal-link"
          @click.prevent="router.push({name: 'terms'})">
          Terms of Service
        </a>

        <a
          v-if="settings.crmPrivacy"
          :href="router.resolve({name: 'privacy'}).href"
          class="ffun-normal-link"
          @click.prevent="router.push({name: 'privacy'})">
          Privacy Policy
        </a>

        <a
          href="#"
          class="ffun-normal-link"
          @click.prevent="$CookieConsent.show(true)">
          Cookie Settings
        </a>
        </div>
      </div>
    </div>
  </footer>
</template>

<script lang="ts" setup>
  import {inject, computed} from "vue";
  import {useRouter} from "vue-router";

  import * as events from "@/logic/events";
  import * as settings from "@/logic/settings";
  import * as asserts from "@/logic/asserts";

  const router = useRouter();

  const eventsView = inject<events.EventsViewName>("eventsViewName");

  asserts.defined(eventsView);

  const year = computed(() => {
    const date = new Date();
    return date.getFullYear();
  });
</script>
