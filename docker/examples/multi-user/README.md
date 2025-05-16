# An example of a single-user setup of Feeds Fun

You can up Feeds Fun in a single-user mode by following these steps:

```
git clone git@github.com:Tiendil/feeds.fun.git
cd ./feeds.fun/docker/examples/multi-user
docker compose up -d
```

Go to `http://localhost/` to access the web interface.

Enter your email, you should receive an email with a link to log in. Click on the link and you will be redirected to the Feeds Fun web interface.

**The comments in the `docker-compose.yml` and other files contain many details.** Those details are not required to run test instances, but we recommend reading (and changing some of them) before running Feeds Fun as a permanent service.

Check notes in [single-user example](../single-user/README.md) for more details about running a permanent instance of Feeds Fun — we try to avoid duplicating docs.

Below you can find some really important notes about running Feeds Fun as a permanent service.

## Use HTTPS for permanent instances

This example is configured to use HTTP only to simplify the setup.

You absolutely **MUST** use HTTPS for permanent instances of Feeds Fun, otherwise your data may be compromised, passwords leaked, and so on.

To turn HTTPS on you should (see comments in the corresponding files):

- Update Caddyfile to use HTTPS.
- Update ffun.env to use appropriate ports and domain names.
