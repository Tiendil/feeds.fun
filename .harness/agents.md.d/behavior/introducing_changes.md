
#### Feeds Fun validation

During implementation, you MAY run focused tests through permitted mise tasks.

During implementation, you MUST NOT run linters, formatters, full test suites, or Polish workflows unless the developer or an active workflow explicitly requires them at that stage.

When the planned changes are ready for final validation, assess each Polish workflow.
If the changes can affect the application code, tests, or checks that a Polish workflow covers, you MUST run that workflow to successful completion against the final repository state.

- Backend — `donna -p llm run @/workflows/polish-backend.donna.md`
- Frontend — `donna -p llm run @/workflows/polish-frontend.donna.md`

When both workflows apply, you MUST run the backend workflow first.
You MUST limit Polish validation to the applicable Donna workflows.
The developer or an active workflow MAY explicitly override these choices for the current changes.

When a Polish workflow applies, you MUST use its Donna command for final validation in place of separate runs of its linters, formatters, or full test suites, unless the developer or an active workflow explicitly requires separate execution at that stage.

Validate changes outside the Polish workflows' scope as follows:

- Agent instructions or their Cog generation: run `mise run harness:agents.md:generate` and inspect the generated `AGENTS.md`.
- Donna workflow definitions: run `donna -p llm validate @/path/to/workflow.donna.md` for each changed workflow and inspect its rendered instructions.
- Prose-only documentation or specifications: review the changed content, examples, references, and consistency with affected artifacts.
