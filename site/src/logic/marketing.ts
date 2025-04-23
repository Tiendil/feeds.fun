import {useRoute, useRouter} from "vue-router";
import type {RouteLocationNormalizedLoaded, Router} from "vue-router";
import * as settings from "@/logic/settings";

export function processUTM(route: RouteLocationNormalizedLoaded, router: Router, utmStorage: any) {
  const utmParams = ["utm_source", "utm_medium", "utm_campaign"];

  // extract UTM parameters from the URL
  const utmData = utmParams.reduce(
    (acc, param) => {
      const value = route.query[param];

      if (!value) {
        return acc;
      }

      if (Array.isArray(value)) {
        if (value[0]) {
          acc[param] = value[0];
        }

        return acc;
      }

      if (value) {
        acc[param] = value;
        return acc;
      }

      return acc;
    },
    {} as Record<string, string>
  );

  // remove UTM parameters from the URL if they exist
  if (Object.keys(utmData).length > 0) {
    const newQuery = {...route.query};

    utmParams.forEach((param) => {
      if (newQuery[param]) {
        delete newQuery[param];
      }
    });

    router.replace({query: newQuery});
  }

  // store UTM in local storage
  if (Object.keys(utmData).length == 0) {
    return;
  }

  utmStorage.value = utmData;
}
