<template>
  <div>
    <div class="text-base">
      <entry-tag
        v-for="tag of displayedTags"
        :key="tag"
        :uid="tag"
        :css-modifier="tagMode(tag)"
        :count="tagsCount[tag]"/>

      <a
        class=""
        title="Click on the news title to open it and see all tags"
        href="#"
        @click.prevent="emit('request-to-show-all')"
        v-if="!showAll && tagsNumber - showLimit > 0"
        >[{{ tagsNumber - showLimit }} more]</a
      >
    </div>
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";

  const showLimit = 5;

  const properties = defineProps<{
    tags: string[];
    contributions: {[key: string]: number};
    tagsCount: {[key: string]: number};
    showAll: boolean;
  }>();

  const emit = defineEmits(["request-to-show-all"]);

  const tagsNumber = computed(() => {
    return properties.tags.length;
  });

  const displayedTags = computed(() => {
    if (properties.showAll) {
      return preparedTags.value;
    }

    return preparedTags.value.slice(0, showLimit);
  });

  function tagMode(tag: string) {
    if (!properties.contributions) {
      return "neurtral";
    }

    if (!(tag in properties.contributions)) {
      return "neurtral";
    }

    if (properties.contributions[tag] == 0) {
      return "neurtral";
    }

    if (properties.contributions[tag] > 0) {
      return "positive";
    }

    return "negative";
  }

  const preparedTags = computed(() => {
    const values = [];

    for (const tag of properties.tags) {
      values.push(tag);
    }

    values.sort((a, b) => {
      const aContributions = Math.abs(properties.contributions[a] || 0);
      const bContributions = Math.abs(properties.contributions[b] || 0);

      if (aContributions > bContributions) {
        return -1;
      }

      if (aContributions < bContributions) {
        return 1;
      }

      const aCount = properties.tagsCount[a];
      const bCount = properties.tagsCount[b];

      if (aCount > bCount) {
        return -1;
      }

      if (aCount < bCount) {
        return 1;
      }

      if (a > b) {
        return 1;
      }

      if (a < b) {
        return -1;
      }

      return 0;
    });

    return values;
  });
</script>
