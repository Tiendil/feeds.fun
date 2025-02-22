<template>
  <div class="ffun-info-common">
    <h4>Pay attention to your feed URLs</h4>

    <p>
      Some websites, like
      <external-url
        url="https://www.reddit.com"
        text="Reddit" />

      or
      <external-url
        url="https://arxiv.org"
        text="arXiv" />,

      provide multiple URLs for feeds:
    </p>

    <ul>
      <li>
        By customizing the list of categories, like
        <code class="inline-block">https://example.org/feed/rss?category1+category2</code>.
      </li>
      <li>
        By supporting different feed formats, like
        <code class="inline-block">https://example.org/feed/rss</code> and
        <code class="inline-block">https://example.org/feed/atom</code>.
      </li>
    </ul>

    <p>
      Consequently, the same news may appear in multiple feeds.
    </p>

    <p>
      We do our best to detect duplicates, but in some cases, they may slip through and lead to extra usage of your API key.
    </p>

    <p><strong>Please follow these recommendations:</strong></p>

    <ul>
      <li>Use short, granular feed URLs.</li>
      <li>If a feed URL can be split into multiple simpler URLs, add them separately.</li>
      <li>
        Add feeds directly from
        <a class="ffun-normal-link" href="#" @click.prevent="goToCollections()">
          collections</a
                       >
        instead of using URLs from websites.
      </li>
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
