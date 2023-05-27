<template>
<div>

  <template v-if="!requested">
    <input type="email"
           v-model="email"
           placeholder="your-account-email@example.com"/>

    <button @click.prevent="login()">Login</button>
  </template>

  <template v-else>
    <p>
      Email with login link has been sent to <strong>{{email}}</strong>
    </p>

    <button type="button" class="btn btn-primary" :disabled="counting" @click="startCountdown">
      <vue-countdown v-if="counting"
                     :time="resendAfter"
                     @end="onCountdownEnd"
                     v-slot="{ totalSeconds }">
        Resend the email in {{ totalSeconds }} seconds.
      </vue-countdown>
      <span v-else @click.prevent="resend()">Resend email</span>
    </button>

    <br/><br/>

    <button @click.prevent="requested = false">Change email</button>
  </template>

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

const requested = ref(supertokens.hasInitialMagicLinkBeenSent());

const counting = ref(false);

const email = ref("");

async function login() {

    await supertokens.sendMagicLink(email.value);

    requested.value = true;
    counting.value = true;
}

async function resend() {
    await supertokens.resendMagicLink();
    counting.value = true;
}

const resendAfter = 6 * 1000;

function onCountdownEnd() {
      counting.value = false;
}

</script>

<style scoped>
</style>
