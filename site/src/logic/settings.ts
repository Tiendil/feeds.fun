declare const __APP_VERSION__: string;

export enum AuthMode {
  SingleUser = "single_user",
  Supertokens = "supertokens",
  OIDC = "oidc"
}

export const appName = import.meta.env.VITE_FFUN_APP_NAME || "Feeds Fun";
export const appDomain = import.meta.env.VITE_FFUN_APP_DOMAIN || "localhost";
export const appPort = import.meta.env.VITE_FFUN_APP_PORT || "5173";

export const environment = import.meta.env.VITE_FFUN_ENVIRONMENT || "local";
export const version = __APP_VERSION__;

export const authMode = import.meta.env.VITE_FFUN_AUTH_MODE || AuthMode.SingleUser;
export const authSupertokensApiBasePath = import.meta.env.VITE_FFUN_AUTH_SUPERTOKENS_API_BASE_PATH || "/supertokens";
export const authSupertokensResendAfter = import.meta.env.VITE_FFUN_AUTH_SUPERTOKENS_RESEND_AFTER || 60 * 1000;

export const blog = import.meta.env.VITE_FFUN_BLOG || "https://blog.feeds.fun";
export const githubRepo = import.meta.env.VITE_FFUN_GITHUB_REPO || "https://github.com/Tiendil/feeds.fun";
export const discordInvite = import.meta.env.VITE_FFUN_DISCORD_INVITE || "https://discord.gg/C5RVusHQXy";
export const redditSubreddit = import.meta.env.VITE_FFUN_REDDIT_SUBREDDIT || "https://www.reddit.com/r/feedsfun/";

export const plausibleEnabled = import.meta.env.VITE_FFUN_PLAUSIBLE_ENABLED == "true" || false;
export const plausibleDomain = import.meta.env.VITE_FFUN_PLAUSIBLE_DOMAIN || "localhost";
export const plausibleScript = import.meta.env.VITE_FFUN_PLAUSIBLE_SCRIPT || "";

export const trackEvents = import.meta.env.VITE_FFUN_TRACK_EVENTS == "true" || false;

export const utmLifetime = import.meta.env.VITE_FFUN_UTM_LIFETIME || 7; // days

export const crmTerms = import.meta.env.VITE_FFUN_CRM_TERMS || null;
export const crmPrivacy = import.meta.env.VITE_FFUN_CRM_PRIVACY || null;

export const hasCollections = import.meta.env.VITE_FFUN_HAS_COLLECTIONS == "true" || false;

console.log("settings.appName", appName);
console.log("settings.appDomain", appDomain);
console.log("settings.appPort", appPort);

console.log("settings.environment", environment);
console.log("settings.version", version);

console.log("settings.authMode", authMode);
console.log("settings.authSupertokensApiBasePath", authSupertokensApiBasePath);
console.log("settings.authSupertokensResendAfter", authSupertokensResendAfter);

console.log("settings.blog", blog);
console.log("settings.githubRepo", githubRepo);
console.log("settings.discordInvite", discordInvite);
console.log("settings.redditSubreddit", redditSubreddit);

console.log("settings.plausibleEnabled", plausibleEnabled);
console.log("settings.plausibleDomain", plausibleDomain);
console.log("settings.plausibleScript", plausibleScript);

console.log("settings.trackEvents", trackEvents);

console.log("settings.utmLifetime", utmLifetime);

console.log("settings.crmTerms", crmTerms ? "set" : "not set");
console.log("settings.crmPrivacy", crmPrivacy ? "set" : "not set");

console.log("settings.hasCollections", hasCollections);

export const isSingleUserMode = authMode === AuthMode.SingleUser;
