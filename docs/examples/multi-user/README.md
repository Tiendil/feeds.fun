# An example of a multi-user setup of Feeds Fun

You can up Feeds Fun in a multi-user mode by following these steps.

## Setup

### Setting the hosts

To use less hacks in dev configuration and be more consistent with production setup, we use custom domains `feeds.fun.local` & `idp.feeds.fun.local` for local development.

- `feeds.fun.local` — Feeds Fun service;
- `idp.feeds.fun.local` — identity provider, such as Keycloak, for multi-user mode (see below).

Add the following line to your `/etc/hosts` file:

```
127.0.0.1 feeds.fun.local
127.0.0.1 idp.feeds.fun.local
```

Then, you can access the site at http://feeds.fun.local/

**We use self-signed TLS certificates for local development.** You need to accept them in your browser.

### Running the services

```
git clone git@github.com:Tiendil/feeds.fun.git
cd ./feeds.fun/docs/examples/multi-user
docker compose up -d
```

Go to `http://feeds.fun.local/` to access the web interface.

User: `alice`
Password: `alice`

Go to `http://idp.feeds.fun.local/` to access the identity provider (Keycloak in this example).

User: `admin`
Password: `admin`

## Important notes

**The comments in the `docker-compose.yml` and other files contain important details.** Those details are not required to run test instances, but we recommend reading (and changing configs accordingly) before running Feeds Fun as a permanent service.

Check notes in [single-user example](../single-user/README.md) for more details about running a permanent instance of Feeds Fun — we try to avoid duplicating docs, so we will not repeat notes here.

Below you can find some really important information about running Feeds Fun as a permanent service.

## Use HTTPS for permanent instances

You absolutely **MUST** use HTTPS for permanent instances of Feeds Fun, otherwise your data may be compromised, passwords leaked, and so on.

## Users managers

Feeds Fun does not manage users by itself. Instead, it relies on third-party services/proxies that should provide two headers for the privatwe api endpoints of Feeds Fun.

- `X-FFun-Identity-Provider-Id` — the unique id of the identity provider that was used to authenticate the user.
- `X-FFun-User-Id` — the unique string id of the user in the identity provider.

Header names are configurable.

Feeds Fun backend identifies users by the combination of the identity provider id and the user id in that provider.

Feeds Fun fronted sends users to the predefined URLs — you may route users to your identity/authentication service from there.

You should be able to use whatever you want to provide those headers (and we would like to hear about your experience with different solutions). However, we recommend using [OIDC](https://de.wikipedia.org/wiki/OpenID_Connect)-based solutions, because they are widely used, supported, and the current de facto standard for user authentication and authorization.

## OIDC

To hand authentication via OIDC, Feeds Fun needs a third-party service that will handle user management, authentication, and authorization. Such services are called Identity Providers (IdP), OIDC providers, Authentication brokers, and so on — terms differ because each service, besides core functionality, provides additional features which may differ a lot.

There are multiple open source and commercial OIDC providers available; they may differ in features and in the architecture of deployment, but most of them should work fine with Feeds Fun — it only requires basic OIDC functionality.

We use [Keycloak](https://www.keycloak.org/) in this example, because it is the most popular and stable open source Identity provider. Other options include [ORY](https://www.ory.sh/), [Zitadel](https://zitadel.com/), [Authentik](https://goauthentik.io/), etc. Also, there are commercial services like [Auth0](https://auth0.com/).

## Keycloak + OAuth2-Proxy + Caddy

Our recommended setup includes:

- [Keycloak](https://www.keycloak.org/) as the Identity Provider.
- [OAuth2-Proxy](https://oauth2-proxy.github.io/oauth2-proxy/) as the authentication broker that sits between Feeds Fun and Keycloak.
- [Caddy](https://caddyserver.com/) as the reverse proxy in front of everything.

When the browser requests Feeds Fun, Caddy asks OAuth2-Proxy to authenticate the user. OAuth2-Proxy either finds an existing session or redirects the user to Keycloak for authentication. After successful authentication, Keycloak redirects the user back to OAuth2-Proxy, which creates a session and sets the required headers before forwarding the request to Feeds Fun.

Check comments in the config files from this example for more details about the setup and configuration.
