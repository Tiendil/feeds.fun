<template>
  <notifications-api-key v-if="showAPIKeyNotification" />
  <collections-notification v-if="showCollectionsNotification" />
  <notifications-create-rule-help v-if="showCreateRuleHelpNotification" />
  <collections-warning v-if="showCollectionsWarning" />
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch, inject} from "vue";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useCollectionsStore} from "@/stores/collections";
  import * as tagsFilterState from "@/logic/tagsFilterState";

  const properties = defineProps<{
    apiKey: boolean;
    createRuleHelp: boolean;
    collectionsNotification_: boolean;
    collectionsWarning_: boolean;
  }>();

  const collections = useCollectionsStore();
  const globalSettings = useGlobalSettingsStore();

  const tagsStates = inject<Ref<tagsFilterState.Storage>>("tagsStates", null);

  // TODO: unify with the code from RuleConstructor.vue
  const hasSelectedTags = computed(() => {
    if (!tagsStates) {
      return false;
    }

    let values = Object.keys(tagsStates.value.selectedTags);

    values = values.filter((tag) => {
      return tagsStates.value.selectedTags[tag] === true;
    });

    return values.length > 0;
  });

  const showApiKeyMessage = computed(() => {
    return (
      globalSettings.userSettings &&
      !globalSettings.userSettings.openai_api_key.value &&
      !globalSettings.userSettings.gemini_api_key.value &&
      !globalSettings.userSettings.hide_message_about_setting_up_key.value
    );
  });

  const showCollectionsNotification = computed(() => {
    return (
      properties.collectionsNotification_ &&
      globalSettings.userSettings &&
      !globalSettings.userSettings.hide_message_about_adding_collections.value &&
      !hasSelectedTags.value
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
      globalSettings.userSettings &&
      !globalSettings.userSettings.hide_message_check_your_feed_urls.value
    );
  });
</script>
