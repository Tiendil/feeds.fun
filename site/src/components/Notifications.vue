<template>
  <notification-api-key v-if="showAPIKeyNotification" />
  <collections-notification v-if="showCollectionsNotification" />
  <notification-create-rule-help v-if="showCreateRuleHelpNotification" />
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch} from "vue";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useCollectionsStore} from "@/stores/collections";

  const properties = defineProps<{
    apiKey: boolean;
    collections: boolean;
    createRuleHelp: boolean;
  }>();

  const collections = useCollectionsStore();
  const globalSettings = useGlobalSettingsStore();

  const showApiKeyMessage = computed(() => {
    return (
      globalSettings.userSettings &&
      !globalSettings.userSettings.openai_api_key.value &&
      !globalSettings.userSettings.gemini_api_key.value &&
      !globalSettings.userSettings.hide_message_about_setting_up_key.value
    );
  });

  const showCollectionsNotification = computed(() => {
    return (properties.collections &&
            !globalSettings.userSettings.hide_message_about_adding_collections.value);
  });

  const showCreateRuleHelpNotification = computed(() => {
    return !showCollectionsNotification.value && properties.createRuleHelp;
  });

  const showAPIKeyNotification = computed(() => {
    return (
      !showCollectionsNotification.value &&
      !showCreateRuleHelpNotification.value &&
      properties.apiKey &&
      showApiKeyMessage.value
    );
  });
</script>
