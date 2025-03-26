<template>
  <template v-if="rules.length > 0">
<ul>
    <li
      v-for="rule in rules"
      :key="rule.id"
      class="ffun-body-list-entry">
      <rule-for-list :rule="rule" />
    </li>
</ul>
</template>
<template v-else>
  <p class="ffun-info-common">No rules to show.</p>
</template>
</template>

<script lang="ts" setup>
  import type * as t from "@/logic/types";
  import * as api from "@/logic/api";
  import * as e from "@/logic/enums";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";

  defineProps<{rules: Array<t.Rule>}>();
</script>
