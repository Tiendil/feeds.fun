import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

import FeedsList from "./components/FeedsList.vue";
import EntriesList from "./components/EntriesList.vue";

import ValueUrl from "./values/URL.vue";
import ValueFeedId from "./values/FeedId.vue";
import ValueDateTime from "./values/DateTime.vue";

const app = createApp(App)

app.component("FeedsList", FeedsList);
app.component("EntriesList", EntriesList);

app.component("ValueUrl", ValueUrl);
app.component("ValueFeedId", ValueFeedId);
app.component("ValueDateTime", ValueDateTime);

app.use(createPinia())
app.use(router)

app.mount('#app')
