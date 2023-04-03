import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

import FeedsList from "./components/FeedsList.vue";

const app = createApp(App)

app.component("FeedsList", FeedsList);

app.use(createPinia())
app.use(router)

app.mount('#app')
