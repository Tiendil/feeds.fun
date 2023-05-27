import { ref, watch } from "vue";
import { useRouter } from 'vue-router'
import { defineStore } from "pinia";

import SuperTokens from 'supertokens-web-js';
import Session from 'supertokens-web-js/recipe/session';
import Passwordless from 'supertokens-web-js/recipe/passwordless'
import * as passwordless from "supertokens-web-js/recipe/passwordless";


export const useSupertokens = defineStore("supertokens", () => {

    function init({apiDomain, apiBasePath, appName}:
                  {apiDomain: string, apiBasePath: string, appName: string}) {
        SuperTokens.init({
            appInfo: {
                apiDomain: apiDomain,
                apiBasePath: apiBasePath,
                appName: appName,
            },
            recipeList: [
                Session.init(),
                Passwordless.init(),
            ],
        });
    }

    function processError(err: any) {
        console.log(err);
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
            processError(err);
            return false;
        }
    }

    async function isLoggedIn() {
        if (await Session.doesSessionExist()) {
            return true;
        }
        return false;
    }

    async function logout() {
        await Session.signOut();
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
            processError(err);
            return false;
        }
    }

    async function hasInitialMagicLinkBeenSent() {
        return await passwordless.getLoginAttemptInfo() !== undefined;
    }

    async function handleMagicLinkClicked({onSignUp, onSignIn, onSignFailed}:
                                          {onSignUp: () => void, onSignIn: () => void, onSignFailed: () => void}) {
        try {
            let response = await passwordless.consumeCode();

            console.log(response);

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
            processError(err);
        }
    }

    async function clearLoginAttempt() {
        await passwordless.clearLoginAttemptInfo();
    }

    return {
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
