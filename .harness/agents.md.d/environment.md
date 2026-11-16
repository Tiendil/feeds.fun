
## Environment

Read, edit, and search repository files on the host.

Invoke mise from the host. Task definitions determine whether their
commands run on the host or in Docker.

Commands that execute backend/frontend application code or require
backend/frontend dependencies MUST run through the corresponding
mise tasks.

Run `mise run docker:build` after changing development Docker
configuration or backend/frontend dependencies.
