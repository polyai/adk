---
title: Build an agent with the ADK
description: Go from a blank Agent Studio project to a production-ready voice agent using the PolyAI ADK and a coding tool such as Claude Code.
---

# Build an agent with the ADK

This guide walks through how to go from a blank slate to a production-ready voice agent with a real backend using **PolyAI ADK**, **Agent Studio**, and a coding tool such as **Claude Code**.

The intended workflow is simple:

<div class="grid cards" markdown>

-   **You provide context**

    ---

    Gather the project requirements, business rules, API information, and reference material.

-   **The coding tool builds**

    ---

    Using the ADK, the coding tool generates the project files.

-   **Agent Studio hosts and deploys**

    ---

    The generated work is pushed into Agent Studio, where it can be reviewed, merged, and deployed.

</div>

!!! info "No manual flow-building required"

    In this workflow, the coding tool generates the project files. Agent Studio is where the output is reviewed, tested, and deployed.

## Architecture at a glance

| Role | Responsibility |
|---|---|
| **You** | Provide requirements, context, and business rules |
| **Claude Code + ADK** | Generate project files and push changes |
| **Agent Studio** | Host, preview, review, and deploy the agent |

## Step 1 — Gather requirements

Collect the project context from your team's communication channels before you begin.

Include anything needed to produce a working agent:

- API endpoint URLs
- business rules
- use-case descriptions
- emails or internal notes
- reference material
- links to relevant documentation

The more complete and structured your input, the less correction the output requires.

!!! tip "Front-load the context"

    Gather everything up front. Providing context piecemeal produces piecemeal output.

## Step 2 — Create a new project in Agent Studio

Open **Agent Studio** and create a brand-new project.

The project starts empty:

- no knowledge base
- no flows
- no configuration

That blank starting point is intentional. The coding tool populates the project in later steps.

!!! note "Think of Agent Studio as the deployment target"

    Agent Studio is where the project lives, but the coding tool generates the actual content.

## Step 3 — Start the coding tool via the CLI

Open your terminal and start your coding tool.

At this stage:

- the ADK must already be installed
- the new Agent Studio project must already exist
- the coding tool should initialize and link the project using the ADK

~~~bash
poly init --region <region> --account_id <account_id> --project_id <project_id>
poly pull
~~~

The ADK acts as the bridge between your local environment and Agent Studio. It lets the coding tool read from and write back to the project.

## Step 4 — Give the coding tool its context

Provide the coding tool with the information you gathered earlier.

Include:

- the project-specific requirements
- the URL to the business's public API documentation
- any relevant internal project context
- best practices or patterns from previous projects

Use the docs command to generate a reference file the coding tool can read:

~~~bash
poly docs --all
~~~

Including patterns from earlier projects reduces correction time and improves consistency.

## Step 5 — Generate the project files

Once the context is in place, the coding tool generates the project files.

This produces the assets the agent needs, including:

<div class="grid cards" markdown>

-   **Conversation flows**

    ---

    Dialogue logic and routing.

-   **Callable functions**

    ---

    Backend functions used during calls.

-   **Knowledge base entries**

    ---

    Information the agent can retrieve when answering questions.

-   **API integrations**

    ---

    Both real API connections and mock endpoints for testing.

</div>

The generated files follow ADK structure and are ready to push to Agent Studio.

## Step 6 — Push to Agent Studio

Once the files are generated, use the ADK to push them to Agent Studio.

A new branch is created so the generated work can be reviewed safely before anything goes live.

When you switch to that branch in Agent Studio, you should see the generated changes, such as:

- updated greeting messages
- new knowledge base entries
- a built tracking flow
- real and mock API integrations

!!! tip "Use the branch review step"

    The branch-based workflow makes it possible to inspect what was generated before merging it into the main project.

## Step 7 — Review, merge, and deploy

Review the generated work inside Agent Studio.

Check the key parts of the agent:

- flows
- functions
- knowledge base entries
- API integrations

Once everything looks right:

1. merge the branch into the main project
2. deploy the project

At that point, the agent is live.

## The overall loop

1. provide context
2. generate the project files using the coding tool
3. push to Agent Studio with the ADK
4. review, merge, and deploy

## Next steps

<div class="grid cards" markdown>

-   **Watch the walkthrough**

    ---

    See the workflow demonstrated in video form.
    [Open the walkthrough video](../get-started/walkthrough-video.md)

</div>
