# An example of a multi-user setup of Feeds Fun

You can run Feeds Fun in multi-user mode by following these steps.

## Setup overview

### Local hostname configuration

To use fewer hacks and be more consistent with the production setup, we use custom domains `feeds.fun.local` and `idp.feeds.fun.local` for the purposes of this example.

- `feeds.fun.local` — Feeds Fun service;
- `idp.feeds.fun.local` — Identity Provider, such as Keycloak, for multi-user mode (see below).

Add the following line to your `/etc/hosts` file:

```
127.0.0.1 feeds.fun.local
127.0.0.1 idp.feeds.fun.local
```

Then, you can access the site at https://feeds.fun.local/

**We use self-signed TLS certificates for local development.** You need to accept them in your browser.

### Running the services

```
git clone git@github.com:Tiendil/feeds.fun.git
cd ./feeds.fun/docs/examples/multi-user
docker compose up -d
```

Go to `http://feeds.fun.local/` to access the web interface.

Application user:

- User: `alice`
- Password: `alice`

Go to `http://idp.feeds.fun.local/` to access the Identity Provider (Keycloak in this example).

Keycloak admin:

- User: `admin`
- Password: `admin`

## Important notes

**The comments in the `docker-compose.yml` and other files contain important details.** Those details are not required to run example instances, but we recommend reading (and changing configs accordingly) before running Feeds Fun as a permanent service.

Check notes in the [single-user example](../single-user/README.md) for more details on running a permanent instance of Feeds Fun — we try to avoid duplicating docs, so we will not repeat the notes here.

Below you can find some really important information about running Feeds Fun as a permanent service in a multi-user mode.

## Use HTTPS for permanent instances

You absolutely **MUST** use HTTPS for permanent instances of Feeds Fun, otherwise your data may be compromised, passwords leaked, and so on.

## Managing users

Feeds Fun does not manage users on its own. Instead, it relies on third-party services or proxies that must inject two HTTP headers into requests to Feeds Fun's private API endpoints.

- `X-FFun-Identity-Provider-Id` — the unique id of the Identity Provider that was used to authenticate the user.
- `X-FFun-User-Id` — the unique string id of the user in the Identity Provider.

Header names are configurable.

You may want to check [ffun.auth.settings](../../../ffun/ffun/auth/settings.py) for how to configure the list of allowed Identity Providers and other auth-related settings.

Feeds Fun backend identifies users by the combination of the Identity Provider id and the user id in that provider.

That means **you must never expose feeds fun to the internet without a proxy that sets those headers properly.** otherwise, anyone may set those headers by themselves and impersonate any user.

Feeds Fun frontend sends users to the predefined URLs — you may route users to your identity/authentication service from there.

You should be able to use whatever you want to provide those headers (and we would like to hear about your experience with different solutions). However, we recommend using [OIDC](https://de.wikipedia.org/wiki/OpenID_Connect)-based solutions, because they are widely used, supported, and the current de facto standard for user authentication and authorization.

## OIDC

To handle authentication via OIDC, Feeds Fun needs a third-party service that will handle user management, authentication, and authorization. Such services are called Identity Providers (IdP), OIDC providers, Authentication brokers, and so on — the terms differ because each service, besides core functionality, provides additional features that may vary widely.

There are multiple open-source and commercial OIDC providers available; they may differ in features and deployment architecture, but most should work fine with Feeds Fun — it only requires basic OIDC functionality.

We use [Keycloak](https://www.keycloak.org/) in this example because it is the most popular and stable open source Identity Provider. Other options include [ORY](https://www.ory.sh/), [Zitadel](https://zitadel.com/), [Authentik](https://goauthentik.io/), etc. Also, there are commercial services like [Auth0](https://auth0.com/).

## Keycloak + OAuth2-Proxy + Caddy

Our recommended setup includes:

- [Keycloak](https://www.keycloak.org/) as the Identity Provider.
- [OAuth2-Proxy](https://oauth2-proxy.github.io/oauth2-proxy/) as the authentication broker that sits between Feeds Fun and Keycloak.
- [Caddy](https://caddyserver.com/) as the reverse proxy in front of everything.

When the browser requests Feeds Fun, Caddy asks OAuth2-Proxy to authenticate the user. OAuth2-Proxy either finds an existing session or redirects the user to Keycloak for authentication. After successful authentication, Keycloak redirects the user back to OAuth2-Proxy, which creates a session, sets the required headers, and returns control to Caddy, which forwards the request to Feeds Fun.

Check comments in the config files from this example for more details about the setup and configuration.
