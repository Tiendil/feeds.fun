
import "vanilla-cookieconsent/dist/cookieconsent.css";
import * as CookieConsent from "vanilla-cookieconsent";

import * as settings from "@/logic/settings";


export const plugin = {
  install(app: any, pluginConfig: any): void {
    app.config.globalProperties.$CookieConsent = CookieConsent;
    CookieConsent.run(pluginConfig);
  },

};


export function isAnalyticsAllowed(): boolean {
  return CookieConsent.acceptedCategory('analytics');
}


const plausibleId = 'plausible-script';

function syncPlausible(): void {

  if (!settings.plausibleEnabled) {
    disablePlausible();
    return;
  }

  if (!isAnalyticsAllowed()) {
    disablePlausible();
    return;
  }

  enablePlausible();
}

function isPlausibleEnabled() {
  return document.getElementById(plausibleId) !== null;
}

function disablePlausible() {
  if (!isPlausibleEnabled()) {
    return;
  }

  // The simplest and straightforward way to disable smth is to reload the page
  // We expect that users will not reevaluate the cookie consent modal often
  window.location.reload();
}

function enablePlausible() {

  if (isPlausibleEnabled()) {
    return;
  }

  console.log('setup Plausible script');

  const script = document.createElement("script");
  script.id = plausibleId;
  script.src = settings.plausibleScript;
  script.async = true;
  script.defer = true;
  script.setAttribute("data-domain", settings.plausibleDomain);
  document.body.appendChild(script);
}


const _description = 'We use cookies and local storage for session tracking (required) and optional analytics. Please let us collect analytics to better understand how you use us and become the best news reader ever.';


export const defaultConfig = {

  revision: 1,

  onConsent({cookie}): void {
    syncPlausible();
  },

  onChange({cookie}): void {
    syncPlausible();
  },

  categories: {
    necessary: {
      enabled: true,
      readOnly: true
    },
    analytics: {
      enabled: true,
      readOnly: false
    }
  },

  language: {
    default: 'en',
    translations: {
      en: {
        consentModal: {
          title: 'We use cookies and local storage',
          description: _description,
          acceptAllBtn: 'Accept all',
          acceptNecessaryBtn: 'Reject all',
          showPreferencesBtn: 'Manage preferences'
        },
        preferencesModal: {
          title: 'Manage privacy preferences',
          acceptAllBtn: 'Accept all',
          acceptNecessaryBtn: 'Reject all',
          savePreferencesBtn: 'Accept current selection',
          closeIconLabel: 'Close',
          sections: [
            {
              description: _description
            },
            {
              title: 'Strictly necessary data',
              description: 'This data is essential for the proper functioning of the website and cannot be disabled.',

              linkedCategory: 'necessary',

              cookieTable: {
                headers: {
                  name: "Data",
                  description: "Description"
                },
                "body": [
                  {
                    name: "Session information",
                    description: "We store your session information which is absolutely necessary for the website to work."
                  }
                ]
              }
            },
            {
              title: 'Performance and analytics',
              description: 'These services collect information about how you use our website.',
              linkedCategory: 'analytics',

              cookieTable: {
                headers: {
                  name: "Service",
                  domain: "Domain",
                  description: "Description"
                },
                body: [
                  {
                    name: "Plausible",
                    domain: "plausible.io",
                    description: "EU-based, cookie-free service that helps us measure traffic and improve usability, without collecting personal data."
                  },
                  {
                    name: "Feeds Fun",
                    domain: "feeds.fun",
                    description: "We collect our own analytics to improve the service. We do not share this data with third parties."
                  }
                ]
              }
            }
          ]
        }
      }
    }
  }
};
