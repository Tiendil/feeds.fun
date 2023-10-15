<template>
  <notification-openai-api-key v-if="showOpenAIKeyNotification" />
  <notification-collections v-if="showCollectionsNotification" />
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch} from "vue";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";

  const properties = defineProps<{
    openaiApiKey: boolean;
    collections: boolean;
  }>();

  const globalSettings = useGlobalSettingsStore();

  const showApiKeyMessage = computed(() => {
    return (
      globalSettings.userSettings &&
      !globalSettings.userSettings.openai_api_key.value &&
      !globalSettings.userSettings.openai_hide_message_about_setting_up_key.value
    );
  });

  const showCollectionsNotification = computed(() => {
    return properties.collections;
  });

  const showOpenAIKeyNotification = computed(() => {
    return !showCollectionsNotification.value && properties.openaiApiKey && showApiKeyMessage.value;
  });
</script>
