DB migration required: **no**

### Changes

- ff-665 Renamed development scripts in `bin` and updated references.
  - Renamed five scripts to their new `dev-*` or `tests.sh` names.
  - Updated script references in `.github/workflows/code-checks.yaml` and `README.md`.
- ff-665 Added Donna polish workflow for backend/frontend checks and runtime validation.
  - Added `project:work:polish` artifact with ordered run/fix stages.
  - Used direct utility commands via `./bin/backend-utils.sh` and `./bin/frontend-utils.sh` instead of aggregated `./bin/*.sh` scripts.
  - Implemented stages for backend formatting, frontend formatting, backend semantics, frontend semantics, and runtime checks.
- ff-665 Added backend and frontend spellcheck to Donna polish workflow using `codespell`.
  - Added dedicated backend/frontend spellcheck run and fix steps to `project:work:polish`.
  - Installed `codespell` for backend and frontend utility containers.
  - Scoped spellcheck commands to project code paths and fixed spelling issues in backend/frontend source comments.
