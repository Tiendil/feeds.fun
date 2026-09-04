<template>
  <side-panel-layout :reload-button="false">
    <template #main-header> Discover feeds </template>

    <template #side-menu-item-1>
      <ui-section-navigation :sections="discoverySections" />
    </template>

    <div class="ui-content-rail">
      <ui-page-section
        :id="navigation.discoverySectionIds.addFeed"
        title="Add a feed">
        <template #description>
          <p>Paste a website or direct RSS/Atom feed URL.</p>

          <details class="ui-disclosure">
            <summary class="ui-disclosure-summary">How to choose a feed URL</summary>

            <div class="ui-disclosure-body">
              <p>Some websites provide multiple feeds whose news may overlap.</p>

              <ul class="list-disc pl-5">
                <li>Prefer specific, granular feed URLs.</li>
                <li>Do not subscribe to multiple formats of the same feed, such as both RSS and Atom.</li>
                <li>When a combined feed can be split into simpler feeds, add those feeds separately.</li>
                <li v-if="settings.hasCollections">
                  Prefer feeds from
                  <a
                    href="#"
                    @click.prevent="goToCollections()"
                    >collections</a
                  >
                  when they are available.
                </li>
              </ul>

              <p>Overlapping feeds can produce duplicate news and unnecessary API-key or token usage.</p>
            </div>
          </details>
        </template>

        <discovery-form />
      </ui-page-section>

      <ui-page-section
        :id="navigation.discoverySectionIds.importOPML"
        title="Import OPML">
        <template #description>
          <p>
            <external-url
              url="https://en.wikipedia.org/wiki/OPML"
              text="OPML" />
            is a widely used format for transferring feed lists between applications.
          </p>

          <p>Export an OPML file from your previous reader and import it into Feeds Fun.</p>
        </template>

        <opml-upload />
      </ui-page-section>
    </div>
  </side-panel-layout>
</template>

<script lang="ts" setup>
  import {provide} from "vue";
  import {useRouter} from "vue-router";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import * as e from "@/logic/enums";
  import * as navigation from "@/logic/navigation";
  import * as settings from "@/logic/settings";

  const globalSettings = useGlobalSettingsStore();
  const router = useRouter();

  provide("eventsViewName", "discovery");

  globalSettings.mainPanelMode = e.MainPanelMode.Discovery;

  const discoverySections = [
    {id: navigation.discoverySectionIds.addFeed, title: "Add a feed"},
    {id: navigation.discoverySectionIds.importOPML, title: "Import OPML"}
  ] as const;

  function goToCollections() {
    router.push({name: e.MainPanelMode.Collections, params: {}});
  }
</script>
