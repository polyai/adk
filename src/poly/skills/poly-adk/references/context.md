# Context

## Overview
Background/documentation markdown files under `context/`, providing project knowledge. These do **not** affect
runtime behavior of the agent — they're documentation only, and are also surfaced to Poly's Studio Assistant as a
place for ongoing project context.

## File structure
Only `*.md` files are discovered, read from the `context/` folder:
```
<account>/<project>/
  context/
    CONTEXT.md
    FUNCTION_GUIDELINES.md
    SUCCESS_CRITERIA.md
```

Use this for anything a human or the Studio Assistant needs to know about the project that shouldn't live inside
a runtime resource (flows, topics, rules) — e.g. why a design decision was made, non-obvious constraints, or
success criteria for the build.
