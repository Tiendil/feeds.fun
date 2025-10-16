<template>
  <div v-if="globalState.isLoggedIn">
    <h3 class="">You have already logged in</h3>
    <button
      class="text-blue-600 hover:text-blue-800 text-xl pt-0"
      @click.prevent="goToWorkspace()"
      >Go To Feeds ⇒</button
    >
  </div>

  <div v-else>
    <h2 class="my-0">Single e-mail to log in</h2>
    <template v-if="!requested">
      <p class="text-center">We'll send you an email with a login link, no password required.</p>

      <form
        @submit.prevent="login()"
        class="w-full flex justify-center">
        <input
          class="ffun-input flex-grow p-1 mr-2"
          type="email"
          v-model="email"
          required
          placeholder="me@example.com" />
        <button
          class="ffun-form-button"
          type="submit"
          >Log In</button
        >
      </form>
    </template>

    <template v-else>
      <p class="">
        Login link was sent to <strong>{{ email }}</strong>

        <a
          class="ml-1"
          @click.prevent="onChangeEmail()"
          >change</a
        >
      </p>

      <button
        v-if="!counting"
        type="button"
        class="btn btn-primary ffun-form-button">
        <span @click.prevent="resend()">Resend email</span>
      </button>

      <vue-countdown
        v-else
        :time="supertokens.allowResendAfter"
        @end="onCountdownEnd"
        class=""
        v-slot="{totalSeconds}">
        Resend in {{ totalSeconds }} seconds
      </vue-countdown>
    </template>
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref, onMounted} from "vue";
  import * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as api from "@/logic/api";
  import {computedAsync} from "@vueuse/core";
  import DOMPurify from "dompurify";
  import {useEntriesStore} from "@/stores/entries";
  import {useSupertokens} from "@/stores/supertokens";
  import {useGlobalState} from "@/stores/globalState";
  import {useRouter} from "vue-router";
  import * as settings from "@/logic/settings";
  const router = useRouter();

  const globalState = useGlobalState();

  const supertokens = useSupertokens();

  const requested = ref(false);

  const counting = ref(false);

  const email = ref("");

  async function afterEmailSend(success: boolean) {
    if (success) {
      return;
    }

    window.alert("Something went wrong. Please try again.");
    requested.value = false;
    counting.value = false;
    await supertokens.clearLoginAttempt();
  }

  function beforeEmailSend() {
    requested.value = true;
    counting.value = true;
  }

  async function login() {
    beforeEmailSend();

    const success = await supertokens.sendMagicLink(email.value);

    await afterEmailSend(success);
  }

  async function resend() {
    beforeEmailSend();

    const success = await supertokens.resendMagicLink();

    await afterEmailSend(success);
  }

  function onCountdownEnd() {
    counting.value = false;
  }

  async function onChangeEmail() {
    requested.value = false;
    await supertokens.clearLoginAttempt();
  }

  function goToWorkspace() {
    router.push({name: e.MainPanelMode.Entries, params: {}});
  }

  onMounted(async () => {
    if (settings.authMode === settings.AuthMode.SingleUser) {
      return true;
    }

    requested.value = await supertokens.hasInitialMagicLinkBeenSent();
  });
</script>

<style scoped></style>
