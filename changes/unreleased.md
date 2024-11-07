
In this release, we added a bunch of tracking functionality to better understand how users interact with the app.

This analytics:

- is strongly for our internal use;
- uses only internal IDs — does not contain emails, urls, etc.
- in most cases does not exceed what we already have in logs and database — just a more convenient way to access the data.

Changes:

- Frontend dependencies upgraded.
- ff-141 — Track frontend events `news_link_opened`, `news_body_opened`.
- ff-103 — Added `in_collection` marker to `feed_linked` and `feed_unlinked` events.
- ff-142 — CLI command to track aggregated metrics.
- ff-143 — Fixed a situation when, after removing a feed on the Feeds page, the feeds list was not updated.
- ff-145 — Track users' interest in feeds.fun social channels.
- ff-119 — Track OPML imports.
- ff-112 — Track subscriptions on feeds from collections.
