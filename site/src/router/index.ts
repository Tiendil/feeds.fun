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
import CRMView from "../views/CRMView.vue";
import * as e from "@/logic/enums";
import * as settings from "@/logic/settings";

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
      path: "/news/:tags*",
      name: e.MainPanelMode.Entries,
      component: NewsView
    },
    {
      path: "/rules/:tags*",
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
      path: "/show/:collectionSlug/:tags*",
      name: "public-collection",
      component: PublicCollectionView
    },
    {
      path: "/terms",
      name: "terms",
      component: CRMView,
      props: { content: settings.crmTerms, kind: "terms" }
    },
    {
      path: "/privacy",
      name: "privacy",
      component: CRMView,
      props: { content: settings.crmPrivacy, kind: "privacy" }
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: "/"
    }
  ],
  scrollBehavior(to, from, savedPosition) {
    return {top: 0};
  }
});

export default router;
