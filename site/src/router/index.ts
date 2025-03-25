import {createRouter, createWebHistory} from "vue-router";
import MainView from "../views/MainView.vue";
import AuthView from "../views/AuthView.vue";
import FeedsView from "../views/FeedsView.vue";
import NewsView from "../views/NewsView.vue";
import RulesView from "../views/RulesView.vue";
import DiscoveryView from "../views/DiscoveryView.vue";
import CollectionsView from "../views/CollectionsView.vue";
import SettingsView from "../views/SettingsView.vue";
import PublicCollectionView from "../views/PublicCollectionView.vue";
import * as e from "@/logic/enums";

// lazy view loading does not work with router.push function
// first attempt to router.push into not loaded view, will cause its loading, but will not change components

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "main",
      component: MainView
    },
    {
      path: "/auth",
      name: "auth",
      component: AuthView
    },
    {
      path: "/feeds",
      name: e.MainPanelMode.Feeds,
      component: FeedsView
    },
    {
      path: "/news",
      name: e.MainPanelMode.Entries,
      component: NewsView
    },
    {
      path: "/rules",
      name: e.MainPanelMode.Rules,
      component: RulesView
    },
    {
      path: "/discovery",
      name: e.MainPanelMode.Discovery,
      component: DiscoveryView
    },
    {
      path: "/collections",
      name: e.MainPanelMode.Collections,
      component: CollectionsView
    },
    {
      path: "/settings",
      name: e.MainPanelMode.Settings,
      component: SettingsView
    },
    {
      // TODO: adapt all other routes with tags to this approach
      path: "/show/:collectionSlug/:tags*",
      name: "public-collection",
      component: PublicCollectionView
    },
  ]
});

export default router;
