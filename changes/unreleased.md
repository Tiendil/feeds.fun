**Operations required AFTER UPDATE**:

1. Run `ffun user-settings remove-deprecated-settings`
2. Set `FFUN_OPENAI_COLLECTIONS_API_KEY` if you want to provide users with free tagging for feeds in collections.

Changes:

- [gh-229](https://github.com/Tiendil/feeds.fun/issues/229) — Removed `Allow using OpenAI key for feeds in standard collections` user settings. It was confusing for users and not usable in the current state of the project. Instead, system setting `FFUN_OPENAI_COLLECTIONS_API_KEY` was introduced. By new logic, the service's owner is responsible for managing tags for all feeds in collections. I.e., for users, it will look like they get tagging for feeds in collections for free.
