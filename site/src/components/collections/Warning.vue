<template>
  <div class="ffun-info-common">
    <h4>Check your feed URLs</h4>

    <p
      >Websites like
      <a
        href="https://reddit.com"
        target="_blank"
        >Reddit <i class="ti ti-external-link"/></a
      >
      or
      <a
        href="https://arxiv.org"
        target="_blank"
        >arXiv <i class="ti ti-external-link"/></a
      >
      provide multiple feeds by:</p
    >

    <ul>
      <li
        >Customizing news categories lists in URL (like
        <code class="inline-block">https://site.com/feed/rss?category1+category2</code>) instead of using separate
        URLs.</li
      >
      <li
        >Supporting different feed formats (like <code class="inline-block">https://site.com/feed/rss</code> and
        <code class="inline-block">https://site.com/feed/atom</code>).</li
      >
    </ul>

    <p
      >This can lead to the same news item appearing in multiple feeds, not being recognized as news from collections,
      and being processed with your API key. We do our best to detect such news, but there are always exceptions.</p
    >

    <p><strong>To get the most from free tagging in collections:</strong></p>

    <ul>
      <li>Use specific, granular feed URLs.</li>
      <li
        >Add feeds directly from
        <a
          class="ffun-normal-link"
          href="#"
          @click.prevent="goToCollections()"
          >collections</a
        >
        instead of using URLs from sites.</li
      >
    </ul>

    <user-setting-for-notification
      class=""
      kind="hide_message_check_your_feed_urls"
      button-text="Hide this message" />
  </div>
</template>

<script lang="ts" setup>
  import {useRouter} from "vue-router";
  import * as e from "@/logic/enums";

  const router = useRouter();

  function goToCollections() {
    router.push({name: e.MainPanelMode.Collections, params: {}});
  }
</script>
