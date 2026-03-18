
This update should finish the series of changes started with feed cleanup improvements in `1.23.0`, which revealed a set of unhandled corner cases in feed processing, leading to the misbehavior of Feeds Fun. Now we postulate that the basis of entry lifetime management is the times of their ingestion (first and last), not any dates received from the feed sources.

### Migration

1. Run migrations `ffun migrate`

### Changes

- ff-677 — Remove only entries that are absent from the loaded feeds.
- ff-678 — Make the entry publish date in the GUI equal to the date of the first entry ingestion, because the feed-based publish date is absolutely unreliable.
