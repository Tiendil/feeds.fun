
### Migration

1. Run migrations `ffun migrate`

### Changes

- ff-674 — Fixed behaviour when Feeds Fun added and removed news entries in the loop when their published date is behind the max allowed age, but they are still returned by the feed.
  - In most places, ordering of entries refactored from `created_at` to `published_at`.
  - The logic related to the time of cataloging news entry was removed from the backend, because it worked incorrectly.
  - News entries with the publish date older than `FFUN_LIBRARY_MAX_ENTRY_AGE` now will not be saved to the database.
  - Removed ordering of news by cataloged time from the news page, because detection of correct catalogged time is broken, and nobody uses it.
  - For the news entries that appear in multiple feeds, the published date is now determined from the user's feeds, not from the first feed where the news entry is encountered.
  - If a feed changes the news entry's published date, it will be updated (saved) next time the feed is processed.
  - Added CLI command `ffun cleaner shrink-feeds` to unlink old news entries from feeds, so they can be removed as orphans later.
