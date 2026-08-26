---
title: Context documents
description: Markdown files in context/ that carry background knowledge about the project for Studio Assistant, without affecting agent runtime.
---

# Context documents

<p class="lead">
Context documents are Markdown files that hold background knowledge about the project — how it is structured, why decisions were made, what "done" looks like for a piece of work.
</p>

**They do not affect agent runtime.** Nothing in a context document reaches a caller. They serve two purposes: documenting the project for the people working on it, and giving PolyAI's **Studio Assistant** a place to read ongoing project context.

## Location

Documents live in `context/`, at the top level of the project. Only `.md` files are discovered, and nesting is not supported — the directory is read one level deep.

~~~text
<account>/<project>/
└── context/
    ├── CONTEXT.MD
    ├── FUNCTION_GUIDELINES.md
    └── SUCCESS_CRITERIA.md
~~~

!!! warning "`CONTEXT.MD` must use exact uppercase"

    The platform treats `CONTEXT.MD` as a special file and requires that exact casing. A file whose name matches `context.md` case-insensitively but is not exactly `CONTEXT.MD` will fail validation. All other document filenames preserve whatever case you give them.

## Contents

The body is plain Markdown, passed through unchanged in both directions. Two consequences:

- **Resource references are not resolved.** `{{fn:}}`, `{{attr:}}`, and the other reference prefixes are inert here — they stay as literal text rather than resolving to a resource.
- **There is no schema and no validation.** `poly validate` has nothing to check, so a context document cannot fail a push on its own content.

## Syncing

Documents follow the standard lifecycle — `poly pull`, `poly status`, `poly diff`, and `poly push` all treat them as ordinary resources, and the document's path is its identity on the platform.

## Related pages

- [Tests](./tests.md) — the other non-runtime resource type
- [Working locally](../../development/working-locally.md) — where `context/` sits in the project structure
- [Resource architecture](../../development/resource-architecture.md#resource-references) — the full `{{prefix:name}}` reference table, inert here but live everywhere else
- [`poly docs`](../cli/docs.md) — output this reference from the CLI with `poly docs context`
