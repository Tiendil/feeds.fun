
export enum AuthMode {
    SingleUser = 'single_user',
    Supertokens = 'supertokens'
}


export const appName = import.meta.env.VITE_FFUN_APP_NAME || "Feeds Fun";
export const appDomain = import.meta.env.VITE_FFUN_APP_DOMAIN || "localhost";
export const appPort = import.meta.env.VITE_FFUN_APP_PORT || "5173";
export const appProtocol = import.meta.env.VITE_FFUN_APP_PROTOCOL || "https";

export const authMode = import.meta.env.VITE_FFUN_AUTH_MODE || AuthMode.SingleUser;
export const authSupertokensApiBasePath = import.meta.env.VITE_FFUN_AUTH_SUPERTOKENS_API_BASE_PATH || "/supertokens";
export const authSupertokensResendAfter = import.meta.env.VITE_FFUN_AUTH_SUPERTOKENS_RESEND_AFTER || 60 * 1000;

console.log('settings.appName', appName);
console.log('settings.appDomain', appDomain);
console.log('settings.appPort', appPort);
console.log('settings.appProtocol', appProtocol);

console.log('settings.authMode', authMode);
console.log('settings.authSupertokensApiBasePath', authSupertokensApiBasePath);
console.log('settings.authSupertokensResendAfter', authSupertokensResendAfter);
