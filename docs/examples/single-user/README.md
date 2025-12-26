# An example of a single-user setup of Feeds Fun

You can up Feeds Fun in a single-user mode by following these steps:

```
git clone git@github.com:Tiendil/feeds.fun.git
cd ./feeds.fun/docs/examples/single-user
docker compose up -d
```

Go to `http://localhost/` to access the web interface.

**The comments in the `docker-compose.yml` and other files contain important details.** Those details are not required to run example instances, but we recommend reading (and changing configs accordingly) before running Feeds Fun as a permanent service.

Below you can find some really important notes about running Feeds Fun as a permanent service in a single-user mode.

## Tag processor configs

Set API keys in the settings section of the site to turn on the LLM-based tagging.

Tag processor configs can be found in [./tag_processors.yml](./tag_processors.yml) file. Prompts in them are similar to the ones used on the [feeds.fun](https://feeds.fun) site. You may want to play with them to get the best results for your needs.

**Best practices:**

- Set an OpenAI or Gemini API key to get the best experience from using the Feeds Fun.

## Caddy server

This example uses [Caddy](https://caddyserver.com/) as a reverse proxy. It is a simple and powerful web server with automatic HTTPS support.

**Best practices:**

- **ALWAYS** use a reverse proxy ([Caddy](https://caddyserver.com/), [Nginx](https://www.nginx.com/), etc.) in front of the Feeds Fun if you are going to expose it to the internet.

## Feeds Fun versions and migrations

This example uses the `latest` tag of the Feeds Fun images, so you will always get the latest version for your experiments. It is ok for testing, but not for production environments — we do our best to support automatic database migration between versions, but in some rare cases you may need to do some manual migrations.

**Best practices:**

- Replace `:latest` tag of the Feeds Fun images with a specific version tag (e.g. `:1.19.0`) in the `docker-compose.yml` file.
- Check [CHANGELOG](https://github.com/Tiendil/feeds.fun/blob/main/CHANGELOG.md) before upgrading to a new version.
