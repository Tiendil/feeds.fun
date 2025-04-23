import {useRoute, useRouter} from "vue-router";
import type {Route, Router} from "vue-router";
import * as settings from "@/logic/settings";

export function processUTM(route: Route, router: Router, utmStorage: any) {
  const utmParams = ["utm_source", "utm_medium", "utm_campaign"];

  // extract UTM parameters from the URL
  const utmData = utmParams.reduce(
    (acc, param) => {
      const value = route.query[param];

      if (value) {
        acc[param] = Array.isArray(value) ? value[0] : value;
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
