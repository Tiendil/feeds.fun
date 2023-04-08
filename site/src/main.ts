import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

import FeedsList from "./components/FeedsList.vue";
import EntriesList from "./components/EntriesList.vue";
import TagsList from "./components/TagsList.vue";
import MainModeSwitcher from "./components/MainModeSwitcher.vue";
import ConfigSelector from "./components/ConfigSelector.vue";

import ValueUrl from "./values/URL.vue";
import ValueFeedId from "./values/FeedId.vue";
import ValueDateTime from "./values/DateTime.vue";
import ValueTag from "./values/Tag.vue";
import ValueScore from "./values/Score.vue";

const app = createApp(App)

app.component("FeedsList", FeedsList);
app.component("EntriesList", EntriesList);
app.component("TagsList", TagsList);
app.component("MainModeSwitcher", MainModeSwitcher);
app.component("ConfigSelector", ConfigSelector);

app.component("ValueUrl", ValueUrl);
app.component("ValueFeedId", ValueFeedId);
app.component("ValueDateTime", ValueDateTime);
app.component("ValueTag", ValueTag);
app.component("ValueScore", ValueScore);

app.use(createPinia())
app.use(router)

app.mount('#app')
