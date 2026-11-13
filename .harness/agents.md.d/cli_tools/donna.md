
### `donna`

Use Donna to run project-local deterministic workflows when the developer, these instructions, or an active Donna workflow explicitly asks for one.

Donna controls workflow state only. Agents remain responsible for reading project instructions, using `depmesh` where applicable, editing files, running checks, and reporting results.

You may need to read the usage intructions for `donna -p llm skill usage` in these cases:

- You need to run a workflow first time in the session.
- You need to list available workflows first time in the session.

Use Donna's `llm` protocol for agent-facing commands unless a human explicitly asks for another protocol:

Depmesh is configured to log significant operation steps via `task` tool.

At the start of working session run `donna -p llm list` to list all available workflows.

Do not run `donna -p llm new-session` unless the developer explicitly asks to reset or start a fresh Donna session.

Special instructions:

- Use donna polish workflow to groom the code after you've introduced changes (instead of running linters, formatters and while tests manually).

Run Donna workflows only when explicitly instructed to do so by the developer or by the project instructions.
Do not run workflows on your own initiative.

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
