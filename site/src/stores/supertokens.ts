import { ref, watch } from "vue";
import { useRouter } from 'vue-router'
import { defineStore } from "pinia";

import SuperTokens from 'supertokens-web-js';
import Session from 'supertokens-web-js/recipe/session';
import Passwordless from 'supertokens-web-js/recipe/passwordless'
import { createCode } from "supertokens-web-js/recipe/passwordless";


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


    async function sendMagicLink(email: string) {
        try {
            let response = await createCode({
                email
            });

            window.alert("Please check your email for the magic link");
        } catch (err: any) {
            console.log(err);
            if (err.isSuperTokensGeneralError === true) {
                // this may be a custom error message sent from the API by you,
                // or if the input email / phone number is not valid.
                window.alert(err.message);
            }
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
        window.location.href = "/";
    }

    return {
        init,
        sendMagicLink,
        isLoggedIn,
        logout,
    };
});
