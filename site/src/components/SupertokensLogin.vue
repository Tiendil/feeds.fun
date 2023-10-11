<template>

  <div v-if="!globalState.isLoggedIn">
    <p class="">You have already logged in.</p>
    <button class="text-blue-600 hover:text-blue-800 text-xl pt-0"
            @click.prevent="goToWorkspace()">Go To Feeds ⇒</button>
  </div>

  <div v-else>
    <template v-if="!requested">
      <p class="text-left">We'll send you an email with a login link.</p>

      <p class="text-left">If you don&apos;t have an account, one will be created.</p>

      <form @submit.prevent="login()" class="w-full flex">
        <input
          class="flex-grow border-2 p-1 rounded border-blue-200 focus:border-blue-300 focus:outline-none placeholder-gray-500 mr-2"
          type="email"
          v-model="email"
          required
          placeholder="me@example.com" />
        <button class="ffun-form-button"
                type="submit">Login</button>
      </form>
    </template>

    <template v-else>
      <p class="">
        Login link was sent to <strong>{{ email }}</strong>

        <a class="text-blue-600 hover:text-blue-800 cursor-pointer ml-1"
           @click.prevent="onChangeEmail()">change</a>
      </p>

      <button
        v-if="!counting"
        type="button"
        class="btn btn-primary ffun-form-button disabled:bg-blue-700/75">
        <span
          @click.prevent="resend()"
          >Resend email</span>
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
    window.alert("Please check your email for the magic link");
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
