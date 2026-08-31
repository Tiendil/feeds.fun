
### Migration

- Replace `FFUN_BENEFITS_PACKAGE_TEMPLATES` with `FFUN_BENEFITS_PACKAGE_TEMPLATES_CONFIG`. The latter should contain a file path to a TOML file with benefits configuration. You can find an example of such a file in `docs/examples/single-user-with-entitlements/benefit_packages.toml`.

### Changes

- Benefits configuration moved from an environment variable to a TOML file.
