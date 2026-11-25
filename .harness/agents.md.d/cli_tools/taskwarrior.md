
### `taskwarrior`

`task` — Taskwarrior — is the project journal for significant agent-side work.

Use these command templates from the project root.
You MUST set `agent:` to your runtime name in each record you write.
In Codex, use `/root` for the primary agent and the full name returned by the spawn tool for a subagent, such as `/root/session__qa_automation` or `/root/subtask__reviewer_technical__subscription_cli`.
If the spawn tool supplies only an ID for addressing, use the runtime name from your initial assignment.

```bash
mise run journal:task -- log +journal +agent agent:"<agent-name>" kind:goal "<goal description>"
mise run journal:task -- log +journal +agent agent:"<agent-name>" kind:step "<phase progress or completion handoff>"
mise run journal:task -- log +journal +agent agent:"<agent-name>" kind:thought "<important thought>"
mise run journal:task -- log +journal +agent agent:"<agent-name>" kind:assumption "<important assumption>"
mise run journal:task -- log +journal +agent agent:"<agent-name>" kind:change "<what changed and where>"
```

Journal messages MUST be single-line strings.

You MUST log:

- Goals of long-running agent-side operations with `kind:goal`.
- Significant steps of long-running operations with `kind:step`.
- Significant thoughts during long-running operations with `kind:thought`.
- Significant assumptions during long-running operations with `kind:assumption`.
- Changes in project source code or project structure with `kind:change`.

You MAY add extra tags before the message.

```bash
mise run journal:task -- log +journal +agent agent:"<agent-name>" kind:"<message-kind>" +<extra-tag>... "<single-line journal message>"
```

For each non-trivial Donna action request or long-running agent task:

1. Write exactly one `goal` record at action-request or task start.
2. Write `step` records at significant phase boundaries.
3. Write `change` records after each meaningful source update batch.
4. Write one final `step` record immediately before reporting completion or handing work back to the developer.

You MUST consider these cases significant phase boundaries:

- A work phase expected to take more than 10 seconds.
- Transition from analysis or research to implementation.
- Transition to a new step in a multi-step process.
- Start or completion of a multi-file or multi-artifact change batch.
- A decision that changes implementation direction.

You MUST NOT log:

- CLI commands you execute.
- Elementary or trivial steps.

Use `journal:tail` to read recent records.
The actor column shows the runtime name in place of the `agent` tag when `agent:` is set.

```bash
mise run journal:tail -- --lines 20
```
