
### `difftastic`

Use `difft` as the default tool for inspecting code changes and whenever a semantic, syntax-aware diff is useful. Prefer stable, agent-readable output:

```bash
difft --display=inline --color=never --context=6 OLD-PATH NEW-PATH
difft --display=inline --color=never --context=6 --sort-paths OLD-DIR NEW-DIR
GIT_EXTERNAL_DIFF="difft --display=inline --color=never --context=6" git --no-pager diff -- PATH
GIT_EXTERNAL_DIFF="difft --display=inline --color=never --context=6" git --no-pager diff --cached -- PATH
```

Use a classic line-oriented diff, such as `git --no-pager diff --no-ext-diff` or `diff -u`, only when the task explicitly requires raw line-by-line output—for example, producing a patch, inspecting exact whitespace or line endings, or supplying unified-diff input to another tool. Do not choose a classic diff merely because a change is small or limited to text.
