
# MVP

## Restrictions

- single user
- http auth

## Functionality

- [ ] FEEDS
  - [ ] cli: import opml file
- [ ] STORAGE
  - [ ] store entities by ids
  - [ ] get entities by list of ids
- [ ] LOADER
  - [ ] cli: load feeds from FEEDS, parse and store in STORAGE
- [ ] LIBRARY
  - [ ] store tags for entities
  - [ ] get tags for entities
- [ ] LIBRARIAN
  - [ ] cli: get unprocessed entities from STORAGE, ask GPT to classify them, store tags in ONTOLOGY
- [ ] VIEWER
  - [ ] scores are hardcoded in configs
  - [ ] HTTP API: get feeds
  - [ ] HTTP API: get entities sort by score and date
- [ ] Frontend GUI
  - [ ] list of feeds
  - [ ] list of latest entities sorted by score and date

# Questions

- [x] Type of feed id: UUID
- [x] Type of entity id: UUID
- [x] Type of tag id: UUID
