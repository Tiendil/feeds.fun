---
name: session
description: Manage task-local temporary working files in the project `.session/` directory. Use whenever an agent needs to create scratch files, notes, temporary plans, intermediate reasoning artifacts, generated helper files, or other task-scoped temporary data; also use when the user asks to start a new session.
---

# Session

## Temporary Files

- Store every temporary file created during work on a task under `<project-root>/.session/`.
- Create `<project-root>/.session/` before creating temporary files if the directory does not already exist.
- Use files in `<project-root>/.session/` for task-scoped temporary information such as intermediate notes, plans, scratch artifacts, and working data.
- Do not place temporary task files outside `<project-root>/.session/`.

## New Sessions

When the user tells you to start a new session, remove all files and directories inside `<project-root>/.session/`.

Keep the `.session` directory itself available for later temporary files when practical.
