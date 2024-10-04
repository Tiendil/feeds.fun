**Operations required AFTER UPDATE**:

1. Run migrations `ffun migrate`
2. Run `ffun user-settings remove-deprecated-settings`
3. If you are using an OpenAI tag processor, specify a custom configuration file for tag processors with an API key. Details can be found in the updated README.md
4. If you want to periodically clean your database from old entries, add the call `ffun cleaner clean` to your cron tasks. It is recommended.

Changes:

- [gh-229](https://github.com/Tiendil/feeds.fun/issues/229) — Removed `Allow using OpenAI key for feeds in standard collections` user settings. It was confusing for users and not usable in the project's current state. Instead, you can specify an LLM API key to process collections per tag processor. By new logic, the service's owner is responsible for managing tags for all feeds in collections.
- [gh-245](https://github.com/Tiendil/feeds.fun/issues/245) — Implemented the universal LLM tag processor. Currently, it supports two API providers: OpenAI (ChatGPT) and Google (Gemini). Also:
    - The configuration of tag processors was moved to a separate file; see README.md for actual details.
    - The configuration of LLM models was moved to a separate file; see README.md for actual details.
    - You can configure multiple LLM tag processors with different parameters, including prompts, API keys, etc.
    - Token usage tracking has been replaced with cost tracking. User settings will convert automatically.
- Collections refactored. Now, they are configurable and empty by default. You can specify the path to the directory with collections configuration in `FFUN_FEEDS_COLLECTIONS_COLLECTION_CONFIGS`. An example of configuration can be found in the `./feeds_collections/collections`.
- `FFUN_META_MAX_ENTRIES_PER_FEED` setting moved to `FFUN_LIBRARY_MAX_ENTRIES_PER_FEED`.
