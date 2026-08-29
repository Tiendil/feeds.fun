# A single-user Feeds Fun setup with benefits and entitlements

**Version compatibility:** These instructions match the version of the repository you are viewing. On the `main` branch, they may describe development code that is not yet available in the `latest` Docker images because development images are not published to Docker Hub. If you encounter installation problems, use the instructions from the latest release tag and pin every Feeds Fun image in `docker-compose.yml` to that same version. Most of the time, the instructions on `main` should still work with the latest images.

This example enables entitlement enforcement and configures two benefit packages:

- `monthly-reader` provides 100 daily and 1000 monthly entry-processing tokens.
- `lifetime-token-pack` provides 10000 lifetime entry-processing tokens.

Unlike the regular single-user example, an entry linked to the user is processed only while the user has available tokens.

## Start the service

```shell
git clone git@github.com:Tiendil/feeds.fun.git
cd ./feeds.fun/docs/examples/single-user-with-entitlements
docker compose up -d
```

Open `http://localhost/` once before granting a benefit. The first authenticated request creates the internal user.

## Find the internal user ID

```shell
docker compose exec postgres \
  psql --username ffun --dbname ffun --tuples-only --no-align \
  --command 'SELECT id FROM u_users;'
```

The command prints the user UUID used by the benefit commands below.

## Grant a benefit

To grant the renewable package as a subscription for its default 31-day period:

```shell
docker compose exec backend-api ffun benefits apply-subscription \
  --user-id <user-uuid> \
  --benefit-id monthly-reader
```

To grant the lifetime token pack as a one-time purchase:

```shell
docker compose exec backend-api ffun benefits apply-one-time-purchase \
  --user-id <user-uuid> \
  --benefit-id lifetime-token-pack
```

The configured processors assign domain, native, and uppercase-title tags without external API keys. You can inspect current grants with:

```shell
docker compose exec backend-api ffun entitlements list --user-id <user-uuid>
```

Personal API keys retain their legacy behavior and authorize linked entries without consuming entitlements. To exercise entitlement enforcement with an LLM processor, configure its route with a service-level API key instead of adding a personal key in the web interface.

## Permanent installations

The comments in `docker-compose.yml` and the other files contain important operational details. Before using this setup permanently:

- Replace the `:latest` image tags with matching released backend and frontend versions.
- Replace `FFUN_USER_SETTINGS_SECRET_KEY` in `ffun.env`.
- Configure a reverse proxy and HTTPS before exposing the service to the internet.
- Read the [changelog](https://github.com/Tiendil/feeds.fun/blob/main/CHANGELOG.md) before upgrading.
