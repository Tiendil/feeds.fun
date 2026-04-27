
### Changes

- ff-624 — Implemented support for integration plugins to improve the interaction of Feeds Fun with feed sources
  - Check README.md for details on how to add an integration plugin and what plugins are currently available.
  - Added integrations for Reddit, GitHub, YouTube, ArXiv, and Hacker News.
  - Improved HTML cleaning for LLM needs, now it removes all semantically meaningless attributes such as `class`, `id`, `style`, etc.
  - Improved news body purification at the frontend to protect it from JS interference and style pollution from the source.
