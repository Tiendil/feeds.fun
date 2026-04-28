import {defineStore} from "pinia";
import {computedAsync} from "@vueuse/core";

import * as api from "@/logic/api";

export const useIntegrationsStore = defineStore("integrationsStore", () => {
  const integrations = computedAsync(async () => {
    return await api.getIntegrations();
  }, []);

  return {
    integrations
  };
});
