# Resource reference page structure

Every page in this directory documents one high level ADK resource. Follow this shape exactly so pages stay interchangeable and can be regenerated or extended without re-deriving the format each time.

## Page skeleton

```
---
title: <Resource name>
description: One sentence — what the resource does and where it lives.
---

# <Resource name>

<p class="lead">
One or two sentences: what this resource is for, in plain terms.
</p>

<Optional !!! note/warning if the resource has a platform quirk worth knowing
before you touch it — e.g. platform-provisioned files, uppercased filenames.>

## Location

<Where it lives on disk — a file path or a `text` tree. State whether the
file/directory is optional. If the resource isn't file-based (e.g. Variables,
which are set in code, not a file), rename this section to fit — "How
variables work" — but keep it as the second section on the page.>

~~~text
config/entities.yaml
~~~

## What a/an <resource> contains|controls|is for

<The overview. Use grid cards when there are several sub-parts to introduce
(e.g. agent settings has personality/role/rules); use plain prose when there's
only one shape.>

### Fields

| Field | Description |
|---|---|
| `field_name` | ... |

Add a `Required` column only when some fields are optional and that matters:

| Field | Required | Description |
|---|---|---|

### Example

~~~yaml
field_name: value
~~~

## Validation

<Every constraint `poly validate`/`poly push` actually enforces, as a bullet
list — required fields, allowed values, cross-field rules, uniqueness
constraints. One rule is still a `## Validation` section, not an inline note
next to the field.>

## Best practices

- <short, imperative bullets>

## Related pages

<div class="grid cards" markdown>

-   **Sibling resource**

    ---

    One sentence on how it relates.
    [Open sibling resource](./sibling.md)

</div>
```

Include every section from the skeleton that applies; skip `Validation` or `Best practices` if there's genuinely nothing to say — don't pad them out.

## The overview section's heading

Right after `## Location` comes one overview section, and its wording depends on the resource's nature — match what's already established per resource, don't reinvent it:

- **"What a/an `<resource>` contains"** — data-shaped resources (a topic, an entity, a test case, an SMS template, a handoff, a translation)
- **"What `<resource>` controls"** — settings that shape behavior (chat settings, safety filters, response control, speech recognition, voice settings)
- **"What `<resource>` are/is for"** — process or capability resources (flows, functions)

Pick the one that reads naturally; the point is consistency of *shape*, not the literal words.

## Reference syntax

If a field accepts `{{prefix:name}}`-style references to other resources, always link each prefix to the resource page it resolves to — never leave `{{attr:...}}` or `{{vrbl:...}}` as a bare code span with no link.

For a field that supports several prefixes (`rules.txt`, topic `actions` — the free-text fields that accept the full reference vocabulary), use a table:

| Syntax | Meaning |
|---|---|
| `{{fn:function_name}}` | [Global function](./functions.md) |

For a field that supports only one or two, a table is overkill — link inline in the field's own description instead: "Supports [`{{attr:...}}`](./variants.md) and [`{{vrbl:...}}`](./variables.md) references." Don't add a table just to hold one or two rows.

A prefix that refers to the resource *on the page you're writing* (e.g. `{{ho:handoff_name}}` on `handoffs.md`) doesn't need a link — it's self-referential.

## Admonitions

- `!!! note` — platform-managed quirks: resources that are provisioned automatically, can only be updated (not created) via the ADK, or otherwise behave differently from a normal file.
- `!!! warning` — data-loss or surprising-overwrite behavior (filenames get uppercased, a field gets reassigned on push).
- `!!! info` — an edge case worth flagging that doesn't rise to a warning (e.g. non-standard values that silently pass validation).
- `!!! tip` — a best-practice nudge that's more useful inline than buried in the `Best practices` list.

Every admonition gets a quoted title — `!!! warning "Filenames are uppercased"` — never a bare `!!! warning` with nothing after it.

## Cross-links

Link to sibling resource pages with relative paths (`./functions.md`), to CLI pages with `../cli/<command>.md`, and to platform docs with the full external URL plus `{ target="_blank" rel="noopener" }`.

Links to a `development/` concept page are different — never inline. Collect them in `## Related pages` at the bottom instead, alongside the sibling-resource cards.

`## Related pages` uses the grid-cards format (see skeleton) — this is the established pattern across the directory. Reserve a plain bullet list only for a page with two or three links and no room-for-cards content to write (e.g. a non-runtime resource page).

## Non-runtime resources

`tests.md` and `context.md` document resources that sync like any other file but never affect what the agent does on a call. Say that explicitly, early — right after the lead paragraph — so it isn't assumed to be a runtime resource by default.

## Don't document the sync process per resource

Permission-gated visibility — a user without read access to a resource in Agent Studio won't see it locally — is a property of the sync process itself, not something specific to any one resource. It applies (or will apply) across the whole `resources/` directory, not just the page you're writing.

Don't add a per-page note about it. That belongs at a high level in [resource architecture](../../development/resource-architecture.md) and gets a brief mention on the [resources overview](../resources.md) — not repeated on every page it could theoretically affect.
