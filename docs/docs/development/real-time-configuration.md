---
title: Real-time configuration
description: Manage per-environment Real-Time Configuration with poly rtc, including drift protection and merge behavior.
---

# Real-time configuration

Real-Time Configuration (RTC) is per-environment configuration that takes effect without a deployment. Each environment holds a **schema**, which defines the shape of the configuration, and **data**, which holds the values.

RTC sits outside the branch workflow. It is not branched, not versioned alongside your resources, and not promoted through the deployment ladder — you pull and push it per environment.

!!! warning "`poly rtc push --env live` writes directly to production"

    There is no branch, review, or promotion step. A push to `live` takes effect immediately. Push to `sandbox` first and verify there.

## Local layout

RTC files live outside the resource tree, one directory per environment:

~~~text
real_time_configuration/
├── draft_and_sandbox/     # the sandbox environment
│   ├── schema.json
│   └── data.json
├── pre_release/
│   ├── schema.json
│   └── data.json
└── live/
    ├── schema.json
    └── data.json
~~~

Note that the `sandbox` environment maps to the `draft_and_sandbox/` directory.

## Working with RTC

The cycle mirrors the resource workflow, minus the branching:

~~~bash
poly rtc pull                  # bring down the current state
poly rtc diff                  # compare local against remote
poly rtc validate              # check the data against its schema
poly rtc push --env sandbox    # send it back
~~~

`poly rtc pull` covers every environment by default. `poly rtc push` always requires an explicit environment, so you cannot push to the wrong one by omission. Both can operate on just the schema or just the data when you only need to change one.

`poly rtc edit` does the whole cycle in one step — it pulls, opens the configuration in your editor, validates what you wrote, and pushes it back.

Because RTC is per environment, changing a value everywhere means pushing to each environment. There is no promotion between them.

## Drift protection

Each pull records the remote timestamp along with a base copy of the schema and data. On push, the ADK compares that base against the current remote state, and if the remote has moved on since your last pull, the configuration has **drifted** — usually because someone changed it in the Agent Studio UI.

By default drift is merged rather than rejected. RTC merges **per key**, unlike resource files which merge per line: a key changed on only one side is applied cleanly, and only a key changed differently on both sides is a conflict. You can ask for a hard failure instead, or force your version to win.

!!! info "Drift protection needs a prior pull"

    Base copies only come from `poly rtc pull`. Push without ever having pulled and there is nothing to merge against, so the check is skipped — the ADK tells you to pull to enable it. Pulling first is the habit that makes drift protection work at all.

Every flag for these commands is in the [CLI reference](../reference/cli.md).
