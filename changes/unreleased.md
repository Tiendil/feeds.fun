
**Configs migration:** if you are have turned on OpenAI ChatGPT processors, like `FFUN_LIBRARIAN_OPENAI_CHAT_35_FUNCTIONS_PROCESSOR__ENABLED="True"` or `FFUN_LIBRARIAN_OPENAI_CHAT_35_PROCESSOR__ENABLED="True", remove their configs and add configs for OpenAI General Processor, like `FFUN_LIBRARIAN_OPENAI_GENERAL_PROCESSOR__ENABLED="True"`, instead. The semantic of the configs is the same.

- [gh-227](https://github.com/Tiendil/feeds.fun/issues/227) — Old OpenAI ChatGPT processors is replaced with OpenAI General Processor which utilizes power of GPT-4o-mini model.
