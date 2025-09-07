
- ff-491 — Adapting Feeds Fun for gpt-5 and new Responses API:
  - Removed "general" OpenAI model descriptions, kept only specific ones.
  - OpenAI token calculation now uses only the iktoken library.
  - Migrated to the new Responses API.
  - Removed `presence_penalty` and `frequency_penalty` LLM config parameters, since Responses API does not support them.
- ff-467 — Backbones of tag normalization.


TODO:

- Correct configs for each normalizer.
