---
title: Build an agent with the ADK
description: Go from a blank Agent Studio project to a production-ready voice agent using the PolyAI ADK and an AI coding agent.
---

# Build an agent with the ADK

This guide walks through how to go from a blank slate to a production-ready voice agent with a real backend using **PolyAI ADK**, **Agent Studio**, and a coding agent such as **Claude Code**.

The intended workflow is simple:

<div class="grid cards" markdown>

-   **You provide context**

    ---

    Gather the project requirements, business rules, API information, and reference material.

-   **The coding agent builds**

    ---

    Using the ADK, the coding agent generates the files needed for the agent.

-   **Agent Studio hosts and deploys**

    ---

    The generated work is pushed back into Agent Studio, where it can be reviewed, merged, and deployed.

</div>

!!! info "No manual flow-building required"

    This workflow is designed so that the coding agent does the heavy lifting of building the agent, while Agent Studio remains the place where the finished work is reviewed, tested, and deployed.

## Architecture at a glance

| Role | Responsibility |
|---|---|
| **You** | Provide requirements, context, and business rules |
| **Claude Code + ADK** | Generate project files and push changes |
| **Agent Studio** | Host, preview, review, and deploy the agent |

## Step 1 — Gather requirements

Collect the project context from your team’s communication channels before you begin.

This should include anything the coding agent will need to produce a working agent, such as:

- API endpoint URLs
- business rules
- use-case descriptions
- emails or internal notes
- reference material
- links to relevant documentation

The more complete and structured the input is, the better the coding agent’s output will be.

!!! tip "Front-load the context"

    This workflow works best when you gather the requirements up front rather than feeding them in piecemeal later.

## Step 2 — Create a new project in Agent Studio

Open **Agent Studio** and create a brand-new project.

The project starts empty:

- no knowledge base
- no flows
- no configuration

That blank starting point is intentional. The coding agent will populate the project in later steps.

!!! note "Think of Agent Studio as the deployment target"

    Agent Studio is where the project lives, but the coding agent does most of the actual building work.

## Step 3 — Launch the coding agent via the CLI

Open your command line interface and launch your coding agent.

At this stage:

- the ADK must already be installed
- the new Agent Studio project should already exist
- the coding agent should be linked to the project using the ADK

The ADK acts as the bridge between your local development environment and Agent Studio in the cloud. It allows the coding agent to read from and write back to the project.

## Step 4 — Feed context to the coding agent

Now provide the coding agent with the information you gathered earlier.

This is the core input step. Include:

- the project-specific requirements
- the URL to the business’s public API documentation
- any relevant internal project context
- best practices or patterns from previous projects

Reusing proven patterns from earlier projects can improve both speed and output quality.

## Step 5 — Let the agent build

Once the context has been provided, let the coding agent generate the project files.

The coding agent can produce the assets needed for the agent, including:

<div class="grid cards" markdown>

-   **Conversation flows**

    ---

    Dialogue logic and routing for the agent.

-   **Callable functions**

    ---

    Backend functions used during calls.

-   **Knowledge base entries**

    ---

    Information the agent can reference when answering questions.

-   **API integrations**

    ---

    Both real API connections and mock endpoints for testing.

</div>

The generated assets are structured for Agent Studio and prepared to be pushed back to the platform.

## Step 6 — Push back to Agent Studio

Once the coding agent has generated the project files, it uses the ADK to push them back into Agent Studio.

A new branch is created in the project so the generated work can be reviewed safely before anything goes live.

When you switch to that branch in Agent Studio, you should see the generated changes, such as:

- updated greeting messages
- new knowledge base entries
- a built tracking flow
- real and mock API integrations

!!! tip "Use the branch review step"

    The branch-based workflow makes it possible to inspect what was generated before merging it into the main project.

## Step 7 — Review, merge, and deploy

Review the generated work inside Agent Studio.

Check that the key parts of the agent look correct:

- flows
- functions
- knowledge base entries
- API integrations

Once everything looks right:

1. merge the branch into the main project
2. deploy the project

At that point, the agent is live.

## Summary

| Metric | Value |
|---|---|
| **Steps** | 7 |
| **Total time** | ~30 minutes |
| **Manual flows built** | 0 |

The overall loop is straightforward:

1. provide context
2. let the coding agent generate the project assets
3. use the ADK to push them into Agent Studio
4. review, merge, and deploy

By reusing patterns from previous projects, the coding agent can produce production-grade output much faster than a fully manual workflow.

## Next steps

<div class="grid cards" markdown>

-   **Watch the walkthrough**

    ---

    See the workflow demonstrated in video form.
    [Open the walkthrough video](../get-started/walkthrough-video.md)

</div>
