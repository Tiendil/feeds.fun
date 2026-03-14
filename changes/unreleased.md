
### Migration

- ...

### Changes

- ff-674 — Fixed behaviour when Feeds Fun added and removed news entries in loop when their published date is behind max allowed age but they are still returned by the feed.
  - Removed ordering of news by cataloged time from the news page, because detection of correct catalogged time is broken and nobody uses it.
