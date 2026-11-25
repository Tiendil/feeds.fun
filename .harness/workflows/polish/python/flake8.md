Instructions on fixing special cases:

- `E800 Found commented out code` — remove the commented out code.
- `CCR001 Cognitive complexity is too high` — ignore by adding `# noqa: CCR001` at the end of the line.
- `CCR002 Function "x" has N arguments that exceeds max allowed M` — ignore by adding `# noqa: CCR002` at the end of the line.
- `F821 undefined name` when there are missing imports — add the necessary import statements at the top of the file.
- `F821 undefined name` in all other cases — ask the developer to fix it manually.
