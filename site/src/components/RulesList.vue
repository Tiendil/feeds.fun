<template>
  <ul>
    <li
      v-for="rule in rules"
      :key="rule.id">
      <rule-for-list :rule="rule" />
    </li>
  </ul>
</template>

<script lang="ts" setup>
  import type * as t from "@/logic/types";
  import * as api from "@/logic/api";
  import * as e from "@/logic/enums";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";

  defineProps<{rules: Array<t.Rule>}>();

</script>
