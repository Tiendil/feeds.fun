<template>
  <div class="ffun-info-common">
    <h4>Setup API keys</h4>

    <p>
      Please
      <a
        href="#"
        @click.prevent="goToSettings()"
        >set up</a
      >
      your own
      <external-url
        url="https://platform.openai.com/docs/api-reference/introduction"
        text="OpenAI" />
      or
      <external-url
        url="https://ai.google.dev/gemini-api/docs/api-key"
        text="Gemini" />
      API keys to tag your personal feeds.
    </p>

    <p>
      <a
        href="#"
        @click.prevent="goToCollections()"
        >Collection</a
      >
      feeds are tagged automatically, so no actions are required for them.
    </p>

    <user-setting-for-notification
      kind="hide_message_about_setting_up_key"
      button-text="Hide this message" />
  </div>
</template>

<script lang="ts" setup>
  import {useRouter} from "vue-router";
  import * as e from "@/logic/enums";

  const router = useRouter();

  function goToCollections() {
    router.push({name: e.MainPanelMode.Collections, params: {}});
  }

  function goToSettings() {
    router.push({name: e.MainPanelMode.Settings, params: {}});
  }
</script>
