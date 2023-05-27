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

app.component('vue-countdown', VueCountdown);

app.use(createPinia())
app.use(router)

app.mount('#app')


const supertokens = useSupertokens();

// TODO: parametrize

supertokens.init({apiDomain: "http://127.0.0.1:8000",
                  apiBasePath: "/auth",
                  appName: "Feeds Fun"});


if (await supertokens.isLoggedIn()) {
    console.log("Already logged in");
}

else {

    async function onSignIn() {
    }


    async function onSignFailed() {
        await supertokens.clearLoginAttempt();
    }


    if (supertokens.hasInitialMagicLinkBeenSent()) {
        supertokens.handleMagicLinkClicked({onSignUp: onSignIn,
                                            onSignIn: onSignIn,
                                            onSignFailed: onSignFailed});
    }
}
