import {createApp} from "vue";
import {createPinia} from "pinia";
import {Bar as ChartBar} from "vue-chartjs";

import App from "./App.vue";
import router from "./router";

import "./style.css";

import * as CookieConsent from "./plugins/CookieConsent";
import {configurePlots} from "./logic/plots";

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
import SimplePagination from "./components/SimplePagination.vue";
import UserSetting from "./components/UserSetting.vue";
import TokensCost from "./components/TokensCost.vue";
import TokenUsageStatistics from "./components/TokenUsageStatistics.vue";
import ProductTokens from "./components/ProductTokens.vue";
import NewsToolbar from "./components/NewsToolbar.vue";
import AppTooltip from "./components/AppTooltip.vue";
import FaviconElement from "./components/FaviconElement.vue";
import RuleForList from "./components/RuleForList.vue";
import UserSettingForNotification from "./components/UserSettingForNotification.vue";

import UiPageSection from "./components/ui/PageSection.vue";
import UiFieldHint from "./components/ui/FieldHint.vue";
import UiEmptyState from "./components/ui/EmptyState.vue";
import UiButton from "./components/ui/Button.vue";

import FeedListColumns from "./components/feed_list/Columns.vue";
import FeedEntriesPerDayChart from "./components/feed_list/FeedEntriesPerDayChart.vue";

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
import BodyListEntryCover from "./components/body_list/EntryCover.vue";
import BodyListReferences from "./components/body_list/References.vue";
import BodyListReference from "./components/body_list/Reference.vue";
import IntegrationsYouTube from "./integrations/YouTube.vue";

import MainDescription from "./components/main/Description.vue";
import MainItem from "./components/main/Item.vue";
import MainNewsTitle from "./components/main/NewsTitle.vue";
import MainHeaderLine from "./components/main/HeaderLine.vue";
import MainBlock from "./components/main/Block.vue";
import MainIntegrationsTable from "./components/main/IntegrationsTable.vue";
import MainShowMoreButton from "./components/main/ShowMoreButton.vue";

import SidePanelCollapseButton from "./components/side_pannel/CollapseButton.vue";

import WideLayout from "./layouts/WideLayout.vue";
import SidePanelLayout from "./layouts/SidePanelLayout.vue";

import VueCountdown from "@chenfengyuan/vue-countdown";

const app = createApp(App);

configurePlots();

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
app.component("SimplePagination", SimplePagination);
app.component("UserSetting", UserSetting);
app.component("TokensCost", TokensCost);
app.component("TokenUsageStatistics", TokenUsageStatistics);
app.component("ProductTokens", ProductTokens);
app.component("NewsToolbar", NewsToolbar);
app.component("AppTooltip", AppTooltip);
app.component("FaviconElement", FaviconElement);
app.component("RuleForList", RuleForList);
app.component("UserSettingForNotification", UserSettingForNotification);

app.component("UiPageSection", UiPageSection);
app.component("UiFieldHint", UiFieldHint);
app.component("UiEmptyState", UiEmptyState);
app.component("UiButton", UiButton);

app.component("FeedListColumns", FeedListColumns);
app.component("FeedEntriesPerDayChart", FeedEntriesPerDayChart);

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
app.component("BodyListEntryCover", BodyListEntryCover);
app.component("BodyListReferences", BodyListReferences);
app.component("BodyListReference", BodyListReference);
app.component("IntegrationsYouTube", IntegrationsYouTube);

app.component("MainDescription", MainDescription);
app.component("MainItem", MainItem);
app.component("MainNewsTitle", MainNewsTitle);
app.component("MainHeaderLine", MainHeaderLine);
app.component("MainBlock", MainBlock);
app.component("MainIntegrationsTable", MainIntegrationsTable);
app.component("MainShowMoreButton", MainShowMoreButton);

app.component("SidePanelCollapseButton", SidePanelCollapseButton);

app.component("WideLayout", WideLayout);
app.component("SidePanelLayout", SidePanelLayout);

app.component("ChartBar", ChartBar);
app.component("VueCountdown", VueCountdown);

app.use(createPinia());
app.use(router);
app.use(CookieConsent.plugin, CookieConsent.defaultConfig);

app.mount("#app");
