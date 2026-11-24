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

Secret operations require an HTTP 2xx response. If the API redirects a request, the command exits with an error and reports the HTTP status.

## `poly secrets list`

List each secret's name, description, type, project access, creation time, and last update. Visible projects are shown by name and ID. If a project name is unavailable, the list shows its stored ID. JSON output uses project IDs. Stored values are never shown.

Examples:

```bash
poly secrets list
poly secrets list --current-project --json
```

| Flag | Description |
|---|---|
| `--current-project` | Only list secrets the current project can use. |

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
poly secrets set
poly secrets set <secret_name>
poly secrets set <secret_name> --type key-value
poly secrets set <secret_name> --type single
poly secrets set <secret_name> --delete-key obsolete
poly secrets set <secret_name> --description 'Service authentication'
poly secrets set <secret_name> --grant project-b --revoke project-a
poly secrets set <secret_name> --no-projects
poly secrets set <secret_name> --description 'Updated' --replace-value
poly secrets set <secret_name> --yes < /secure/path/token
poly secrets set <secret_name> --json < /secure/path/token
poly secrets set <secret_name> --type key-value --json < /secure/path/credentials.json
```

In a terminal, run `poly secrets set` to pick an existing secret or choose **New secret…**. Supplying the name skips the picker. For a new secret, choose the type, enter an optional description, and select the projects that can use it. The current project starts checked. Flags supply these choices directly. Once you choose a name, the CLI checks the supplied flags before asking for any remaining fields or reading the value from stdin.

For an existing secret, select **Value or type** to edit the current value or convert the secret to the other type. Conversion requires a complete replacement value. You can also select **Description** and **Project access** in the same save. Edit flags go straight to the requested changes. The key editor shows existing key names and lets you update a value, add a key, or select keys to delete. Choose **Done** to review the changes.

At the description prompt, press Enter to keep the current text or clear the text to remove it. If you keep the description and make no other edits, the command exits without a save prompt.

The save summary shows the secret name, type, key names added, updated or removed, and projects with access. When access changes, it shows the previous and new project lists. Confirm to apply the changes to every environment, including live. Press Enter at the confirmation to cancel. Scripts must supply a name and use `--yes` or `--json` when piping input.

Values come from hidden prompts or stdin, never a command argument. At the interactive value prompt, typing `null` stores it as text. For a single value on stdin, the CLI strips one trailing line ending (LF or CRLF). It preserves embedded newlines and surrounding spaces. To store a final newline, supply one extra newline on stdin.

To change type, use `--type single` or `--type key-value` and supply the complete replacement value, even when also changing the description or project access. For a conversion to key-value, enter every new key and its string value. Conversions reject `--delete-key` and JSON `null` entries.

For key-value input on stdin, pass a nonempty JSON object. A string value such as `{"status":"value"}` adds or updates the key. An unquoted JSON `null`, as in `{"obsolete":null}`, deletes a key when updating a secret that already has the key-value type. New secrets require string values for every key.

Updates to an existing key-value secret change only the supplied keys. Omitted keys keep their stored values without being read. To delete a key without piping JSON, use `--delete-key KEY`. Repeat the flag to delete multiple keys. A secret must retain at least one key.

When changing only description or project access, the stored value is preserved without requesting it. Use `--replace-value` to also enter a single value or key updates interactively, or pipe them on stdin.

For `--project`, `--grant`, and `--revoke`, run `poly project list` for the secret's account and use the **Agent ID** beside the project's name. You can also revoke an ID still on the secret's access list after its project has been deleted.

| Argument | Description |
|---|---|
| `<secret_name>` | Optional in a terminal. Supply the display name to skip the secret picker. |

| Flag | Description |
|---|---|
| `--yes` | Skip the live save confirmation. |
| `--description TEXT` | Set or clear the description. |
| `--type {single,key-value}` | Choose the type for a new secret or convert an existing secret with a complete replacement value. |
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

Delete one or more secrets from the account. Run `poly secrets delete` in a terminal to select secrets with a checkbox, or supply their names. Review the selected names and confirm deletion. For scripts, supply the names and use `--yes` or `--json`.

Examples:

```bash
poly secrets delete
poly secrets delete <secret_name>
poly secrets delete <secret_name> <another_secret_name> --yes
poly secrets delete <secret_name> --json
```

A successful response confirms that the delete request completed. Names that are already absent are accepted.

| Argument | Description |
|---|---|
| `<secret_name>` | Optional in a terminal. Supply one or more display names to skip the checkbox. |

| Flag | Description |
|---|---|
| `--yes` | Skip confirmation. |

!!! warning "Deletion affects every environment"
    Deleting an account secret removes it for every project with access, including live.

`--json` output shape:

```json
{
  "success": true
}
```
