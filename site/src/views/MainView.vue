<template>
<wide-layout>

  <div class="ffun-page-header bg-white">
    <div class="ffun-page-header-center-block">
      <page-header-external-links :show-api="false"/>
    </div>
  </div>

  <hr/>

  <div class="p-5 text-center">
    <h1 class="m-0 text-5xl">Feeds Fun</h1>
    <p class="mt-2 text-2xl">Transparent Personalized News</p>
  </div>

  <main-header-line>
    Save over <strong class="text-green-700">80%</strong> of news-browsing time by focusing on what truly matters to you
  </main-header-line>

  <div class="max-w-xl mx-auto my-5">
    <div class="ffun-info-good text-center">
      <h2 class="my-0">Single e-mail to log in</h2>
      <supertokens-login />
    </div>
  </div>

  <main-header-line>
    Smarter way to read news
  </main-header-line>

  <div class="bg-white text-center my-5">
    <div class="max-w-3xl mx-auto space-y-6">

      <main-description icon="ti-number-1">
        <template #caption>
          Subscribe to sites
        </template>

        <template #description>
          <p class="text-lg font-medium">Give us the site URL and we do the rest.</p>
        </template>
      </main-description>

      <main-description icon="ti-number-2">
        <template #caption>
          Get automatic tagging
        </template>

        <template #description>
          <div>
            <main-news-title class="" title="UFO crashes in Central Park" :score="null" />

            <fake-tag
              uid="ufo"
              name="ufo"
              :link="null"
              css-modifier="positive"/>

            <fake-tag
              uid="news-dot-fake"
              name="news.fake"
              link="http://example.com"
              css-modifier="negative" />

            <fake-tag
              uid="new-york"
              name="new-york"
              :link="null"
              css-modifier="positive" />

            <fake-tag
              uid="space-exploration"
              name="space-exploration"
              :link="null"
              css-modifier="positive" />

          </div>

        </template>
      </main-description>

      <main-description icon="ti-number-3">
        <template #caption>
          Create scoring rules
        </template>

        <template #description>

          <div class="grid grid-cols-2 justify-items-start">

            <div class="">

              <fake-tag
                uid="sci-fi"
                name="sci-fi"
                :link="null"
                css-modifier="positive" />

              <i class="ti ti-arrow-right"></i>

              <span class="cursor-pointer text-purple-700 text-xl">+5</span>

            </div>

            <div class="">

              <fake-tag
                uid="news-dot-fake"
                name="news.fake"
                link="http://example.com"
                css-modifier="negative" />

              <i class="ti ti-arrow-right"></i>

              <span class="cursor-pointer text-purple-700 text-xl">-55</span>

            </div>

            <div class="">
              <fake-tag
                uid="ufo"
                name="ufo"
                :link="null"
                css-modifier="positive" />

              <i class="ti ti-plus"></i>

              <fake-tag
                uid="new-york"
                name="new-york"
                :link="null"
                css-modifier="positive" />

              <i class="ti ti-arrow-right"></i>

              <span class="cursor-pointer text-purple-700 text-xl">+8</span>

            </div>

            <div class="">
              <fake-tag
                uid="space-exploration"
                name="space-exploration"
                :link="null"
                css-modifier="positive" />

              <i class="ti ti-arrow-right"></i>

              <span class="cursor-pointer text-purple-700 text-xl">+21</span>

            </div>

          </div>

        </template>
      </main-description>

      <main-description icon="ti-number-4">
        <template #caption>
          Read what matters
        </template>

        <template #description>

          <div class="justify-items-start">

            <main-news-title title="New mission on Mars" :score="21" />

            <main-news-title class="opacity-75" title="Sci-fi novel about UFO in New Yourk" :score="13" />

            <i class="opacity-65 block ti ti-dots justify-self-center"></i>

              <main-news-title class="opacity-55" title="UFO crashes in Central Park" :score="-26" />

            </div>

        </template>
      </main-description>

    </div>
  </div>

  <main-header-line>
    Check our collections TODO
  </main-header-line>

    <div class="bg-white text-center p-5">
      <h1 class="m-0 text-3xl mb-4">How Feeds Looks Like</h1>

      <img
        class="border-2 rounded border-slate-300 mx-auto"
        src="/news-filtering-example.png"
        alt="News filtering example" />

    </div>
  </wide-layout>
</template>

<script lang="ts" setup>
  import * as settings from "@/logic/settings";
</script>
