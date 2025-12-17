
**Operations required BEFORE UPDATE**:

We dropped support for Supertokens-based authentication (in multi-user mode) because Supertokens does not support the OIDC protocol well, lacks some features, and hides others behind paywalls. Instead of Supertokens, Feeds Fun now supports OIDC-compliant identity providers (IdP), e.g. Keycloak, Auth0, Okta, etc. If you used Supertokens-based authentication, you need to:
  - Migrate your users to a new IdP that supports OIDC protocol. `ffun users import-users-to-idp` could help you with that.
  - Update your Feeds Fun configuration accordingly (see examples: https://github.com/Tiendil/feeds.fun/tree/main/docs/examples) — they will be actualized shortly after the release.

Changes:

- ff-538 Refactored backend from Supertokens to the OIDC protocol. There are changes in environment variables:
  - `FFUN_ENABLE_API` replaced with `FFUN_ENABLE_API_SPA`
  - `FFUN_API_*` replaced with `FFUN_API_SPA_*`
  - Removed `VITE_FFUN_AUTH_MODE` for frontend, now frontend gets auth mode from the backend.
  - Removed `FFUN_APP_PORT`, `FFUN_API_PORT`.
- ff-576 — Track clicks on authentication-related buttons.
- ff-565 — Correct properties for session cookies (SPA <-> auth-proxy).
- ff-579 — Removed api methods with optional authentication. Not all auth proxies work well with optional auth.

Dev environment changes:

- ff-577 — Introduced Caddy as a reverse proxy for the dev environment to have a more idiomatic OIDC setup.
- ff-574 — Added configs for Pomerium auth proxy in dev environment.
- ff-569 — Styles for Keycloak themes.
- ff-581 — Added protection from the `X-*` headers injection into Caddy dev config.
- ff-571 — Closed access to `/realms/dev/account*` endpoints in Caddy dev config.
- ff-612 — Fixed logout behaviour, now logout is requested not only from the OAuth2-proxy, but also from Keycloak.
- ff-541 — CLI tool to import users into an Identity Provider `ffun users import-users-to-idp`.
