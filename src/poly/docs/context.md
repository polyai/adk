# Context

## Overview

Project context can be provided via markdown files in the `context/` folder to provide background knowledge about the project. These do not affect the runtime of the Virtual Assistant and are used purely for documentation purposes. These are also used by Poly's Studio Assistant to provide a place for ongoing context. They are stored as Markdown files in the `context/` directory.

## File structure
These are read from the `context/` folder. Only `*.md` files are discovered.

```
<account>/<project>/
  context/
    CONTEXT.md
    FUNCTION_GUIDELINES.md
    SUCCESS_CRITERIA.md
```

## Validation

- The file name can contain only letters, digits, `_`, `-` and `.`. It cannot contain `..` or end with `.`, and is at most 512 characters long.
- A document's content is at most 262,144 bytes (256 KB) when encoded as UTF-8.
- A project has at most 50 context documents.
