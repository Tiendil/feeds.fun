<template>
  <wide-layout>
    <div class="max-w-xl mx-auto px-6 py-12">
      <h1 class="text-3xl font-semibold mb-2">Sign in</h1>
      <p class="text-gray-600 mb-8">Access your personalized news workspace.</p>

      <form class="space-y-6" @submit.prevent="submit">
        <div>
          <label class="block text-sm font-medium text-gray-700" for="identifier">Email</label>
          <input
            id="identifier"
            v-model="identifier"
            type="email"
            name="identifier"
            autocomplete="email"
            class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500"
            required
          />
          <p v-for="message in fieldErrors.identifier" :key="message" class="mt-1 text-sm text-red-600">
            {{ message }}
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700" for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            name="password"
            autocomplete="current-password"
            class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500"
            required
          />
          <p v-for="message in fieldErrors.password" :key="message" class="mt-1 text-sm text-red-600">
            {{ message }}
          </p>
        </div>

        <div v-if="globalMessages.length" class="space-y-2">
          <p v-for="message in globalMessages" :key="message" class="text-sm text-red-600">
            {{ message }}
          </p>
        </div>

        <button
          type="submit"
          class="inline-flex w-full justify-center rounded-md bg-indigo-600 px-4 py-2 text-base font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          :disabled="loading"
        >
          <span v-if="loading">Signing in…</span>
          <span v-else>Sign in</span>
        </button>
      </form>

      <p class="mt-6 text-sm text-gray-600">
        Don't have an account yet?
        <router-link
          class="font-medium text-indigo-600 hover:text-indigo-500"
          :to="{name: 'auth-join', query: {return_to: returnTo}}"
        >
          Join now
        </router-link>
      </p>
    </div>
  </wide-layout>
</template>

<script lang="ts" setup>
import {computed, onMounted, reactive, ref, watch} from "vue";
import {useRoute} from "vue-router";
import axios from "axios";

interface KratosUiNode {
  attributes?: {
    name?: string;
    value?: string;
  };
  messages?: Array<{text?: string}>;
}

interface KratosUi {
  action: string;
  nodes: KratosUiNode[];
  messages?: Array<{text?: string}>;
}

interface KratosFlow {
  id: string;
  type: string;
  ui: KratosUi;
  return_to?: string | null;
}

const route = useRoute();

const flow = ref<KratosFlow | null>(null);
const identifier = ref("");
const password = ref("");
const loading = ref(false);
const fieldErrors = reactive<Record<string, string[]>>({});
const globalMessages = ref<string[]>([]);

function resolveRedirect(data: any): string | null {
  if (!data) {
    return null;
  }

  if (typeof data.redirect_browser_to === "string" && data.redirect_browser_to.length > 0) {
    return data.redirect_browser_to;
  }

  if (Array.isArray(data.continue_with)) {
    for (const item of data.continue_with) {
      if (item?.action === "redirect_browser_to" && typeof item.value === "string") {
        return item.value;
      }
    }
  }

  return null;
}

const returnTo = computed(() => {
  if (typeof route.query.return_to === "string" && route.query.return_to.length > 0) {
    return route.query.return_to;
  }
  if (flow.value?.return_to) {
    return flow.value.return_to;
  }
  return "/news";
});

function extractNodeValue(nodes: KratosUiNode[], name: string): string | null {
  for (const node of nodes) {
    if (node.attributes?.name === name) {
      if (typeof node.attributes.value === "string") {
        return node.attributes.value;
      }
      break;
    }
  }
  return null;
}

function extractNodeMessages(nodes: KratosUiNode[], name: string): string[] {
  for (const node of nodes) {
    if (node.attributes?.name === name) {
      return (node.messages ?? []).map((message) => message.text ?? "").filter((text) => text.length > 0);
    }
  }
  return [];
}

function resetFieldErrors() {
  for (const key of Object.keys(fieldErrors)) {
    delete fieldErrors[key];
  }
}

function restartFlow() {
  const target = returnTo.value || "/news";
  const url = new URL(window.location.origin + "/self-service/login/browser");
  url.searchParams.set("return_to", target);
  window.location.href = url.toString();
}

async function loadFlow(flowId: string) {
  try {
    const response = await axios.get<KratosFlow>("/self-service/login/flows", {
      params: {id: flowId},
      withCredentials: true
    });

    flow.value = response.data;

    const nodes = flow.value.ui?.nodes ?? [];
    identifier.value = extractNodeValue(nodes, "identifier") ?? identifier.value;
    password.value = "";
    resetFieldErrors();
    globalMessages.value = (flow.value.ui?.messages ?? [])
      .map((message) => message.text ?? "")
      .filter((text) => text.length > 0);
  } catch (error) {
    restartFlow();
    throw error;
  }
}

async function submit() {
  if (!flow.value) {
    return;
  }

  loading.value = true;
  resetFieldErrors();
  globalMessages.value = [];

  const nodes = flow.value.ui?.nodes ?? [];
  const csrfToken = extractNodeValue(nodes, "csrf_token");

  const payload: Record<string, string> = {
    method: "password",
    identifier: identifier.value,
    password: password.value
  };

  if (csrfToken) {
    payload.csrf_token = csrfToken;
  }

  try {
    const response = await axios.post(flow.value.ui.action, payload, {withCredentials: true});

    const redirectTarget =
      resolveRedirect(response.data) ??
      route.query.return_to ??
      flow.value.return_to ??
      "/news";

    if (typeof redirectTarget === "string" && redirectTarget.length > 0) {
      window.location.href = redirectTarget;
      return;
    }

    window.location.href = "/news";
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const response = error.response;
      if (response?.status === 400 && response.data?.ui) {
        flow.value = response.data as KratosFlow;
        const newNodes = flow.value.ui?.nodes ?? [];
        fieldErrors.identifier = extractNodeMessages(newNodes, "identifier");
        fieldErrors.password = extractNodeMessages(newNodes, "password");
        const messages = (flow.value.ui?.messages ?? []).map((message) => message.text ?? "").filter(Boolean);
        if (messages.length > 0) {
          globalMessages.value = messages;
        }
      } else if (response?.data?.error?.message) {
        globalMessages.value = [response.data.error.message];
      } else {
        globalMessages.value = [error.message ?? "Authentication failed"];
      }
    } else {
      globalMessages.value = ["Unexpected error during sign in"];
    }
  } finally {
    loading.value = false;
  }
}

watch(
  () => route.query.flow,
  (flowId) => {
    if (typeof flowId === "string" && flowId.length > 0) {
      loadFlow(flowId).catch(() => {});
    }
  }
);

onMounted(() => {
  const flowId = typeof route.query.flow === "string" ? route.query.flow : null;

  if (!flowId) {
    restartFlow();
    return;
  }

  loadFlow(flowId).catch(() => {});
});
</script>
