
No changes.

- ff-538 — Support OIDC authentication.
  - `FFUN_ENABLE_API` replaced with `FFUN_ENABLE_API_SPA`
  - All settings `FFUN_API_*` replaced with `FFUN_API_SPA_*`
  - Removed `VITE_FFUN_AUTH_MODE` for frontend, now frontend gets auth mode from the backend.
  - Removed `FFUN_APP_PORT`, `FFUN_API_PORT`.

TODO:

- update README and another docs:
  - `FFUN_ENABLE_API` -> `FFUN_ENABLE_API_SPA`
  - `FFUN_API_*` -> `FFUN_API_SPA_*`
