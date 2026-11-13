
### `donna`

Use Donna to run project-local deterministic workflows when the developer, these instructions, or an active Donna workflow explicitly asks for one.

Donna controls workflow state only. Agents remain responsible for reading project instructions, using `depmesh` where applicable, editing files, running checks, and reporting results.

You may need to read the usage intructions for `donna -p llm skill usage` in these cases:

- You need to run a workflow first time in the session.
- You need to list available workflows first time in the session.

Use Donna's `llm` protocol for agent-facing commands unless a human explicitly asks for another protocol:

Depmesh is configured to log significant operation steps via `task` tool.

At the start of working session run `donna -p llm list` to list all available workflows.

Do not run `donna -p llm new-session` unless the developer explicitly asks to reset or start a fresh Donna session.

Special instructions:

- Use donna polish workflow to groom the code after you've introduced changes (instead of running linters, formatters and while tests manually).
