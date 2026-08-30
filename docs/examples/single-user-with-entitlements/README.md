# A single-user Feeds Fun setup with benefits and entitlements

**Version compatibility:** These instructions match the version of the repository you are viewing. On the `main` branch, they may describe development code that is not yet available in the `latest` Docker images because development images are not published to Docker Hub. If you encounter installation problems, use the instructions from the latest release tag and pin every Feeds Fun image in `docker-compose.yml` to that same version. Most of the time, the instructions on `main` should still work with the latest images.

**Note:** Use entitlement packages to limit the number of entries processed for a user.

This example enables entitlement enforcement and configures two benefit packages:

- `monthly-reader` provides 100 daily and 1000 monthly entry-processing tokens.
- `lifetime-token-pack` provides 10000 lifetime entry-processing tokens.

Unlike the regular single-user example, an entry linked to the user is processed only while the user has available tokens.

The configured processors assign domain, native, and uppercase-title tags without external API keys.

**Note:** Configuration and usage of entitlements & benefits in the multi-user setup is the same, single-user setup was chosen for simplicity only.

## Start the service

```shell
git clone git@github.com:Tiendil/feeds.fun.git
cd ./feeds.fun/docs/examples/single-user-with-entitlements
docker compose up -d
```

Open `http://localhost/` once before granting a benefit. The first authenticated request creates the internal user.

## Find the internal user ID

Open `http://localhost/`, go to the settings page, and copy the user id from the top of it.

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

You can inspect current grants with:

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

## Important notes

**The comments in the `docker-compose.yml` and other files contain important details.** Those details are not required to run example instances, but we recommend reading (and changing configs accordingly) before running Feeds Fun as a permanent service.

Check notes in the [single-user example](../single-user/README.md) and [multi-user example](../multi-user/README.md) for more details on running a permanent instance of Feeds Fun — we try to avoid duplicating docs, so we will not repeat the notes here.
