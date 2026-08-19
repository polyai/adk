---
title: poly studio
description: Reference for the `poly studio` command.
---

# `poly studio`

Open the current project in the Agent Studio web application using your default browser. Opens the project at the branch currently checked out in the ADK.

Examples:

~~~bash
poly studio
poly studio --path /path/to/project
~~~

Useful for jumping from the terminal to the UI to review a branch, check a deployment, or look at analytics.

`--json` output shape:

~~~json
{
  "url": "https://studio.example.com/home?branchId=my-branch"
}
~~~
