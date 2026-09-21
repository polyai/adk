---
title: poly completion
description: Reference for the `poly completion` command.
---

# `poly completion`

Output a shell completion script for `poly`. Supported shells are `bash`, `zsh`, and `fish`.

Examples:

~~~bash
poly completion bash
poly completion zsh
poly completion fish
~~~

| Argument | Description |
|---|---|
| `shell` | Shell type to generate completions for. One of `bash`, `zsh`, `fish`. Required. |

Add the output to your shell configuration to enable tab completion.

=== "Bash"

    ~~~bash
    eval "$(poly completion bash)"
    # or: poly completion bash >> ~/.bash_completion
    ~~~

=== "Zsh"

    ~~~bash
    eval "$(poly completion zsh)"
    # or: poly completion zsh > ~/.zsh/completions/_poly
    ~~~

=== "Fish"

    ~~~bash
    poly completion fish | source
    # or: poly completion fish > ~/.config/fish/completions/poly.fish
    ~~~
