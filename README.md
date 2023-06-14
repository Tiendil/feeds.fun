
# Closed MVP

- [x] prepare preset lists of feeds to help new users to start
- [ ] better tags format. For example `raw:text`, `person:name`, `domain:the-tale.org`
- [ ] telegram channel or other platform

# Open Source

- [x] fill side panel of GitHub repository
  - [x] fill about
  - [x] fill tags/topics
- [ ] readme
- [x] license
- [x] remove fixtures from the history
- [x] test running dev project from scratch (without preixisting DBs)
- [ ] refactor API endpoints / names
- [ ] update `commands` section in README


# Public MVP

- [ ] fix rendering of feeds list, when feeds are not enough for one page
- [ ] filter by single feed (like a tag?)
- [ ] reduce amount the size of answers from backend
- [ ] favicon
- [ ] openapi key per user
- [ ] blog
- [ ] some styles
- [ ] search for unprocessed entries and reprocess them periodically
- [ ] cache erros and display them somehow in gui
- [ ] names for feeds
- [ ] display feed for each entry
- [ ] tooltip for last entries period about top limit of how many entries can be retrieved
- [ ] in the news list highlight tags that are used in rules

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
