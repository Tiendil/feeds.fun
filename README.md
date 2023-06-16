# Feeds Fun

- Web-based news reader. Self-hosted, if it is your way.
- Automatically assigns tags to news entries.
- You create rules to score news by tags.
- Then filter and sort news how you want.

# Motivation

I've subscribed to many news feeds and want to read only news interesting to me. To save time.

Plus, it is nice to access news from any device.

I did not find an open-source solution that suited my needs. So I decided to create my own.

Also, it is an excellent opportunity to learn and use new AI technologies.

# How to run a local version

```
git clone git@github.com:Tiendil/feeds.fun.git

cd ./feeds.fun

docker compose up -d
```

Then open http://localhost:5173/ in your browser.

# Self-hosting

There are no ready-to-use docker images or PyPi/NPM packages yet.

But they will be.

For now, use [docker-compose.yml](docker-compose.yml) as an example.
