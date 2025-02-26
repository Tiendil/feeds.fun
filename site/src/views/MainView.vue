<template>
<wide-layout>

  <header class="ffun-body-panel-header min-h-10 bg-slate-600">
    <ul class="ffun-body-panel-header-left-block">
    </ul>
  </header>

  <div class="bg-blue-500 text-white p-5 text-center">
    <h1 class="m-0 text-5xl">Feeds Fun</h1>
    <p class="mt-2 text-2xl">Personalized News for Professionals</p>
  </div>

    <div class="bg-slate-200 text-center p-5">
      <p class="text-3xl font-medium">
        Save over <strong class="text-green-700">80%</strong> of news-browsing time by focusing on what truly matters to you
      </p>
    </div>

    <div class="max-w-xl mx-auto my-5">
      <div class="ffun-info-good text-center">
        <h2 class="my-0">Single e-mail to log in</h2>
        <supertokens-login />
      </div>
    </div>

    <div class="bg-slate-200 text-center p-5">
      <p class="text-3xl font-medium">
        Smarter Way to Read News
      </p>
    </div>

    <div class="bg-white text-center my-5">
      <!-- <h1 class="m-0 text-3xl mb-4">How Feeds Fun Works</h1> -->
      <!-- <h1 class="m-0 text-3xl mb-4">Smarter Way to Read News</h1> -->

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
            <!-- <p>Feeds Fun automatically tags news articles based on their content—people, places, topics, games, and more.</p> -->
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

            <!-- Feeds Fun filters and sorts news based on your rules, so the most relevant stories are always on top. -->
          </template>
        </main-description>

        <!-- <main-description icon="ti-number-5"> -->
        <!--   <template #caption> -->
        <!--     Full transparency -->
        <!--   </template> -->

        <!--   <template #description> -->
        <!--     See exactly how your rules shape your feed—no black boxes, no hidden algorithms. Check our -->
        <!--   </template> -->
        <!-- </main-description> -->

      </div>
    </div>

    <div class="bg-slate-200 text-center p-5">
      <p class="text-3xl font-medium">
        Check our collections TODO
      </p>
    </div>

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
