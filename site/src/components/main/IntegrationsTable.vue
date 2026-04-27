<template>
  <div class="mx-2">
    <div class="overflow-hidden rounded-xl border bg-slate-100">
      <div class="overflow-x-auto">
        <table class="min-w-full table-fixed border-collapse text-left">
          <colgroup>
            <col style="width: 25%" />
            <col style="width: 25%" />
            <col style="width: 25%" />
            <col style="width: 25%" />
          </colgroup>

          <thead>
            <tr class="bg-blue-100 text-slate-900">
              <th class="head-cell">Source</th>
              <th class="head-cell text-center">
                <span class="head-label">
                  Feed discovery
                  <icon
                    class="head-info-icon"
                    icon="info-square-filled"
                    size="large"
                    title="We discover feeds that are not explicitly specified by their sites and therefore are not visible to other feed readers." />
                </span>
              </th>
              <th class="head-cell text-center">
                <span class="head-label">
                  Post cleanup
                  <icon
                    class="head-info-icon"
                    icon="info-square-filled"
                    size="large"
                    title="We postprocess the content of posts to remove unnecessary markup and make them look better and easier to read." />
                </span>
              </th>
              <th class="head-cell text-center">
                <span class="head-label">
                  Extra tags
                  <icon
                    class="head-info-icon"
                    icon="info-square-filled"
                    size="large"
                    title="We add extra tags to news according to their unique properties in the source." />
                </span>
              </th>
            </tr>
          </thead>

          <tbody>
            <tr
              v-for="row in visibleRows"
              :key="row.name"
              class="border-t border-slate-300 odd:bg-slate-50 even:bg-slate-100">
              <td class="cell cell-source">
                {{ row.name }}
              </td>

              <td class="cell cell-icon">
                <div class="icon-badge">
                  <icon
                    :icon="row.discoverySupported ? 'check' : 'x'"
                    :class="row.discoverySupported ? 'text-blue-700' : 'text-slate-400'" />
                </div>
              </td>

              <td class="cell cell-icon">
                <div class="icon-badge">
                  <icon
                    :icon="row.cleanupSupported ? 'check' : 'x'"
                    :class="row.cleanupSupported ? 'text-blue-700' : 'text-slate-400'" />
                </div>
              </td>

              <td class="cell cell-extra">
                coming soon
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div
      v-if="showToggleButton"
      class="mt-4 text-center">
      <main-show-more-button v-model:expanded="showAllRows" />
    </div>
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";

  type IntegrationRow = {
    name: string;
    discoverySupported: boolean;
    cleanupSupported: boolean;
  };

  const rows: IntegrationRow[] = [
    {name: "ArXiv", discoverySupported: false, cleanupSupported: true},
    {name: "Reddit", discoverySupported: true, cleanupSupported: true},
    {name: "GitHub", discoverySupported: true, cleanupSupported: true},
    {name: "YouTube", discoverySupported: true, cleanupSupported: true},
    {name: "Hacker News", discoverySupported: false, cleanupSupported: true}
  ];

  const alwaysVisibleRowsCount = 3;

  const showAllRows = ref(false);

  const visibleRows = computed(() => {
    if (showAllRows.value) {
      return rows;
    }

    return rows.slice(0, alwaysVisibleRowsCount);
  });

  const showToggleButton = computed(() => {
    return rows.length > alwaysVisibleRowsCount;
  });
</script>

<style scoped>
  .head-cell {
    @apply px-4 py-3 text-base font-medium md:text-lg;
  }

  .head-label {
    @apply inline-flex items-center gap-1;
  }

  .head-info-icon {
    @apply text-slate-500 transition-colors cursor-pointer hover:text-black;
  }

  .cell {
    @apply px-4 py-3;
  }

  .cell-source {
    @apply text-base font-medium text-slate-900 md:text-lg;
  }

  .cell-icon {
    @apply text-center;
  }

  .cell-extra {
    @apply text-center text-sm font-medium uppercase tracking-wide text-slate-600 md:text-base;
  }

  .icon-badge {
    @apply inline-flex h-9 w-9 items-center justify-center rounded-full border border-slate-300 bg-white;
  }
</style>
