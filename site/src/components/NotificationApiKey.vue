<template>
  <div class="ffun-info-attention">
    <p> Feeds Fun provides tags for feeds from collections for free. </p>
    <p> Please, set up your own OpenAI and/or Gemini API keys to tag your personal feeds. </p>
    <p>
      You can do this on the
      <a
        href="#"
        @click.prevent="router.push({name: e.MainPanelMode.Settings, params: {}})"
        >settings</a
      >
      page.
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
</script>
