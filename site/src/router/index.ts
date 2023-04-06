import { createRouter, createWebHistory } from 'vue-router'
import MainView from '../views/MainView.vue'
import FeedsView from '../views/FeedsView.vue'
import NewsView from '../views/NewsView.vue'

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
      name: 'feeds',
      component: FeedsView
    },
    {
      path: '/news',
      name: 'news',
      component: NewsView
    },

  ]
})

export default router
