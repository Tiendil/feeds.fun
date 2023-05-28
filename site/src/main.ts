import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

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
import TagsFilterElement from "./components/TagsFilterElement.vue";
import DiscoveryForm from "./components/DiscoveryForm.vue";
import FeedInfo from "./components/FeedInfo.vue";
import EntryInfo from "./components/EntryInfo.vue";
import OpmlUpload from "./components/OPMLUpload.vue";
import FeedForList from "./components/FeedForList.vue";
import SupertokensLogin from "./components/SupertokensLogin.vue";

import ScoreSelector from "./inputs/ScoreSelector.vue";
import InputMarker from "./inputs/Marker.vue";

import ValueUrl from "./values/URL.vue";
import ValueFeedId from "./values/FeedId.vue";
import ValueDateTime from "./values/DateTime.vue";
import ValueTag from "./values/Tag.vue";
import ValueScore from "./values/Score.vue";

import WideLayout from "./layouts/WideLayout.vue";
import SidePanelLayout from "./layouts/SidePanelLayout.vue";

import { useSupertokens } from "@/stores/supertokens";

import VueCountdown from '@chenfengyuan/vue-countdown';

const app = createApp(App)

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
app.component("TagsFilterElement", TagsFilterElement);
app.component("DiscoveryForm", DiscoveryForm);
app.component("FeedInfo", FeedInfo);
app.component("EntryInfo", EntryInfo);
app.component("OpmlUpload", OpmlUpload);
app.component("FeedForList", FeedForList);
app.component("SupertokensLogin", SupertokensLogin);

app.component("ScoreSelector", ScoreSelector);
app.component("InputMarker", InputMarker);

app.component("ValueUrl", ValueUrl);
app.component("ValueFeedId", ValueFeedId);
app.component("ValueDateTime", ValueDateTime);
app.component("ValueTag", ValueTag);
app.component("ValueScore", ValueScore);

app.component("WideLayout", WideLayout);
app.component("SidePanelLayout", SidePanelLayout);

app.component('vue-countdown', VueCountdown);

app.use(createPinia())
app.use(router)

app.mount('#app')

import * as api from "@/logic/api";
import * as settings from "@/logic/settings";

if (settings.authMode === settings.AuthMode.Supertokens) {

    const supertokens = useSupertokens();

    // TODO: parametrize

    supertokens.init({apiDomain: "http://localhost:5173",
                      apiBasePath: "/supertokens",
                      appName: "Feeds Fun",
                      // TODO: increase to 1 minute
                      resendAfter: 6 * 1000});
}

else if (settings.authMode === settings.AuthMode.SingleUser) {
}

else {
    throw `Unknown auth mode: ${settings.authMode}`;
}

async function onSessionLost() {
    await supertokens.logout();
    router.push({ name: 'main', params: {} });
}

api.init({onSessionLost: onSessionLost});
