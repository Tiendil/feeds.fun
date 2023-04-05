
# MVP

## Layout

- http_handlers.py
- domain.py
- entities.py
- enums.py
- operations.py

## Restrictions

- single user
- http auth

## Functionality

- [ ] FEEDS
  - [x] save feeds to DB
  - [x] get next feed to load
  - [x] mark feed as loaded
- [ ] LIBRARY
  - [x] store entities by ids
  - [ ] get entities by list of ids
- [ ] LOADER
  - [x] load feeds from FEEDS, parse and store in LIBRARY
- [ ] ONTOLOGY
  - [ ] store tags for entities
  - [ ] get tags for entities
- [ ] LIBRARIAN
  - [ ] cli: get unprocessed entities from LIBRARY, ask GPT to classify them, store tags in ONTOLOGY
- [ ] VIEWER
  - [ ] scores are hardcoded in configs
  - [ ] HTTP API: get feeds
  - [ ] HTTP API: get entities sort by score and date
- [ ] Frontend GUI
  - [x] list of feeds
  - [ ] list of latest entities sorted by score and date
- [ ] Core
  - [ ] logging
- [ ] CLI
  - [x] load opml
  - [x] load feeds
- [ ] Bugs
  - [ ] normalized tags use `-` instead `_`. Why? Should we ban one of these charracters?
- [ ] Improvements
  - [ ] use structlog
  - [ ] search for unprocessed entries and reprocess them periodically

# Questions

- [x] Type of feed id: UUID
- [x] Type of entity id: UUID
- [x] Type of tag id: UUID

# Public MVP

- [ ] multiple users
- [ ] http base auth for multiple users
- [ ] Sentry for backend
- [ ] Sentry for frontend

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
