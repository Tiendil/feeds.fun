<template>
  <side-panel-layout :reload-button="true">
    <template #main-header> Settings </template>

    <template #side-menu-item-1>
      <nav>
        <p class="ui-section-nav-title">On this page</p>

        <ul class="ui-section-nav-list">
          <li
            v-for="section in settingsSections"
            :key="section.id"
            class="ui-section-nav-item">
            <a
              :href="`#${section.id}`"
              class="ui-section-nav-link">
              {{ section.title }}
            </a>
          </li>
        </ul>
      </nav>
    </template>

    <div class="ui-content-rail">
      <ui-page-section
        id="settings-general"
        title="General">
        <label class="mr-1">User id</label>
        <input
          class="ffun-input w-72 cursor-pointer"
          disabled
          :value="userId" />
      </ui-page-section>

      <ui-page-section
        id="settings-subscriptions"
        title="Subscriptions">
        <p
          v-if="productState === null"
          class="text-sm text-slate-500">
          Loading...
        </p>

        <ui-empty-state v-else-if="productState.subscriptions.length === 0">
          No current subscriptions.
        </ui-empty-state>

        <ul
          v-else
          class="m-0 list-none space-y-2 p-0">
          <li
            v-for="(subscription, index) of productState.subscriptions"
            :key="`${subscription.startedAt.toISOString()}-${index}`"
            class="rounded border border-slate-300 bg-white px-3 py-2.5">
            <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
              <span class="font-semibold text-slate-900">{{ subscription.benefitTitle }}</span>

              <span
                class="inline-block rounded px-2 py-0.5 text-sm font-semibold"
                :class="subscriptionStatusProperties[subscription.status].class">
                {{ subscriptionStatusProperties[subscription.status].text }}
              </span>
            </div>

            <p class="m-0 mt-1 text-sm text-slate-700">{{ subscription.benefitDescription }}</p>

            <ul
              v-if="subscription.activeBenefits.length > 0"
              class="m-0 mt-2 list-disc pl-5 text-sm text-slate-700">
              <li
                v-for="benefit of subscription.activeBenefits"
                :key="benefit.kind">
                <span class="font-medium text-slate-900">{{
                  subscriptionBenefitNumberFormatter.format(benefit.value)
                }}</span>
                {{ e.EntitlementKindProperties.get(benefit.kind)?.text }}
                {{ benefit.value === 1 ? "token" : "tokens" }}
              </li>
            </ul>

            <p
              v-else
              class="m-0 mt-2 text-sm text-slate-500">
              No benefits currently active.
            </p>

            <p class="m-0 mt-1 text-sm text-slate-500">{{ subscriptionNextEvent(subscription) }}</p>
          </li>
        </ul>
      </ui-page-section>

      <ui-page-section
        id="settings-messages"
        title="Messages">
        <user-setting
          v-for="kind of messagesSettings"
          :key="kind"
          :kind="kind" />
      </ui-page-section>

      <ui-page-section
        id="settings-personal-feed-tagging"
        title="Personal feed tagging">
        <template #description>
          <p>
            Choose how old news from your personal feeds may be when Feeds Fun schedules it for tagging. This limit
            applies whether tagging uses your tokens or a user-supplied API key. News from predefined collections is
            not affected.
          </p>
        </template>

        <div class="mb-4">
          <user-setting
            kind="process_entries_not_older_than"
            class="!mb-1" />
          <ui-field-hint> A news item's age is based on the publication time reported by its feed. </ui-field-hint>
        </div>
      </ui-page-section>

      <ui-page-section
        id="settings-api-keys"
        title="Your API keys">
        <template #description>
          <p>
            Optionally provide an
            <external-url
              url="https://platform.openai.com/docs/api-reference/introduction"
              text="OpenAI" />
            or
            <external-url
              url="https://ai.google.dev/gemini-api/docs/api-key"
              text="Gemini" />
            API key to tag personal feeds using your provider account instead of Feeds Fun tokens.
          </p>

          <p>
            Feeds from
            <a
              href="#"
              @click.prevent="goToCollections()"
              >collections</a
            >
            are tagged automatically and do not use your API keys or tokens.
          </p>
        </template>

        <details class="ui-disclosure mb-4">
          <summary class="ui-disclosure-summary">How API keys are used</summary>

          <div class="ui-disclosure-body">
            <ul class="list-disc pl-5">
              <li>We use your key only for personal feeds that are not part of predefined collections.</li>
              <li>We stop using your key when its usage exceeds the monthly limit you set.</li>
              <li>
                If a feed has multiple subscribers with API keys, we use the key with the lowest usage in the current
                month.
              </li>
            </ul>

            <p class="font-medium text-slate-700">
              The more users set up an API key, the cheaper Feeds Fun becomes for everyone.
            </p>

            <p class="text-slate-600">API key usage statistics are available on this page.</p>
          </div>
        </details>

        <user-setting kind="openai_api_key" />
        <user-setting kind="gemini_api_key" />
        <user-setting kind="max_tokens_cost_in_month" />
      </ui-page-section>

      <ui-page-section
        id="settings-api-key-usage"
        title="API key usage">
        <template #description>
          <p>Estimated monthly token cost for requests made with your API keys.</p>

          <ul class="list-disc space-y-1 pl-5">
            <li>
              <strong class="font-medium text-slate-800">Estimated Used USD</strong>
              — cost of tokens in processed requests.
            </li>
            <li>
              <strong class="font-medium text-slate-800">Estimated Reserved USD</strong>
              — cost reserved for active or incorrectly processed requests.
            </li>
            <li>
              <strong class="font-medium text-slate-800">Estimated Total USD</strong>
              — total estimated token cost for the month.
            </li>
          </ul>
        </template>

        <p
          v-if="tokensCostData == null"
          class="text-sm text-slate-500">
          Loading...
        </p>

        <div
          v-else
          class="overflow-x-auto">
          <table class="w-full min-w-[56rem] rounded-lg border border-slate-300">
            <thead class="bg-slate-100 text-slate-800">
              <tr>
                <th class="w-32">Period</th>
                <th class="w-48">Estimated Used USD </th>
                <th class="w-48">Estimated Reserved USD</th>
                <th class="w-48">Estimated Total USD</th>
                <th class="w-48">% From Maximum</th>
              </tr>
            </thead>
            <tbody>
              <tokens-cost
                v-for="usage of tokensCostData"
                :key="usage.intervalStartedAt.toISOString()"
                :usage="usage" />

              <tr v-if="tokensCostData.length == 0">
                <td class="text-center">—</td>
                <td class="text-center">—</td>
                <td class="text-center">—</td>
                <td class="text-center">—</td>
                <td class="text-center">—</td>
              </tr>
            </tbody>
          </table>
        </div>
      </ui-page-section>

      <ui-page-section
        id="settings-token-usage"
        title="Token usage">
        <template #description>
          <p>
            Tagging one news item uses one token. Tokens are spent from the daily pool first, then monthly, then
            lifetime.
          </p>

          <p>
            Daily and monthly limits apply to UTC calendar periods, independently of your subscription period. A
            subscription change can update the current limit, but it does not start a new token period.
          </p>

          <ul class="list-disc space-y-1 pl-5">
            <li>
              <strong class="font-medium text-slate-800">Daily tokens</strong>
              — refill each day at 00:00 UTC.
            </li>
            <li>
              <strong class="font-medium text-slate-800">Monthly tokens</strong>
              — refill at 00:00 UTC on the first day of each month.
            </li>
            <li>
              <strong class="font-medium text-slate-800">Lifetime tokens</strong>
              — purchased separately and remain available until used.
            </li>
          </ul>

          <p>News from predefined collections does not use your tokens.</p>
        </template>

        <token-usage-statistics />
      </ui-page-section>

      <ui-page-section
        id="settings-danger-zone"
        title="Danger Zone">
        <ui-notice tone="danger">
          <p><strong>ATTENTION!</strong></p>

          <p>Operations in this section are irreversible and may lead to data loss and even account deletion.</p>
        </ui-notice>

        <ui-notice
          v-if="!globalState.isSingleUserMode"
          tone="danger">
          <ui-button
            variant="danger"
            @click.prevent="removeAccount()"
            >Remove account</ui-button
          >

          <label class="ml-1">Permanently remove your account and all your data.</label>
        </ui-notice>

        <ui-empty-state v-else> Account removal is not available in single-user mode. </ui-empty-state>
      </ui-page-section>
    </div>
  </side-panel-layout>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch, provide} from "vue";
  import {computedAsync} from "@vueuse/core";
  import * as api from "@/logic/api";
  import * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as settings from "@/logic/settings";
  import {useRouter} from "vue-router";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useGlobalState} from "@/stores/globalState";

  const globalState = useGlobalState();
  const globalSettings = useGlobalSettingsStore();

  provide("eventsViewName", "settings");

  globalSettings.mainPanelMode = e.MainPanelMode.Settings;

  const productState = computedAsync(async () => {
    globalSettings.dataVersion;

    return await api.getProductState();
  }, null);

  const tokensCostData = computedAsync(async () => {
    globalSettings.dataVersion;

    return await api.getResourceHistory({kind: "tokens_cost"});
  }, null);

  const subscriptionStatusProperties: Record<e.SubscriptionStatus, {text: string; class: string}> = {
    [e.SubscriptionStatus.Pending]: {text: "Pending", class: "bg-blue-100 text-blue-900"},
    [e.SubscriptionStatus.Trialing]: {text: "Trialing", class: "bg-blue-100 text-blue-900"},
    [e.SubscriptionStatus.Active]: {text: "Active", class: "bg-green-100 text-green-900"},
    [e.SubscriptionStatus.PastDue]: {text: "Past due", class: "bg-yellow-100 text-yellow-900"},
    [e.SubscriptionStatus.Paused]: {text: "Paused", class: "bg-yellow-100 text-yellow-900"},
    [e.SubscriptionStatus.Ended]: {text: "Ended", class: "bg-slate-200 text-slate-700"}
  };

  const subscriptionDateFormatter = new Intl.DateTimeFormat("en-US", {dateStyle: "medium"});
  const subscriptionBenefitNumberFormatter = new Intl.NumberFormat("en-US");

  function subscriptionNextEvent(subscription: t.ProductStateSubscription): string {
    if (subscription.endsAt !== null) {
      return `Ends ${subscriptionDateFormatter.format(subscription.endsAt)}`;
    }

    if (subscription.expectedRenewalAt !== null) {
      return `Renews ${subscriptionDateFormatter.format(subscription.expectedRenewalAt)}`;
    }

    return `Current period ends ${subscriptionDateFormatter.format(subscription.periodEndsAt)}`;
  }

  const userId = computed(() => {
    return globalState.userId == null ? "—" : globalState.userId;
  });

  const messagesSettings = [
    "hide_message_about_setting_up_key",
    "hide_message_about_adding_collections",
    "hide_message_check_your_feed_urls"
  ];

  const settingsSections = [
    {id: "settings-general", title: "General"},
    {id: "settings-subscriptions", title: "Subscriptions"},
    {id: "settings-messages", title: "Messages"},
    {id: "settings-personal-feed-tagging", title: "Personal feed tagging"},
    {id: "settings-api-keys", title: "Your API keys"},
    {id: "settings-api-key-usage", title: "API key usage"},
    {id: "settings-token-usage", title: "Token usage"},
    {id: "settings-danger-zone", title: "Danger zone"}
  ] as const;

  const router = useRouter();

  function goToCollections() {
    router.push({name: e.MainPanelMode.Collections, params: {}});
  }

  function removeAccount() {
    if (confirm("Are you sure you want to remove your account? THIS OPERATION IS NOT REVERSIBLE!")) {
      api.removeUser();
      globalState.logout();
    }
  }

  // TODO: check api keys on setup
  // TODO: basic integer checks
</script>
