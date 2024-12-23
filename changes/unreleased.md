**Operations required AFTER UPDATE**:

1. Run migrations `ffun migrate`

Changes:

- ff-174 — Custom API entry points for OpenAI and Gemini clients.
- ff-175 — Export feeds to OPML file.
- ff-171 — Simplified rules creation:
  - The rules creation form was moved to the tags filter.
  - Rules now allow specifying excluded tags (will not apply if the news has any of them).
  - Tags under the news caption now behave as tags in the tags filter.
  - Button `[more]` on the tags line under the news caption now opens the whole news.
  - Openned news items now always show all tags.
  - Only a single news item now can be opened.
  - Performance of the News page improved 2-3 times.
