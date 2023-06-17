# Feeds Fun

- Web-based news reader. Self-hosted, if it is your way.
- Automatically assigns tags to news entries.
- You create rules to score news by tags.
- Then filter and sort news how you want.

# Motivation

I've subscribed to many news feeds and want to read only news interesting to me. To save time.

Plus, it is nice to access news from any device.

I did not find an open-source solution that suited my needs => decided to create my own.

Also, it is an excellent opportunity to learn and use new AI technologies.

# How to run a local version

```
git clone git@github.com:Tiendil/feeds.fun.git

cd ./feeds.fun

docker compose up -d
```

Then open http://localhost:5173/ in your browser.

This will start the API server and frontend, but not workers to process feeds.

To start workers, run:

```
./bin/backend-utils.sh poetry run ffun workers --librarian --loader
```

## Advanced configuration

All possible configs you can find in `settings.py` files.

Create `.env` in the root folder.

```
# Uncomment to enable supertokens auth: https://supertokens.com/

# FFUN_AUTH_MODE="supertokens"

# Uncomment and set the key to generate tags with OpenAI API
# ChatGPT is the main source of usable tags for news
# => You want these settings if you plan to self-host feeds.fun

# FFUN_LIBRARIAN_OPENAI_CHAT_35_PROCESSOR__ENABLED="True"
# FFUN_LIBRARIAN_OPENAI_CHAT_35_PROCESSOR__API_KEY="<your key>"
```

# Self-hosting

There are no ready-to-use docker images or PyPi/NPM packages yet.

But they will be.

For now, use [docker-compose.yml](docker-compose.yml) as an example.


# Development

## Utils

List of all backend utils:

```
./bin/backend-utils.sh poetry run ffun --help
```

## DB migrations

```
./bin/backend-utils.sh poetry run yoyo --help
```
