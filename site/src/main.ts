import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

import FeedsList from "./components/FeedsList.vue";
import EntriesList from "./components/EntriesList.vue";
import TagsList from "./components/TagsList.vue";

import ValueUrl from "./values/URL.vue";
import ValueFeedId from "./values/FeedId.vue";
import ValueDateTime from "./values/DateTime.vue";
import ValueTag from "./values/Tag.vue";

const app = createApp(App)

app.component("FeedsList", FeedsList);
app.component("EntriesList", EntriesList);
app.component("TagsList", TagsList);

app.component("ValueUrl", ValueUrl);
app.component("ValueFeedId", ValueFeedId);
app.component("ValueDateTime", ValueDateTime);
app.component("ValueTag", ValueTag);

app.use(createPinia())
app.use(router)

app.mount('#app')
