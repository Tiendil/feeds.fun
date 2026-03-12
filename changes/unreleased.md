
### Migration

- You need to upgrade your Postgres database to version 18 or higher to ensure compatibility with the latest version of Feeds Fun. This particular release will continue to support Postgres 15 (and above), but there are no guarantees that future releases will do so.
- If you have customized `models.toml` or `tag_processors.toml` configs, you need to update them according to the changes described in the "Changes" section below in the `ff-640` item.

### Changes

- ff-587 — Feeds Fun now expects at least Postgres 18 as a database.
- ff-640 — Changes in LLM-related configs:
  - Config `max_tokens_per_entry` (`models.toml`) moved to the `llm_general` tag processor (`tag_processors.toml`) under the same name.
  - Config `text_parts_intersection` moved out of nested `tag_processors.llm_config` section to the root of `tag_processors` section (`tag_processors.toml`)
