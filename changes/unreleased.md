
### Migration

1. Run migrations `ffun migrate`.
2. Update your custom `tag_processors.toml` configs to use explicit processor routes.
   - Every processor now needs a `routes` list. Move old top-level `allowed_for_collections` and
     `allowed_for_users` values into a `[[tag_processors.routes]]` item and add a stable route `id`.
     For simple processors, use one route with an`id = "default"`.
   - Route order matters: when several routes can process an entry, Feeds Fun chooses the first matching route.
   - For LLM processors, remove old `collections_api_key`, `general_api_key`, and `general_api_key_warning`
     fields. Configure keys on routes with `api_key` instead.
   - To replace an old collection API key, add a route with `allowed_for_collections = true`,
     `allowed_for_users = false`, and `api_key = "<old collections_api_key>"`.
   - To replace an old general API key, add a route with `allowed_for_collections = true` and
     `allowed_for_users = true` values and `api_key = "<old general_api_key>"`.
   - To keep using user-provided API keys, add a route with `allowed_for_collections = false`,
     `allowed_for_users = true`, and `api_key = ""`.
   - See `ffun/ffun/librarian/fixtures/tag_processors.toml` and the `docs/examples/*/tag_processors.toml`
     files for complete examples.

### Changes

- ff-688 — Added depmesh and tach integration.
- ff-638 — Added `dispatcher` module as a central point for dispatching entries to tag processors.
  - Improved logic of choosing api_keys for LLM-based processors.
  - Added `can_see_tags` marker to control whether tags of a news entry are visible to a user.
