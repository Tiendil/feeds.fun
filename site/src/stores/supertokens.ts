import {ref, watch} from "vue";
import {useRouter} from "vue-router";
import {defineStore} from "pinia";
import {Timer} from "@/logic/timer";
import SuperTokens from "supertokens-web-js";
import Session from "supertokens-web-js/recipe/session";
import Passwordless from "supertokens-web-js/recipe/passwordless";
import * as passwordless from "supertokens-web-js/recipe/passwordless";
import {computedAsync} from "@vueuse/core";

export const useSupertokens = defineStore("supertokens", () => {
  const isLoggedIn = ref<boolean|null>(null);

  async function refresh() {
    isLoggedIn.value = await Session.doesSessionExist();
  }

  const refresher = new Timer(refresh, 1000);

  const allowResendAfter = ref(60 * 1000);

  function init({
    apiDomain,
    apiBasePath,
    appName,
    resendAfter
  }: {
    apiDomain: string;
    apiBasePath: string;
    appName: string;
    resendAfter: number;
  }) {
    allowResendAfter.value = resendAfter;

    SuperTokens.init({
      // enableDebugLogs: true,
      appInfo: {
        apiDomain: apiDomain,
        apiBasePath: apiBasePath,
        appName: appName
      },
      recipeList: [Session.init(), Passwordless.init()]
    });

    refresher.start();
  }

  async function processError(err: any) {
    await refresh();

    if (err.isSuperTokensGeneralError === true) {
      window.alert(err.message);
    }
  }

  async function sendMagicLink(email: string) {
    try {
      let response = await passwordless.createCode({
        email
      });

      return response.status === "OK";
    } catch (err: any) {
      await processError(err);
      return false;
    }
  }

  async function logout() {
    await Session.signOut();

    await passwordless.clearLoginAttemptInfo();

    await refresh();
  }

  async function resendMagicLink() {
    try {
      let response = await passwordless.resendCode();

      if (response.status === "OK") {
        return true;
      } else if (response.status === "RESTART_FLOW_ERROR") {
        // this can happen if the user has already successfully logged in into
        // another device whilst also trying to login to this one.
        return false;
      } else {
        return false;
      }
    } catch (err: any) {
      await processError(err);
      return false;
    }
  }

  async function hasInitialMagicLinkBeenSent() {
    return (await passwordless.getLoginAttemptInfo()) !== undefined;
  }

  async function handleMagicLinkClicked({
    onSignUp,
    onSignIn,
    onSignFailed
  }: {
    onSignUp: () => void;
    onSignIn: () => void;
    onSignFailed: () => void;
  }) {
    try {
      let response = await passwordless.consumeCode();

      await refresh();

      if (response.status === "OK") {
        if (response.createdNewUser) {
          await onSignUp();
        } else {
          await onSignIn();
        }
      } else {
        await onSignFailed();
      }
    } catch (err: any) {
      await processError(err);
    }
  }

  async function clearLoginAttempt() {
    await passwordless.clearLoginAttemptInfo();
  }

  return {
    allowResendAfter,

    init,
    sendMagicLink,
    resendMagicLink,
    isLoggedIn,
    logout,
    hasInitialMagicLinkBeenSent,
    handleMagicLinkClicked,
    clearLoginAttempt
  };
});
