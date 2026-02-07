
# Introduction to the Feeds Fun development

```toml donna
kind = "donna.lib.specification"
```

This document provides an introduction to the Feeds Fun project for agents and developers who want to understand how to work with the Feeds Fun codebase.

## Project overview

Feeds Fun is a self-hosted news reader (RSS, ATOM, etc.) with LLM-powered tags for news articles.

- Reader automatically assigns tags to news.
- User creates rules to score news by tags.
- => User can filter and sort news by their semantics and score.

Rule examples:

- `elon-musk + space => -3`
- `nasa + space => +8`

## Technology stack

### Backend

- Python
- FastAPI
- PostgreSQL

### Frontend

- TypeScript
- Vue
- Vite
- Tailwind

## Infrastructure

- Keycloak for authentication
- Oauth2Proxy
- Caddy
- Docker

## Dictionary

## Points of interest

- `./docker` — dockerfiles and related artifacts.
- `./docs/examples` — example of how to run Feeds Fun with Docker.
- `./feeds_collections` — configs for feeds collections.
- `./ffun` — source code of the Feeds Fun backend.
- `./site` — source code of the Feeds Fun frontend.
- `./tags_quality_base` — validating set of news articles with tags for testing quality of tagging

## Specifications of interest

Check the next specifications:

- `{{ donna.lib.view("project:core:backend_architecture") }}` when you need to introduce any changes to the backend.
- `{{ donna.lib.view("project:core:frontend_architecture") }}` when you need to introduce any changes to the frontend.
