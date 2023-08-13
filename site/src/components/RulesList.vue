<template>
  <table>
    <thead>
      <tr>
        <th>score</th>
        <th>tags</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="rule in rules"
          :key="rule.id">
        <td>
          <rule-score-updater
            :score="rule.score"
            :rule-id="rule.id"
            :tags="rule.tags" />
        </td>
        <td>
          <template
            v-for="tag of rule.tags"
            :key="tag">
            <ffun-tag :uid="tag" />&nbsp;
          </template>
        </td>
        <td>
          <a
            href="#"
            @click.prevent="deleteRule(rule.id)"
            >delete</a
          >
        </td>
      </tr>
    </tbody>
  </table>
</template>

<script lang="ts" setup>
  import type * as t from "@/logic/types";
  import * as api from "@/logic/api";
  import * as e from "@/logic/enums";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";

  defineProps<{rules: Array<t.Rule>}>();

  const globalSettings = useGlobalSettingsStore();

  async function deleteRule(id: t.RuleId) {
    await api.deleteRule({id: id});
    globalSettings.updateDataVersion();
  }
</script>

<style></style>
