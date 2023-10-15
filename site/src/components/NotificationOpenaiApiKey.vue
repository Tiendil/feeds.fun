<template>
  <div class="ffun-info-attention">
    <p>
      Because, for now, our service is free to use and OpenAI API costs money, we politely ask you to set up your own
      OpenAI API key.
    </p>
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
      kind="openai_hide_message_about_setting_up_key"
      button-text="Hide this message" />
  </div>
</template>

<script lang="ts" setup>
  import {useRouter} from "vue-router";
  import * as e from "@/logic/enums";

  const router = useRouter();
</script>
