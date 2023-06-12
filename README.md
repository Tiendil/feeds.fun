
# Closed MVP

- [ ] prepare preset lists of feeds to help new users to start
- [ ] fix rendering of feeds list, when feeds are not enough for one page
- [ ] cache erros and display them somehow in gui
- [ ] telegram channel of other platform
- [ ] names for feeds
- [ ] display feed for each entry
- [ ] filter by single feed
- [ ] tooltip for last entries period about top limit of how many entries can be retrieved
- [ ] in the news list highlight tags that are used in rules

# Public MVP

- [ ] reduce amount the size of answers from backend
- [ ] favicon
- [ ] openapi key per user
- [ ] blog
- [ ] some styles
- [ ] search for unprocessed entries and reprocess them periodically

# Open Source

- [ ] fill side panel of GitHub repository
  - [ ] fill about
  - [ ] fill tags/topics
- [ ] readme
- [ ] license
- [ ] remove fixtures from the history
- [ ] test running dev project from scratch (without preixisting DBs)
- [ ] refactor API endpoints / names
- [ ] update `commands` section in README

# Errors

- [ ] when login, frontend too fast colls `/supertokens/session/refresh`. Possibly it is because too fast refresh of login state.

# Backlog

- [ ] save global settings on backend
- [ ] minor mobile support
- [ ] load only feeds that are need at least by one user
- [ ] change user email
- [ ] invite link https://supertokens.com/docs/passwordless/common-customizations/disable-sign-up/passwordless-via-invite-link
- [ ] personalized names for feeds
- [ ] personalized names for tags
- [ ] personalized names for tags
- [ ] normalize urls for feeds and merge them
- [ ] normalize urls for entities and merge them
- [ ] do not run processors for entries with duplicated content
- [ ] contact https://karl-voit.at/ about the tags?
- [ ] exit faster on ctrl+c. Need some way to stop background processors but do not affect ongoing DB requests, etc.
- [ ] resend magic link counter is controlled on client (shoud be on backend?) and reseted after page refresh.
- [ ] remove building duplicated containers

# Rules

- [ ] likes/dislikes for entries => propose rules/tags on base of them

# Tags

- [ ] Tag: unicode-in-caption or too-much-unicode-in-caption

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
