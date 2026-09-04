<template>
  <ui-async-action-status
    :status="status"
    running-text="Subscribing…"
    succeeded-text="Feeds added!"
    failed-text="Unknown error occurred! Please, try later." />
</template>

<script lang="ts" setup>
  import type {AsyncActionStatus} from "@/logic/asyncAction";

  defineProps<{status: AsyncActionStatus}>();
</script>
