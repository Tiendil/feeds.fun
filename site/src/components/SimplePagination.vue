<template>
  <div>
    {{ realShowEntries }} of {{ total }}

    <button
      class="ffun-form-button ml-2"
      v-if="canShowMore"
      @click.prevent="showMore()">
      next {{ realShowPerPage }}
    </button>

    <button
      class="ffun-form-button ml-2"
      v-if="canHide"
      @click.prevent="hideAll()"
      >hide</button
    >

    <div
      v-if="counterOnNewLine"
      style="line-height: 0.5rem"
      >&nbsp;</div
    >
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import * as t from "@/logic/types";
  import {computedAsync} from "@vueuse/core";

  const properties = defineProps<{
    showFromStart: number;
    showPerPage: number;
    total: number;
    counterOnNewLine: boolean;
  }>();

  const showEntries = ref(properties.showFromStart);

  const emit = defineEmits(["update:showEntries"]);

  emit("update:showEntries", showEntries.value);

  function showMore() {
    showEntries.value += properties.showPerPage;

    if (showEntries.value > properties.total) {
      showEntries.value = properties.total;
    }

    emit("update:showEntries", showEntries.value);
  }

  function hideAll() {
    showEntries.value = properties.showFromStart;
    emit("update:showEntries", showEntries.value);
  }

  const realShowPerPage = computed(() => {
    return Math.min(properties.showPerPage, properties.total - showEntries.value);
  });

  const realShowEntries = computed(() => {
    const size = Math.min(showEntries.value, properties.total);

    emit("update:showEntries", size);

    return size;
  });

  const canHide = computed(() => {
    return showEntries.value > properties.showFromStart;
  });

  const canShowMore = computed(() => {
    return showEntries.value < properties.total;
  });
</script>
