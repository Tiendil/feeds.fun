import {createApp} from "vue";
import {createPinia} from "pinia";

import App from "./App.vue";
import router from "./router";

import "./style.css";

import * as CookieConsent from './plugins/CookieConsent'

import FeedsList from "./components/FeedsList.vue";
import EntriesList from "./components/EntriesList.vue";
import RulesList from "./components/RulesList.vue";
import ConfigSelector from "./components/ConfigSelector.vue";
import ConfigFlag from "./components/ConfigFlag.vue";
import EntryForList from "./components/EntryForList.vue";
import RuleConstructor from "./components/RuleConstructor.vue";
import DiscoveryForm from "./components/DiscoveryForm.vue";
import FeedInfo from "./components/FeedInfo.vue";
import OpmlUpload from "./components/OPMLUpload.vue";
import FeedForList from "./components/FeedForList.vue";
import SupertokensLogin from "./components/SupertokensLogin.vue";
import SimplePagination from "./components/SimplePagination.vue";
import UserSetting from "./components/UserSetting.vue";
import TokensCost from "./components/TokensCost.vue";
import FaviconElement from "./components/FaviconElement.vue";
import RuleForList from "./components/RuleForList.vue";
import UserSettingForNotification from "./components/UserSettingForNotification.vue";

import TagBase from "./components/tags/Base.vue";
import EntryTag from "./components/tags/EntryTag.vue";
import EntryTagsList from "./components/tags/EntryTagsList.vue";
import FilterTag from "./components/tags/FilterTag.vue";
import TagsFilter from "./components/tags/TagsFilter.vue";
import RuleTag from "./components/tags/RuleTag.vue";
import FakeTag from "./components/tags/FakeTag.vue";

import PageHeaderHomeButton from "./components/page_header/HomeButton.vue";
import PageHeaderExternalLinks from "./components/page_header/ExternalLinks.vue";
import PageFooter from "./components/page_footer/Footer.vue";

import NotificationsApiKey from "./components/notifications/ApiKey.vue";
import NotificationsCreateRuleHelp from "./components/notifications/CreateRuleHelp.vue";
import Notifications from "./components/notifications/Block.vue";
import NotificationsLoadedOldNews from "./components/notifications/LoadedOldNews.vue";

import CollectionsNotification from "./components/collections/Notification.vue";
import CollectionsWarning from "./components/collections/Warning.vue";
import CollectionsBlock from "./components/collections/Block.vue";
import CollectionsBlockItem from "./components/collections/BlockItem.vue";
import CollectionsDetailedItem from "./components/collections/DetailedItem.vue";
import CollectionsSubscribingProgress from "./components/collections/SubscribingProgress.vue";
import CollectionsFeedItem from "./components/collections/FeedItem.vue";
import CollectionsPublicSelector from "./components/collections/PublicSelector.vue";
import CollectionsPublicIntro from "./components/collections/PublicIntro.vue";

import ScoreSelector from "./inputs/ScoreSelector.vue";

import ExternalUrl from "./values/ExternalUrl.vue";
import ValueFeedId from "./values/FeedId.vue";
import ValueDateTime from "./values/DateTime.vue";
import ValueScore from "./values/Score.vue";
import Icon from "./values/Icon.vue";
import SocialLink from "./values/SocialLink.vue";

import BodyListReverseTimeColumn from "./components/body_list/ReverseTimeColumn.vue";
import BodyListFaviconColumn from "./components/body_list/FaviconColumn.vue";
import BodyListEntryBody from "./components/body_list/EntryBody.vue";

import MainDescription from "./components/main/Description.vue";
import MainItem from "./components/main/Item.vue";
import MainNewsTitle from "./components/main/NewsTitle.vue";
import MainHeaderLine from "./components/main/HeaderLine.vue";
import MainBlock from "./components/main/Block.vue";

import SidePanelCollapseButton from "./components/side_pannel/CollapseButton.vue";

import WideLayout from "./layouts/WideLayout.vue";
import SidePanelLayout from "./layouts/SidePanelLayout.vue";

import {useSupertokens} from "@/stores/supertokens";

import VueCountdown from "@chenfengyuan/vue-countdown";

const app = createApp(App);

app.component("FeedsList", FeedsList);
app.component("EntriesList", EntriesList);
app.component("RulesList", RulesList);
app.component("ConfigSelector", ConfigSelector);
app.component("ConfigFlag", ConfigFlag);
app.component("EntryForList", EntryForList);
app.component("RuleConstructor", RuleConstructor);
app.component("DiscoveryForm", DiscoveryForm);
app.component("FeedInfo", FeedInfo);
app.component("OpmlUpload", OpmlUpload);
app.component("FeedForList", FeedForList);
app.component("SupertokensLogin", SupertokensLogin);
app.component("SimplePagination", SimplePagination);
app.component("UserSetting", UserSetting);
app.component("TokensCost", TokensCost);
app.component("FaviconElement", FaviconElement);
app.component("RuleForList", RuleForList);
app.component("UserSettingForNotification", UserSettingForNotification);

app.component("TagBase", TagBase);
app.component("EntryTag", EntryTag);
app.component("EntryTagsList", EntryTagsList);
app.component("FilterTag", FilterTag);
app.component("TagsFilter", TagsFilter);
app.component("RuleTag", RuleTag);
app.component("FakeTag", FakeTag);

app.component("PageHeaderHomeButton", PageHeaderHomeButton);
app.component("PageHeaderExternalLinks", PageHeaderExternalLinks);
app.component("PageFooter", PageFooter);

app.component("NotificationsApiKey", NotificationsApiKey);
app.component("NotificationsCreateRuleHelp", NotificationsCreateRuleHelp);
app.component("Notifications", Notifications);
app.component("NotificationsLoadedOldNews", NotificationsLoadedOldNews);

app.component("CollectionsNotification", CollectionsNotification);
app.component("CollectionsWarning", CollectionsWarning);
app.component("CollectionsBlock", CollectionsBlock);
app.component("CollectionsBlockItem", CollectionsBlockItem);
app.component("CollectionsDetailedItem", CollectionsDetailedItem);
app.component("CollectionsSubscribingProgress", CollectionsSubscribingProgress);
app.component("CollectionsFeedItem", CollectionsFeedItem);
app.component("CollectionsPublicSelector", CollectionsPublicSelector);
app.component("CollectionsPublicIntro", CollectionsPublicIntro);

app.component("ScoreSelector", ScoreSelector);

app.component("ExternalUrl", ExternalUrl);
app.component("ValueFeedId", ValueFeedId);
app.component("ValueDateTime", ValueDateTime);
app.component("ValueScore", ValueScore);
app.component("Icon", Icon);
app.component("SocialLink", SocialLink);

app.component("BodyListReverseTimeColumn", BodyListReverseTimeColumn);
app.component("BodyListFaviconColumn", BodyListFaviconColumn);
app.component("BodyListEntryBody", BodyListEntryBody);

app.component("MainDescription", MainDescription);
app.component("MainItem", MainItem);
app.component("MainNewsTitle", MainNewsTitle);
app.component("MainHeaderLine", MainHeaderLine);
app.component("MainBlock", MainBlock);

app.component("SidePanelCollapseButton", SidePanelCollapseButton);

app.component("WideLayout", WideLayout);
app.component("SidePanelLayout", SidePanelLayout);

app.component("vue-countdown", VueCountdown);

app.use(createPinia());
app.use(router);

app.use(CookieConsent.plugin, CookieConsent.defaultConfig);

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
