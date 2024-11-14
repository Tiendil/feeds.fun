
- ff-155 — Performance improvements.

  - use [orjson](https://github.com/ijl/orjson) instead of standard json lib for response serialization;
  - changed response format of `/api/get-last-entries` and `/api/get-entries-by-ids` API to reduce the size of the response and speed up its generation.
