
No changes.

- ff-538 Refactored backend from Supertokens to the OIDC protocol
  - `FFUN_ENABLE_API` replaced with `FFUN_ENABLE_API_SPA`
  - All settings `FFUN_API_*` replaced with `FFUN_API_SPA_*`
  - Removed `VITE_FFUN_AUTH_MODE` for frontend, now frontend gets auth mode from the backend.
  - Removed `FFUN_APP_PORT`, `FFUN_API_PORT`.
- ff-577 — Introduced Caddy as a reverse proxy for the dev environment to have a more idiomatic OIDC setup.

TODO:

- Add a passage about changes in `FFUN_AUTH_*` configs
  - new way of configuration
  - migrating to the new way
