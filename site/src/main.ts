import {createApp} from "vue";
import {createPinia} from "pinia";

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
import TagsFilter from "./components/TagsFilter.vue";
import DiscoveryForm from "./components/DiscoveryForm.vue";
import FeedInfo from "./components/FeedInfo.vue";
import OpmlUpload from "./components/OPMLUpload.vue";
import FeedForList from "./components/FeedForList.vue";
import SupertokensLogin from "./components/SupertokensLogin.vue";
import FfunTag from "./components/FfunTag.vue";
import SimplePagination from "./components/SimplePagination.vue";
import UserSetting from "./components/UserSetting.vue";
import TokensCost from "./components/TokensCost.vue";
import FaviconElement from "./components/FaviconElement.vue";
import RuleForList from "./components/RuleForList.vue";
import UserSettingForNotification from "./components/UserSettingForNotification.vue";

import NotificationsApiKey from "./components/notifications/ApiKey.vue";
import NotificationsCreateRuleHelp from "./components/notifications/CreateRuleHelp.vue";
import Notifications from "./components/notifications/Block.vue";

import CollectionsNotification from "./components/collections/Notification.vue";
import CollectionsWarning from "./components/collections/Warning.vue";
import CollectionsBlock from "./components/collections/Block.vue";
import CollectionsBlockItem from "./components/collections/BlockItem.vue";
import CollectionsDetailedItem from "./components/collections/DetailedItem.vue";
import CollectionsSubscribingProgress from "./components/collections/SubscribingProgress.vue";
import CollectionsFeedItem from "./components/collections/FeedItem.vue";

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

const app = createApp(App);

app.component("FeedsList", FeedsList);
app.component("EntriesList", EntriesList);
app.component("RulesList", RulesList);
app.component("TagsList", TagsList);
app.component("ConfigSelector", ConfigSelector);
app.component("ConfigFlag", ConfigFlag);
app.component("EntryForList", EntryForList);
app.component("RuleConstructor", RuleConstructor);
app.component("TagsFilter", TagsFilter);
app.component("DiscoveryForm", DiscoveryForm);
app.component("FeedInfo", FeedInfo);
app.component("OpmlUpload", OpmlUpload);
app.component("FeedForList", FeedForList);
app.component("SupertokensLogin", SupertokensLogin);
app.component("FfunTag", FfunTag);
app.component("SimplePagination", SimplePagination);
app.component("UserSetting", UserSetting);
app.component("TokensCost", TokensCost);
app.component("FaviconElement", FaviconElement);
app.component("RuleForList", RuleForList);
app.component("UserSettingForNotification", UserSettingForNotification);

app.component("NotificationsApiKey", NotificationsApiKey);
app.component("NotificationsCreateRuleHelp", NotificationsCreateRuleHelp);
app.component("Notifications", Notifications);

app.component("CollectionsNotification", CollectionsNotification);
app.component("CollectionsWarning", CollectionsWarning);
app.component("CollectionsBlock", CollectionsBlock);
app.component("CollectionsBlockItem", CollectionsBlockItem);
app.component("CollectionsDetailedItem", CollectionsDetailedItem);
app.component("CollectionsSubscribingProgress", CollectionsSubscribingProgress);
app.component("CollectionsFeedItem", CollectionsFeedItem);

app.component("ScoreSelector", ScoreSelector);
app.component("InputMarker", InputMarker);

app.component("ValueUrl", ValueUrl);
app.component("ValueFeedId", ValueFeedId);
app.component("ValueDateTime", ValueDateTime);
app.component("ValueScore", ValueScore);

app.component("WideLayout", WideLayout);
app.component("SidePanelLayout", SidePanelLayout);

app.component("vue-countdown", VueCountdown);

app.use(createPinia());
app.use(router);

app.mount("#app");

import * as api from "@/logic/api";
import * as settings from "@/logic/settings";

/////////////////////
// supertokens
/////////////////////

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

/////////////////////
// plausible
/////////////////////

if (settings.plausibleEnabled) {
  const script = document.createElement("script");
  script.src = settings.plausibleScript;
  script.async = true;
  script.defer = true;
  script.setAttribute("data-domain", settings.plausibleDomain);
  document.body.appendChild(script);
}
