
export enum AuthMode {
    SingleUser = 'single_user',
    Supertokens = 'supertokens'
}


export const authMode = import.meta.env.VITE_FFUN_AUTH_MODE;


console.log('settings.authMode', authMode);
