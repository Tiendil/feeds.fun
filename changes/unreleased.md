
- ff-530 — Fixed a crash when tags renormalization is running in parallel with tags removal.
- ff-537 — Removed unnecessary alert dialog on sending login email.
- ff-527 — Fixed a bug when the CLI command to run migrations (`ffun yoyo migrate`) did not take an exclusive lock on migrations to prevent concurrent runs.
- ff-551 — Stopped normalizing native feed tags because Feeds Fun has no control over the logic that assigns them.
