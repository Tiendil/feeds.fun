import {createApp} from "vue";
import {createPinia} from "pinia";
import * as Sentry from "@sentry/vue";

import App from "./App.vue";
import router from "./router";

import "./style.css";

import FeedsList from "./components/FeedsList.vue";
import EntriesList from "./components/EntriesList.vue";
import RulesList from "./components/RulesList.vue";
import TagsList from "./components/TagsList.vue";
import ConfigSelector from "./components/ConfigSelector.vue";
import ConfigFlag from "./components/ConfigFlag.vue";
import EntryForList from "./components/EntryForList.vue";
import RuleConstructor from "./components/RuleConstructor.vue";
import RuleScoreUpdater from "./components/RuleScoreUpdater.vue";
import TagsFilter from "./components/TagsFilter.vue";
import DiscoveryForm from "./components/DiscoveryForm.vue";
import FeedInfo from "./components/FeedInfo.vue";
import EntryInfo from "./components/EntryInfo.vue";
import OpmlUpload from "./components/OPMLUpload.vue";
import FeedForList from "./components/FeedForList.vue";
import SupertokensLogin from "./components/SupertokensLogin.vue";
import FeedsCollections from "./components/FeedsCollections.vue";
import FfunGithubButtons from "./components/FfunGithubButtons.vue";
import FfunTag from "./components/FfunTag.vue";
import SimplePagination from "./components/SimplePagination.vue";
import UserSetting from "./components/UserSetting.vue";
import OpenaiTokensUsage from "./components/OpenaiTokensUsage.vue";
import FaviconElement from "./components/FaviconElement.vue";
import CollectionsProposal from "./components/CollectionsProposal.vue";

import ScoreSelector from "./inputs/ScoreSelector.vue";
import InputMarker from "./inputs/Marker.vue";

import ValueUrl from "./values/URL.vue";
import ValueFeedId from "./values/FeedId.vue";
import ValueDateTime from "./values/DateTime.vue";
import ValueScore from "./values/Score.vue";

import WideLayout from "./layouts/WideLayout.vue";
import SidePanelLayout from "./layouts/SidePanelLayout.vue";

import {useSupertokens} from "@/stores/supertokens";

import VueCountdown from "@chenfengyuan/vue-countdown";
import GithubButton from "vue-github-button";

const app = createApp(App);

app.component("FeedsList", FeedsList);
app.component("EntriesList", EntriesList);
app.component("RulesList", RulesList);
app.component("TagsList", TagsList);
app.component("ConfigSelector", ConfigSelector);
app.component("ConfigFlag", ConfigFlag);
app.component("EntryForList", EntryForList);
app.component("RuleConstructor", RuleConstructor);
app.component("RuleScoreUpdater", RuleScoreUpdater);
app.component("TagsFilter", TagsFilter);
app.component("DiscoveryForm", DiscoveryForm);
app.component("FeedInfo", FeedInfo);
app.component("EntryInfo", EntryInfo);
app.component("OpmlUpload", OpmlUpload);
app.component("FeedForList", FeedForList);
app.component("SupertokensLogin", SupertokensLogin);
app.component("FeedsCollections", FeedsCollections);
app.component("FfunGithubButtons", FfunGithubButtons);
app.component("FfunTag", FfunTag);
app.component("SimplePagination", SimplePagination);
app.component("UserSetting", UserSetting);
app.component("OpenaiTokensUsage", OpenaiTokensUsage);
app.component("FaviconElement", FaviconElement);
app.component("CollectionsProposal", CollectionsProposal);

app.component("ScoreSelector", ScoreSelector);
app.component("InputMarker", InputMarker);

app.component("ValueUrl", ValueUrl);
app.component("ValueFeedId", ValueFeedId);
app.component("ValueDateTime", ValueDateTime);
app.component("ValueScore", ValueScore);

app.component("WideLayout", WideLayout);
app.component("SidePanelLayout", SidePanelLayout);

app.component("vue-countdown", VueCountdown);
app.component("github-button", GithubButton);

app.use(createPinia());
app.use(router);

if (settings.sentryEnable) {
  Sentry.init({
    app,
    dsn: settings.sentryDsn,
    environment: settings.environment,
    sampleRate: settings.sentrySampleRate,
    attachStacktrace: true,
    enableTracing: false,
    integrations: []
  });
}

app.mount("#app");

import * as api from "@/logic/api";
import * as settings from "@/logic/settings";

// must be copy of smart_url from backend
function smartUrl(domain: string, port: number) {
  if (port == 80) {
    return `http://${domain}`;
  }

  if (port == 443) {
    return `https://${domain}`;
  }

  return `http://${domain}:${port}`;
}

let supertokens: ReturnType<typeof useSupertokens> | null = null;

if (settings.authMode === settings.AuthMode.Supertokens) {
  supertokens = useSupertokens();

  supertokens.init({
    apiDomain: smartUrl(settings.appDomain, settings.appPort),
    apiBasePath: settings.authSupertokensApiBasePath,
    appName: settings.appName,
    resendAfter: settings.authSupertokensResendAfter
  });
} else if (settings.authMode === settings.AuthMode.SingleUser) {
} else {
  throw `Unknown auth mode: ${settings.authMode}`;
}

async function onSessionLost() {
  if (supertokens !== null) {
    await supertokens.logout();
  }

  router.push({name: "main", params: {}});
}

api.init({onSessionLost: onSessionLost});
