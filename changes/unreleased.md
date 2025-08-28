
- ff-491 — GPT-5 Adoption,
  - Removed "general" OpenAI model descriptions, keepd only specific ones.
  - OpenAI token calculation now uses only tiktoken library.

TODO:

- check docker examples for model ids
- update default models in default config files
- check temperature for all new models
- reasoning tokens usage
- try setting grammar
- try tags
- try increase the number of tags
- try to reduce the length of tags (number of components)
- try verify/refine step as the final step
- validate grammar before using it
- larc strict-mode
- keep only ine top_p or temperature
- configure top_logprobs
- major version change?

-----------

Changes done:

- migrated to GPT-5-nano
- migrated to reponse API
- use lark grammar
