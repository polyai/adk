---
title: poly secrets
description: Reference for the `poly secrets` command.
---

# `poly secrets`

Manage account secrets. `poly secrets` requires a subcommand. Replace `<secret_name>` with the secret's display name, omitting the angle brackets.

Examples:

```bash
poly secrets list
poly secrets set <secret_name>
poly secrets delete <secret_name> --yes
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
      "display_name": "<secret_name>",
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
poly secrets set <secret_name>
poly secrets set <secret_name> --key-value
poly secrets set <secret_name> --delete-key obsolete
poly secrets set <secret_name> --description 'Service authentication'
poly secrets set <secret_name> --grant project-b --revoke project-a
poly secrets set <secret_name> --no-projects
poly secrets set <secret_name> --description 'Updated' --replace-value
poly secrets set <secret_name> --json < /secure/path/token
poly secrets set <secret_name> --key-value --json < /secure/path/credentials.json
```

Values come from hidden prompts or stdin, never a command argument. Interactive key-value input prompts separately for each key and hides each value. A single value read from stdin is used verbatim, including any trailing newline. Key-value stdin must contain a nonempty JSON object: strings add or update keys, and `null` deletes a key from an existing secret. New secrets require string values for every key.

Updates to an existing key-value secret change only the supplied keys. Omitted keys keep their stored values without being read. For example, input `{"password":"new-value"}` updates only `password`; `{"obsolete":null}` removes only `obsolete`. Alternatively, use repeatable `--delete-key` to remove keys without supplying a value. A secret must retain at least one key.

When changing only description or project access, the stored value is preserved without requesting it. Use `--replace-value` to also enter a single value or key updates interactively, or pipe them on stdin. An existing secret's type cannot be changed.

| Argument | Description |
|---|---|
| `<secret_name>` | The secret's display name. |

| Flag | Description |
|---|---|
| `--description TEXT` | Set or clear the description. |
| `--key-value` | Create a key-value secret instead of a single-value secret. |
| `--project PROJECT_ID` | Replace project access; repeat for multiple projects. |
| `--no-projects` | Give no projects access. Mutually exclusive with `--project`. |
| `--grant PROJECT_ID` | Add a project to an existing secret's access; repeat as needed. |
| `--revoke PROJECT_ID` | Remove a project from an existing secret's access; repeat as needed. |
| `--replace-value` | Also prompt for a value or key updates when changing metadata. |
| `--delete-key KEY` | Delete a key from an existing key-value secret; repeat for multiple keys. |

!!! warning "Account changes include live"
    Changes affect every environment for projects with access to the secret, including key updates and deletions.

!!! info "JSON mode does not prompt"
    When setting a value with `--json`, provide it on stdin; a terminal input is rejected. Metadata-only updates and `--delete-key` need no value. Project replacement (`--project` or `--no-projects`) cannot be combined with `--grant` or `--revoke`. A key supplied on stdin cannot also be named with `--delete-key`.

`--json` output shape:

```json
{
  "success": true,
  "secret": {
    "display_name": "<secret_name>",
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
poly secrets delete <secret_name>
poly secrets delete <secret_name> <another_secret_name> --yes
poly secrets delete <secret_name> --json
```

| Argument | Description |
|---|---|
| `<secret_name>` | One or more secret display names. |

| Flag | Description |
|---|---|
| `--yes` | Skip confirmation. |

!!! warning "Deletion affects every environment"
    Deleting an account secret removes it for every project with access, including live.

`--json` output shape:

```json
{
  "success": true,
  "deleted": ["<secret_name>"]
}
```
