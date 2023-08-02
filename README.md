# Feeds Fun

Web-based news reader. Self-hosted, if it is your way.

- Reader automatically assigns tags to news entries.
- You create rules to score news by tags.
- Filter and sort news how you want to read only what you want.
- ?????
- Profit.

# Motivation

I've subscribed to a lot of news feeds and want to read only news most interesting & important personaly for me.

Plus, it is nice to access news from any device.

I did not find an open-source solution that suited my needs => decided to create my own.

# Features

- Feeds management, including discovery by URL and tracking errors.
- Automatic tag assignment for every news entry.
- Rules to score news by tags.
- Filter news by tags: exclude entries by tags, show only entries with tags.
- Sort news by score, date, etc.
- Track read state of news, optionally hide read news.
- A lot of other features are comming.

# Official site

Last stable version is always accessible at https://feeds.fun/

It is free to use, should be stable, no resets, etc.

Just do not forget to set up your OpenAI API key to access full power of tags generation.

# Self-hosted version

- Backend is accessible as [ffun](https://pypi.org/project/ffun/) package on PyPI.
- Frontend is accessible as [feeds-fun](https://www.npmjs.com/package/feeds-fun) package on NPM.
- Use latest versions, they should be compatible with each other.

There no official docker images yet. Do not want to dictate how to organize your infrastructure — there are too many variations exists of how to prepare and run containers.

## Configuration

All configs can be redefined via environment variables or `.env` file in the working directory.

You can print all actual backend configs values with:

```
ffun print-configs
```

The output is not as pretty and ready for copying as it should be, but I'll improve it later.

All actual frontend configs can be found [here](site/src/logic/settings.ts).

Format of environment variables:

- For backend: `FFUN_<component>_<option>` or `FFUN_<component>_<option>__<suboption>`.
- For frontend: `VITE_FFUN_<component>_<option>` or `VITE_FFUN_<component>_<option>__<suboption>` — must be set on build time!

For example:

```
FFUN_AUTH_MODE="supertokens"

FFUN_LIBRARIAN_OPENAI_CHAT_35_PROCESSOR__ENABLED="True"
FFUN_LIBRARIAN_OPENAI_CHAT_35_PROCESSOR__API_KEY="<your key>"
```

## Backend

TODO: add must-have environment variables (enable...)

```
pip install ffun

# run DB migrations
ffun migrate

# run API server
uvicorn ffun.application.application:app --host 0.0.0.0 --port 8000 --workers 1

# run workers
ffun workers --librarian --loader
```

More details see in the architecture section.

## Frontend

TODO

# Architecture

ASGI application, that you run with `uvicorn` (in the example) provides only HTTP API to access the data and change user-related properties.

All actual work is done by workers, that you run with `ffun workers` command.

## Loader worker

Simply loads & parses feeds.

Can use HTTP proxies, see [configuration options](ffun/ffun/loader/settings.py)

## Librarian worker

Analyse feeds entries and assign tags to them.

All logic is split into processors. Each processor implements a single approach to produce tags and can be enabled/disabled via configuration.

See configuration options [here](ffun/ffun/librarian/settings.py)

Currently implemented processors:

- `DomainProcessor` — extract domain and subdomains from URL and saves them as a tags.
- `NativeTagsProcessor` — save tags that are received with the feed entry.
- `OpenAIChat35Processor` — asks OpenAI chatgpt-3.5 to detect tags.
- `OpenAIChat35FunctionsProcessor` — new version of `OpenAIChat35Processor` that uses OpenAI chatgpt-3.5 functions to detect tags.

# Development

## Run

```
git clone git@github.com:Tiendil/feeds.fun.git

cd ./feeds.fun
```

Start the API server and frontend:

```
docker compose up -d
```

Site will be accessible on http://localhost:5173/

Start workers:

```
./bin/backend-utils.sh poetry run ffun workers --librarian --loader
```

## Utils

List of all backend utils:

```
./bin/backend-utils.sh poetry run ffun --help
```

## DB migrations

Apply migrations:

```
./bin/backend-utils.sh poetry run ffun migrate
```

Create new migration:

```
./bin/backend-utils.sh poetry run yoyo new --message "what you want to do" ./ffun/<component>/migrations/
```

Pay attention. There are different directories layouts in the repository and in the docker containers => paths for migrations should be with only a single `ffun` directory.
