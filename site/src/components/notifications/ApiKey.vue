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
    your own OpenAI and/or Gemini API keys to tag your personal feeds.
  </p>

  <p>
    Remember, Feeds Fun provides tags for feeds from
    <a
      href="#"
      @click.prevent="goToCollections()"
      >collections</a
                    >
    for free. You do not need to set up your own API keys to have tags in news from collections.
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
