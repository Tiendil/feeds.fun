
- ff-363 — Control the number of stored entries per feed, even if the feed is no longer loaded correctly.
- ff-362 — `ffun cleaner` now removes orphaned feeds, in addition to entries.
- ff-364 — Skip failed entries on parsing the feed, keeping the rest instead of skipping the entire feed.
- ff-365 — Silence parsing URL error for URLs with malformed hostnames.
- ff-372 — Better handling of `RemoteProtocolError` in loader for cases of "peer closed connection without sending complete message body"
- ff-373 — Trim too big entries (for LLM processing) in case `max_tokens_per_entry` limit is reached.
- ff-369 — HTML text cleaner now correctly processes broken surrogate Unicode characters.
