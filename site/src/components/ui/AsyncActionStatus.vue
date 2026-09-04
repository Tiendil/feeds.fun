<template>
  <ui-notice
    v-if="notice !== null"
    :tone="notice.tone">
    <div
      v-if="properties.status === 'succeeded' || properties.status === 'failed'"
      class="flex items-center gap-3">
      <p class="grow">{{ notice.text }}</p>

      <ui-button
        variant="quiet"
        size="compact"
        class="shrink-0"
        tooltip="Close notification"
        aria-label="Close notification"
        @click="dismissed = true">
        <icon
          icon="x"
          size="small" />
      </ui-button>
    </div>

    <template v-else>{{ notice.text }}</template>
  </ui-notice>
</template>

<script lang="ts" setup>
  import {computed, ref, watch} from "vue";
  import type {AsyncActionStatus} from "@/logic/asyncAction";

  type NoticeTone = "info" | "success" | "danger";

  const properties = defineProps<{
    status: AsyncActionStatus;
    runningText: string;
    succeededText: string;
    failedText: string;
  }>();

  const dismissed = ref(false);

  const notice = computed<{tone: NoticeTone; text: string} | null>(() => {
    if (properties.status === "running") {
      return {tone: "info", text: properties.runningText};
    }

    if (properties.status === "succeeded") {
      if (dismissed.value) {
        return null;
      }

      return {tone: "success", text: properties.succeededText};
    }

    if (properties.status === "failed") {
      if (dismissed.value) {
        return null;
      }

      return {tone: "danger", text: properties.failedText};
    }

    return null;
  });

  watch(
    () => properties.status,
    (status) => {
      if (status === "running") {
        dismissed.value = false;
      }
    }
  );
</script>
