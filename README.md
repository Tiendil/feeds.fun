
# Supertokens

- [ ] default mode should use single user
- [ ] landing page
- [ ] protect only required views
- [ ] login widget
- [ ] logout button
- [ ] remove side panel from landing / main page
- [ ] stylize landing page
- [ ] resend magic link

# MVP

- [x] scoring
- [x] scoring rules editing
- [x] use structlog
- [x] smart tags ordering in gui (by popularity? by module of score?)
- [x] fix `network-domain-www-theatlantic-com`
- [x] statistics about tags
- [x] feeds on a user level (not global)
- [x] add feed throught gui
- [x] import opml throught gui
- [x] common way of processing HTTP errors
- [x] remove/unlink feed for user
- [x] common mechanism to refresh lists of news, feeds, rules on their changes
- [ ] simple (or not) users management
- [x] mark entriy processed with status: error/success
- [ ] load only feeds that are need at least by one user

# Errors

- [x] This model's maximum context length is 4097 tokens. However, you requested 4140 tokens (3116 in the messages, 1024 in the completion)
- [x] Tags normalization breaks `c#` tag to `c`

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
- [ ] likes/dislikes for entries => propose rules/tags on base of them

# Public MVP

- [ ] refactor API endpoints / names
- [ ] blog?
- [ ] some styles?
- [ ] minor mobile support?
- [ ] save global settings on backend?
- [ ] search for unprocessed entries and reprocess them periodically
- [ ] do not run openai on the old entries


# Backlog:

- [ ] personalized names for feeds
- [ ] personalized names for tags
- [ ] personalized names for tags
- [ ] normalize urls for feeds
- [ ] normalize urls for entities
- [ ] do not run processors for entries with duplicated content
- [ ] contact https://karl-voit.at/ about the tags?
- [ ] exit faster on ctrl+c. Need some way to stop background processors but do not affect ongoing DB requests, etc.


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
