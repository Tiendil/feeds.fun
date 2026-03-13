
### Migration

- You need to upgrade your Postgres database to version 18 or higher to ensure compatibility with the latest version of Feeds Fun. This particular release will continue to support Postgres 15 (and above), but there are no guarantees that future releases will do so.
- If you have customized `models.toml` or `tag_processors.toml` configs, you need to update them according to the changes described in the "Changes" section below in the `ff-640` item.
- By default, the max news entry age is set to 30 days (was infinite before). If you want to keep the old behavior, set `FFUN_LIBRARY_MAX_ENTRY_AGE` to a very large value (e.g., `3650` for 10 years). You also may want to set `VITE_FFUN_ENTRIES_PERIOD_LIST`.

### Changes

- ff-587 — Feeds Fun now expects at least Postgres 18 as a database.
- ff-640 — Changes in LLM-related configs:
  - Config `max_tokens_per_entry` (`models.toml`) moved to the `llm_general` tag processor (`tag_processors.toml`) under the same name.
  - Config `text_parts_intersection` moved out of nested `tag_processors.llm_config` section to the root of `tag_processors` section (`tag_processors.toml`)
- ff-641 — Split the default scientific papers collections into multiple smaller ones. Improved collections UI on the main page.
- ff-637 — Added functionality to automatically unlink from feeds (to remove later) entries that are older than a specified age.
  - Added a new config `FFUN_LIBRARY_MAX_ENTRY_AGE` for the backend, which defines the maximum age of entries in the library.
  - Added a new config `VITE_FFUN_ENTRIES_PERIOD_LIST` for the frontend, which defines the list of periods that can be selected as filters for entries on the News view.
