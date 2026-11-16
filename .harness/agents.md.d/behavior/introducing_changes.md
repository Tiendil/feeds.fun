
#### Feeds Fun validation

During implementation, you MAY run focused tests through permitted mise tasks.

During implementation, you MUST NOT run linters, formatters, full test suites, or the Polish workflow unless the developer or an active workflow explicitly requires them at that stage.

When the planned changes are complete and ready for final validation, assess whether any changes can affect behavior or checks within the scope declared in `workflows/polish.donna.md`:

- If they can, you MUST run `donna -p llm run @/workflows/polish.donna.md` to successful completion.
- If they cannot, you MUST NOT run the Polish workflow.

The developer or an active workflow MAY explicitly override this choice for the current changes.

When the Polish workflow applies, you MUST use it during final validation instead of running its linters, formatters, or full test suites separately, unless the developer or an active workflow explicitly requires separate execution at that stage.

Validate changes outside the Polish workflow's scope as follows:

- Agent instructions or their Cog generation: run `mise run harness:agents.md:generate` and inspect the generated `AGENTS.md`.
- Donna workflow definitions: run `donna -p llm validate @/path/to/workflow.donna.md` for each changed workflow and inspect its rendered instructions.
- Prose-only documentation or specifications: review the changed content, examples, references, and consistency with affected artifacts.
