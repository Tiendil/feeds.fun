
- ff-491 — Adapting Feeds Fun for gpt-5 and new Responses API:
  - Removed "general" OpenAI model descriptions, kept only specific ones.
  - OpenAI token calculation now uses only the iktoken library.
  - Migrated to the new Responses API.
  - Removed `presence_penalty` and `frequency_penalty` LLM config parameters, since Responses API does not support them.
- ff-467 — Minimal valuable implementation of tag normalization. For details, see README.md.
- ff-500 — Silenced the error when a news server disconnects during network communication.
- ff-497 — Silenced the error when a news server disconnects without sending all the data.
- ff-496 — Better SLL error handling.
