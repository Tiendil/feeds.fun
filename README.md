
# MVP

- [x] scoring
- [x] scoring rules editing
- [ ] do not run openai on the old entries
- [ ] use structlog
- [ ] search for unprocessed entries and reprocess them periodically
- [x] smart tags ordering in gui (by popularity? by module of score?)
- [ ] fix `network-domain-www-theatlantic-com`
- [ ] common mechanism to refresh lists of news, feeds, rules on their changes
- [x] statistics about tags

# Errors

- [ ] This model's maximum context length is 4097 tokens. However, you requested 4140 tokens (3116 in the messages, 1024 in the completion)

# Closed MVP

- [ ] cache erros and display them somehow in gui
- [ ] multiple users
- [ ] every api endpoint must required auth
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
- [ ] Tag: unicode-in-caption or too-much-unicode-in-caption
- [ ] reduce amount the size of answers from backend
- [ ] in the news list highlight tags that are used in rules

# Public MVP

- [ ] refactor API endpoints / names
- [ ] blog?
- [ ] some styles?
- [ ] minor mobile support?
- [ ] save global settings on backend?

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
