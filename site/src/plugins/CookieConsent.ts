
import "vanilla-cookieconsent/dist/cookieconsent.css";
import * as CookieConsent from "vanilla-cookieconsent";

import * as settings from "@/logic/settings";


// TODO: translations
// TODO: custom events tracking


export const plugin = {
  install(app: any, pluginConfig: any): void {
    app.config.globalProperties.$CookieConsent = CookieConsent;
    CookieConsent.run(pluginConfig);
  }
};


const plausibleId = 'plausible-script';

function syncPlausible(enabled: boolean): void {

  if (!settings.plausibleEnabled) {
    disablePlausible();
    return;
  }

  if (!enabled) {
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


export const defaultConfig = {

  revision: 1,

  onConsent({cookie}): void {
    syncPlausible(cookie.categories.includes('analytics'));
    console.log('onConsent', cookie);
  },

  onChange({cookie}): void {
    syncPlausible(cookie.categories.includes('analytics'));
    console.log('onChange', cookie);
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
          title: 'We use cookies',
          description: 'Cookie modal description',
          acceptAllBtn: 'Accept all',
          acceptNecessaryBtn: 'Reject all',
          showPreferencesBtn: 'Manage Individual preferences'
        },
        preferencesModal: {
          title: 'Manage cookie preferences',
          acceptAllBtn: 'Accept all',
          acceptNecessaryBtn: 'Reject all',
          savePreferencesBtn: 'Accept current selection',
          closeIconLabel: 'Close modal',
          sections: [
            {
              title: 'Somebody said ... cookies?',
              description: 'I want one!'
            },
            {
              title: 'Strictly Necessary cookies',
              description: 'These cookies are essential for the proper functioning of the website and cannot be disabled.',

              //this field will generate a toggle linked to the 'necessary' category
              linkedCategory: 'necessary'
            },
            {
              title: 'Performance and Analytics',
              description: 'These cookies collect information about how you use our website. All of the data is anonymized and cannot be used to identify you.',
              linkedCategory: 'analytics'
            },
            {
              title: 'More information',
              description: 'For any queries in relation to my policy on cookies and your choices, please <a href="#contact-page">contact us</a>'
            }
          ]
        }
      }
    }
  }
};
