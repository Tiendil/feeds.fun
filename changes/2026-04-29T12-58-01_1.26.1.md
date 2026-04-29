
- ff-685 — Set used USD to 0 for LLM requests that were rejected by a provider (authentication failure, quota exceeded, etc.). That behavior caused noticeable fake growth in usage stats due to issues on the providers' side or quota restrictions.
