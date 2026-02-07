# Log Changes Workflow

```toml donna
kind = "donna.lib.workflow"
start_operation_id = "determine_scope"
```

Log new unreleased changes in the Changy-managed changelog.

## Determine change scope

```toml donna
id = "determine_scope"
kind = "donna.lib.request_action"
```

1. If this workflow was started by a parent workflow and it provided a specific scope, analyze changes only in that scope.
2. If this workflow was started directly by a developer with no additional scope, analyze all changes in the current branch.
3. If you are analyzing full branch changes, `{{ donna.lib.goto("analyze_full_branch_changes") }}`.
4. If you are analyzing a scoped set of changes, `{{ donna.lib.goto("analyze_scoped_changes") }}`.

## Analyze full branch changes

```toml donna
id = "analyze_full_branch_changes"
kind = "donna.lib.request_action"
```

1. Determine the base branch (typically `main`) and compare against it to identify changes introduced by this branch.
2. Collect the change summary using git commands such as:
   - `git status -sb`
   - `git diff --stat main...HEAD`
   - `git log --oneline --decorate main..HEAD`
3. Summarize the main changes across the entire branch to use for the changelog entry.
4. `{{ donna.lib.goto("analyze_branch_name") }}`

## Analyze scoped changes

```toml donna
id = "analyze_scoped_changes"
kind = "donna.lib.request_action"
```

1. Focus on changes in the `session:` world artifacts provided by the parent workflow.
2. Summarize the main changes within that scoped set to use for the changelog entry.
3. Only after the scoped analysis, check the git state to confirm the summary reflects the current working tree.
4. `{{ donna.lib.goto("analyze_branch_name") }}`

## Analyze branch name

```toml donna
id = "analyze_branch_name"
kind = "donna.lib.request_action"
```

1. Determine the current branch name with `git rev-parse --abbrev-ref HEAD`.
2. Extract task id and short description from the branch name:
   - Task id: first token matching `<letters>-<digits>` (examples: `abc-123`, `xyz-456`).
   - Short description: the remainder of the branch name after the task id, with `-` converted to spaces (examples: `new api`, `fix crash`).
3. If no meaningful branch description exists, derive a concise description from the change summary.
4. `{{ donna.lib.goto("locate_unreleased_file") }}`

## Locate unreleased changes file

```toml donna
id = "locate_unreleased_file"
kind = "donna.lib.request_action"
```

1. Locate the Changy unreleased changes file (typically `changes/unreleased.md`).
2. If unsure, search with `rg --files -g 'unreleased.md' changes` or `find changes -name 'unreleased.md'`.
3. `{{ donna.lib.goto("update_changes_section") }}`

## Update changes section

```toml donna
id = "update_changes_section"
kind = "donna.lib.request_action"
```

1. Add a new entry under the `### Changes` section (create the section if missing).
2. Format the main entry:
   - With task id: `- <short-id> <short-changes-description>`
   - Without task id: `- <short-changes-description>`
3. Add sub-items for all major changes in behavior, architecture, or code.
4. `{{ donna.lib.goto("update_breaking_changes_section") }}`

Notes:

- Use past tense (`Added …`, `Fixed …`, etc.)
- Be concise.

## Update breaking changes section

```toml donna
id = "update_breaking_changes_section"
kind = "donna.lib.request_action"
```

1. If there are breaking changes, add or update the `### Breaking Changes` section with the relevant entries.
2. If there are no breaking changes, do not add the section.
3. `{{ donna.lib.goto("update_migration_section") }}`

Notes:

- Use past tense (`Added …`, `Fixed …`) or present tense (`X is now …`).
- Be concise.

## Update migration section

```toml donna
id = "update_migration_section"
kind = "donna.lib.request_action"
```

1. If migrations are needed, add or update the `### Migration` section with the relevant entries.
2. If no migrations are needed, do not add the section.
3. `{{ donna.lib.goto("update_deprecations_section") }}`

Notes:

- Use past tense (`Added …`, `Fixed …`) or present tense (`X is now …`).
- Be concise.

## Update deprecations section

```toml donna
id = "update_deprecations_section"
kind = "donna.lib.request_action"
```

1. If deprecations are introduced, add or update the `### Deprecations` section with the relevant entries.
2. If no deprecations are introduced, do not add the section.
3. `{{ donna.lib.goto("update_removals_section") }}`

Notes:

- Use past tense (`Added …`, `Fixed …`) or present tense (`X is now …`).
- Be concise.

## Update removals section

```toml donna
id = "update_removals_section"
kind = "donna.lib.request_action"
```

1. If functionality removals occur, add or update the `### Removals` section with the relevant entries.
2. If no removals occur, do not add the section.
3. `{{ donna.lib.goto("validate_changelog") }}`

Notes:

- Use past tense (`Added …`, `Fixed …`) or present tense (`X is now …`).
- Be concise.

## Validate changelog

```toml donna
id = "validate_changelog"
kind = "donna.lib.request_action"
```

1. Ensure the changelog remains well-structured and readable.
2. Confirm the updated sections are in the expected order and formatting.
3. `{{ donna.lib.goto("finish") }}`

## Finish

```toml donna
id = "finish"
kind = "donna.lib.finish"
```

Log changes workflow completed.
