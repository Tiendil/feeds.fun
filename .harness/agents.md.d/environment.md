
## Environment

All development-related operations MUST be performed in Docker containers, see `./docker-compose.yml` for details.

You MUST not perform any development-related operations directly on the host machine.

Most important commands have script shortcuts in `./bin` directory.

Command you are allowed to use:

- `./bin/backend-utils.sh` — run utils in the backend environment, for example `/bin/backend-utils.sh poetry run <your command>`
- `./bin/build-dev-containers.sh` — build base Docker images for development. Call this command after making changes to Docker configs or dependencies.
- `./bin/frontend-utils.sh` — run utils in the frontend environment.
- `./bin/taskwarior.sh` — run Taskwarrior commands related to project journaling.

Code and file searches MUST run on the host using host-installed tools, including `ast-grep` and `rg`, without Docker or development-helper wrappers.
Read and manipulate code on the host machine as well.
