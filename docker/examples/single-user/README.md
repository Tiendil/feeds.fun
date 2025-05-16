# An example of a single-user setup of Feeds Fun

You can up Feeds Fun in a single-user mode by following these steps:

```
git clone git@github.com:Tiendil/feeds.fun.git
cd ./feeds.fun/docker/examples/single-user
docker compose up -d
```

Go to `http://localhost/` to access the web interface.

**The comments in the `docker-compose.yml` and other files contain many details.** Those details are not required to run test instances, but we recommend reading (and changing some of them) before running Feeds Fun as a permanent service.

## Caddy server

This example uses [Caddy](https://caddyserver.com/) as a reverse proxy. It is a simple and powerful web server with automatic HTTPS support.

In this example, Caddy is configured to serve on `localhost` and only via `HTTP` protocol. If you want to expose your Feeds Fun instance to the internet, you need to change the `Caddyfile` to use `HTTPS` and set up a domain name.

**ALWAYS** use a reverse proxy ([Caddy](https://caddyserver.com/), [Nginx](https://www.nginx.com/), etc.) in front of the Feeds Fun if you are going to expose it to the internet.
