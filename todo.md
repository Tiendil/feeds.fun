

- [x] dev container for KeyCloak
  - [x] realm
  - [x] two users with passwords
  - [x] healthcheck for docker
  - [x] dependency for backend from the keycloak container
- [ ] check public redirect URL — there a lot of data in it
- [ ] Support api calls that require no auth? (public collections, info, etc.)
- [ ] AuthMode.oidc
- [ ] backend logic for oidc
- [ ] frontend logic for auth redirects
- [ ] backend logic for sessions
- [ ] frontend logic for sessions
- [ ] magic link login
- [ ] social login

Things to think about:

- logout initiated from the IdP side
- PKCE
- update GDPR-related docs
- create an epic/tasks with auth tech debt
- `spa` module for SPA API, instead of `api` module for universal API
- OIDC Discovery: load endpoints/algorithms from /.well-known/openid-configuration at runtime. Store just issuer, client_id, client auth method, and redirect/logout URIs.
- Increment primary version of project, because of breaking changes in auth?
- KeyCloak magic link auth/registration
- Add KeyCloak default users into README.md & multi-user instructions?
- Replace multi-user setup instructions with reference to the default dev environment?
- Implement example MCP server
- FastAPI docs generation
- In oidc mode we should save not "mode" in the users mapping, but an actual idp id.
- Remove API docs & api links from the menu?
- single-user & oidc & supertokens modes works via single docker-compose (in dev)
- try to keep html/css for keycloak theming in this repo
- Backup KeyCloak DB
- note: keycloack only allows configuring from files at first startup, later we should use the admin API to manage realms/users
- self-servicing pages
- unify apisix.yaml by moving common configs into templates
- use cookies
- auth/registration — both should work
- manually check behaviour of 401 on post
- remove technical headers in apixis before sending request to backend
- fix main page layout
- registration page, switching between login/registration
- fix single-user / multi-user examples
- Caddy should be configured to proxy /spa/login and, generally, all /spa urls?
