
- ff-468 — Tag form normalization:
           - `book-reviews | books-review | books-reviews | book-review -> book-review`
           - `gravity-axes` -> `gravity-axis`
           - `wooden-axes` -> `wooden-axe`
           It should significantly reduce tag duplication pollution, but "normal form" is not always a "readable form"
           => Some tags may have weird forms, like `arms-control` -> `arm-control`.
           We'll solve such issues in gh-435.
