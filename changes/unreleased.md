### Changes

- ff-406 Added `ffun feeds unlink <feed_ids>` command to unlink specified feeds from all users.
- ff-664 Improved type checking — `Any` type is disallowed (mostly).
  - Unified URLs parsing error handling.
  - Fixed parsing of URLs like `at://did:plc:<id>/app.bsky.actor.profile/self` (presented in Bluesky HTML).
- ff-670 `/robots.txt`, `/sitemap.xml`, `/sitemaps/pages.xml`.
