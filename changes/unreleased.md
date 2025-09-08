
- ff-491 — Adapting Feeds Fun for gpt-5 and new Responses API:
  - Removed "general" OpenAI model descriptions, kept only specific ones.
  - OpenAI token calculation now uses only the iktoken library.
  - Migrated to the new Responses API.
  - Removed `presence_penalty` and `frequency_penalty` LLM config parameters, since Responses API does not support them.
- ff-467 — Backbones of tag normalization.


TODO:

- Correct configs for each normalizer.
- README — add section about normalizers.
- Task for dashbord of normalizers.
- test on real data.
- check tags quality to use normalizers
- splitter: `on` vs `impact-on` (if we split by impact-on, we should skip splitting by `on`)
- parts_blacklist: test for support of complex phrases, like "how-to"
- white_list: produce `how-to` from `how-to-...`?, `day-to-day` (must produce preserved tags and do not stop processing), `free-to-play`, `before-and-after`, `once-upon-a-time` + add marker `final` to tags, to skipp all other normalizers (also, for domain processor)
- Establish order: `white_list` -> `part_replacer` -> `splitter` -> `parts_blacklist`
- normalizer to conver roman numerals to arabic ones
- normalizer for versions (?)
- what to do with `i, you, we, they, he, she, it, one, me, us, them, him, her`
- what to do with `be, am, is, are, was, were, been, being, do, does, did, have, has, had`
- try add more configs with copilot autocomplete
