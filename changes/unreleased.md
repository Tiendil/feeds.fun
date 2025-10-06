
**Operations required AFTER UPDATE**:

1. Run migrations `ffun migrate`

Changes:

- ff-517 — Implemented command `ffun cleaner renormalize` — it goes through all tags in the database and tries to (re)normalize them according to the current configs. It updates the rules and tags of entries accordingly.
