---
title: poly start
description: Reference for the `poly start` command.
---

# `poly start`

End-to-end onboarding for **self-serve** accounts on [studio.poly.ai](https://studio.poly.ai). `poly start` is hardcoded to the `studio` region — for any other region, use [`poly login`](./login.md).

`poly start`:

1. Opens a browser window so you can sign up or sign in to a self-serve workspace.
2. Generates an API key (or reuses your existing one) and writes it to `~/.poly/credentials.json` under the `studio` region.
3. Optionally creates a new Agent Studio project and pulls it down locally.


Examples:

~~~bash
poly start
poly start --base-path /path/to/projects
~~~

| Flag | Description |
|---|---|
| `--base-path` | Base path to initialize the project in. Defaults to the current working directory. |
