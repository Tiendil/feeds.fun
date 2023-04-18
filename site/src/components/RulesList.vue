<template>

  <table>
    <thead>
      <tr>
        <th>score</th>
        <th>tags</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="rule in rules">
        <td>{{rule.score}}</td>
        <td>
          <template v-for="tag of rule.tags"
                    :key="tag">
            <value-tag :value="tag"/>&nbsp;
          </template>
        </td>
      </tr>
    </tbody>
  </table>

</template>

<script lang="ts" setup>
import * as t from "@/logic/types";

defineProps<{ rules: Array[t.Rule]}>();

</script>

<style></style>
