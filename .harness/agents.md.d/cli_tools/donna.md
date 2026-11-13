
### `donna`

Use Donna to run project-local deterministic workflows.

Run Donna workflows only when explicitly instructed to do so by the developer or by the project instructions.
Do not run workflows on your own initiative.

When you run Donna workflows: Donna controls workflow state and execution flow, you follow the instructions provided by Donna.

Run `donna -p llm skill usage` when:

- You run a workflow first time in the session.
- You need to create a new workflow or modify an existing workflow.
- You need to perform an operation that is not covered by instructions.

Run `donna -p llm new-session` when the developer explicitly instructs you to start a new **Donna** session.

Special instructions:

- Use donna polish workflow to groom the code after you've introduced changes (instead of running linters, formatters and while tests manually).

Here is a list of available workflows.

<!-- [[[cog
import json
import shlex
import subprocess

import cog

result = subprocess.run(
    ["donna", "-p", "automation", "list"],
    check=True,
    capture_output=True,
    text=True,
)
for line in result.stdout.splitlines():
    workflow = json.loads(line)
    if workflow.get("artifact_kind") != "donna.lib.workflow":
        continue
    command = shlex.join(["donna", "-p", "llm", "run", workflow["artifact_id"]])
    cog.outl(f"#### {workflow['artifact_title']}")
    cog.outl()
    cog.outl(f"Run `{command}` to execute the workflow.")
    cog.outl()
    cog.outl(workflow["content"])
    cog.outl()
]]] -->
<!-- [[[end]]] -->
