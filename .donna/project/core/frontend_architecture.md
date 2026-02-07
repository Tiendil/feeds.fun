# Feeds Fun frontend architecture

```toml donna
kind = "donna.lib.specification"
```

Top-level description of the Feeds Fun frontend architecture and code structure.

## Modules

All frontend is placed in the `./site` directory, which is a Vue3 project. The main namespaces of the backend are:

- `./src/assets` — general static assets, like icons, fonts, etc.
- `./src/components` — Vue components.
- `./src/css` — general Tailwind CSS styles.
- `./src/inputs` — small Vue components related to user input, like forms, buttons, etc.
- `./src/layouts` — top-level Vue components that define the page layouts.
- `./src/logic` — general frontend logic, like API client, utils, etc.
- `./src/plugins` — Vue plugins.
- `./src/router` — Vue router configuration.
- `./src/stores` — state management with Pinia.
- `./src/values` — small Vue components related to displaying simple values.
- `./src/views` — Vue components related to pages, like news view, feeds view.

The view "inherits" the layout and use components (from `./src/components`) to display the required information to the user. Components may use smaller components from `./src/inputs` and `./src/values`.
