import { createRouter, createWebHistory } from 'vue-router'
import MainView from '../views/MainView.vue'
import FeedsView from '../views/FeedsView.vue'
import NewsView from '../views/NewsView.vue'
import RulesView from '../views/RulesView.vue'
import * as e from "@/logic/enums";

// lazy view loading does not work with router.push function
// first attempt to router.push into not loaded view, will cause its loading, but will not change components

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'main',
      component: MainView
    },
    {
      path: '/feeds',
      name: e.MainPanelMode.Feeds,
      component: FeedsView
    },
    {
      path: '/news',
      name: e.MainPanelMode.Entries,
      component: NewsView
    },
    {
      path: '/rules',
      name: e.MainPanelMode.Rules,
      component: RulesView
    },

  ]
})

export default router
