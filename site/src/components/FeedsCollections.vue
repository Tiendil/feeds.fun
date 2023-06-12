<template>
<div>
  <p>It looks like you have no news to read.</p>

  <p>Try to subscribe for one or all predefined feeds collections that we are prepairing for you!</p>

  <template v-for="item in collections">
    <input type="checkbox" :id="item" :name="item" :value="item" checked>
    <label :for="item">{{item}}</label>
    <br>
  </template>

  <br/>

  <button @click="subscribe">Subscribe</button>

</div>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue";
import * as t from "@/logic/types";
import * as e from "@/logic/enums";
import * as api from "@/logic/api";
import { computedAsync } from "@vueuse/core";
import DOMPurify from "dompurify";
import { useEntriesStore } from "@/stores/entries";


const collections = computedAsync(async () => {
    return await api.getFeedsCollections();
});


</script>

<style scoped>
</style>
