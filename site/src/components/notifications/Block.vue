<template>
  <notifications-api-key v-if="showAPIKeyNotification" />
  <collections-notification v-if="showCollectionsNotification" />
  <notifications-create-rule-help v-if="showCreateRuleHelpNotification" />
  <collections-warning v-if="showCollectionsWarning" />
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch, inject} from "vue";
  import type {Ref} from "vue";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useCollectionsStore} from "@/stores/collections";
  import * as tagsFilterState from "@/logic/tagsFilterState";
  import * as settings from "@/logic/settings";

  const properties = defineProps<{
    apiKey: boolean;
    createRuleHelp: boolean;
    collectionsNotification_: boolean;
    collectionsWarning_: boolean;
  }>();

  const collections = useCollectionsStore();
  const globalSettings = useGlobalSettingsStore();

  const tagsStates = inject<Ref<tagsFilterState.Storage> | null>("tagsStates", null);

  const showApiKeyMessage = computed(() => {
    return (
      globalSettings.userSettingsPresent &&
      !globalSettings.openai_api_key.value &&
      !globalSettings.gemini_api_key.value &&
      !globalSettings.hide_message_about_setting_up_key.value
    );
  });

  const showCollectionsNotification = computed(() => {
    return (
      properties.collectionsNotification_ &&
      globalSettings.userSettingsPresent &&
      !globalSettings.hide_message_about_adding_collections.value &&
      !tagsStates?.value.hasSelectedTags &&
      settings.hasCollections
    );
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

  const showCollectionsWarning = computed(() => {
    return (
      properties.collectionsWarning_ &&
      !showCollectionsNotification.value &&
      globalSettings.userSettingsPresent &&
      !globalSettings.hide_message_check_your_feed_urls.value
    );
  });
</script>
