---
title: poly secrets
description: Reference for the `poly secrets` command.
---

# `poly secrets`

Manage secrets stored in the current project's account without revealing their values. `poly secrets` requires a subcommand.

Examples:

```bash
poly secrets list
poly secrets set service-token
poly secrets delete service-token --yes
```

These commands update account secrets directly, across branches and environments including live. They do not write values to project files or require `poly push`.

## `poly secrets list`

List each secret's name, description, type, project access, creation time, and last update. Stored values are never shown.

Examples:

```bash
poly secrets list
poly secrets list --project --json
```

| Flag | Description |
|---|---|
| `--project` | Only list secrets the current project can use. |

`--json` output shape:

```json
{
  "success": true,
  "secrets": [
    {
      "display_name": "service-token",
      "description": "Service authentication",
      "value_type": "single",
      "access_config": ["project-a"],
      "created_at": "2026-01-01T00:00:00Z",
      "last_updated": "2026-01-02T00:00:00Z"
    }
  ]
}
```

## `poly secrets set`

Create a secret or update an existing one. A new secret is single-value by default and grants access to the current project. Updates preserve the existing type, description, and access unless explicitly changed.

Examples:

```bash
poly secrets set service-token
poly secrets set credentials --key-value
poly secrets set service-token --description 'Service authentication'
poly secrets set service-token --grant project-b --revoke project-a
poly secrets set service-token --no-projects
poly secrets set service-token --description 'Updated' --replace-value
poly secrets set service-token --json < /secure/path/token
poly secrets set credentials --key-value --json < /secure/path/credentials.json
```

Values come from hidden prompts or stdin, never a command argument. Interactive key-value input prompts separately for each key and hides each value. A single value read from stdin is used verbatim, including any trailing newline. Key-value stdin must contain a nonempty JSON object whose values are strings.

When changing only description or project access, the stored value is preserved without requesting it. Use `--replace-value` to also enter a replacement interactively, or pipe the replacement on stdin. An existing secret's type cannot be changed.

| Argument | Description |
|---|---|
| `name` | The secret's display name. |

| Flag | Description |
|---|---|
| `--description TEXT` | Set or clear the description. |
| `--key-value` | Create a key-value secret instead of a single-value secret. |
| `--project ID` | Replace project access; repeat for multiple projects. |
| `--no-projects` | Give no projects access. Mutually exclusive with `--project`. |
| `--grant ID` | Add a project to an existing secret's access; repeat as needed. |
| `--revoke ID` | Remove a project from an existing secret's access; repeat as needed. |
| `--replace-value` | Also prompt for a replacement value when changing metadata. |

!!! warning "Account changes include live"
    Changes affect every environment for projects with access to the secret. Replacing a key-value secret replaces the **complete map**: omitted keys are removed. Enter every key you want to keep.

!!! info "JSON mode does not prompt"
    When setting a value with `--json`, provide it on stdin; a terminal input is rejected. Metadata-only updates need no value. Project replacement (`--project` or `--no-projects`) cannot be combined with `--grant` or `--revoke`.

`--json` output shape:

```json
{
  "success": true,
  "secret": {
    "display_name": "service-token",
    "description": "Service authentication",
    "value_type": "single",
    "access_config": ["project-a"]
  }
}
```

## `poly secrets delete`

Delete one or more secrets from the account. Interactive deletion asks for confirmation; `--json` skips confirmation.

Examples:

```bash
poly secrets delete service-token
poly secrets delete service-token credentials --yes
poly secrets delete service-token --json
```

| Argument | Description |
|---|---|
| `names` | One or more secret display names. |

| Flag | Description |
|---|---|
| `--yes` | Skip confirmation. |

!!! warning "Deletion affects every environment"
    Deleting an account secret removes it for every project with access, including live.

`--json` output shape:

```json
{
  "success": true,
  "deleted": ["service-token"]
}
```
