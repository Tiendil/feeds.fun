
# MVP

- [ ] scoring
- [ ] scoring rules editing
- [ ] use structlog
- [ ] search for unprocessed entries and reprocess them periodically
- [ ] move scoring & sorting out of backend?
- [ ] run console commands constantly in backgroud?
- [ ] save global settings on backend?

# Closed MVP

- [ ] multiple users
- [ ] http base auth for multiple users
- [ ] Sentry for backend
- [ ] Sentry for frontend
- [ ] metrics for frontend
- [ ] telegram channel of other platform
- [ ] close openapi stand at base auth
- [ ] names for feeds
- [ ] display feed for each entry
- [ ] filter by single feed
- [ ] flexible gui layout? aka flex css, etc.
- [ ] favicon
- [ ] config-menu should change accoring main-mode
- [ ] tooltip for last entries period about top limit of how many entries can be retrieved
- [ ] do not show all entries in one page by default (only on scroll)

# Public MVP

- [ ] blog?
- [ ] some styles?
- [ ] minor mobile support?

# Backlog:

- [ ] personalized names for feeds
- [ ] personalized names for tags
- [ ] personalized names for tags
- [ ] normalize urls for feeds
- [ ] normalize urls for entities


# Commands

```
cd ./ffun

poetry run yoyo apply

poetry run yoyo rollback --all

poetry run yoyo new -m "name" ./ffun/????/migrations

poetry run ffun load-opml ../fixtures/feedly.opml

```

```
psql -h localhost -U ffun ffun

```
