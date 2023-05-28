import * as utils from "@/logic/utils";


export enum AuthMode {
    SingleUser = 'single_user',
    Supertokens = 'supertokens'
}


export const authMode = utils.getKeyByValue(AuthMode, import.meta.env.VITE_AUTH_MODE, AuthMode.SingleUser);


// 59da1b8f-c0c4-416f-908d-85daecfb1726
