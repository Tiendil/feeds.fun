
## Environment

All development-related operations MUST be performed in Docker containers, see `./docker-compose.yml` for details.

You MUST not perform any development-related operations directly on the host machine.

Project commands are available as mise tasks. Run `mise tasks ls` to discover them.

Command you are allowed to use:

- `mise run backend:run -- <command>` — run commands in the backend environment.
- `mise run backend:poetry -- <arguments>` — run Poetry commands in the backend environment.
- `mise run backend:ffun -- <arguments>` — run Feeds Fun CLI commands in the backend environment.
- `mise run backend:yoyo -- <arguments>` — run Yoyo migration commands in the backend environment.
- `mise run docker:build` — build base Docker images for development. Call this command after making changes to Docker configs or dependencies.
- `mise run frontend:run -- <command>` — run utils in the frontend environment.
- `mise run journal:task -- <arguments>` — run Taskwarrior commands related to project journaling.

Code and file searches MUST run on the host using host-installed tools, including `ast-grep` and `rg`, without Docker or development-helper wrappers.
Read and manipulate code on the host machine as well.
