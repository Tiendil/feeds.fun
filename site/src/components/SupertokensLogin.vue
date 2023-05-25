<template>
<div>
  <input type="email"
         v-model="email"
         placeholder="your-account-email@example.com"/>

  <button @click.prevent="login()">Login</button>

  <p v-if="requested">
    Email with login link has been sent to your email address.
  </p>

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
import { useSupertokens } from "@/stores/supertokens";

const supertokens = useSupertokens();

const requested = ref(false);

const email = ref("");

async function login() {

    await supertokens.sendMagicLink(email.value);

    requested.value = true;

}

</script>

<style scoped>
</style>
