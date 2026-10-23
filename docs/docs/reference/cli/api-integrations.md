---
title: poly api-integrations
description: Reference for the `poly api-integrations` command.
---

# `poly api-integrations`

Manage stored authentication credentials for [API integrations](../resources/api_integrations.md). `poly api-integrations` requires a subcommand.

## `poly api-integrations configure`

Configure credentials for an existing integration in one environment. Push its base URL and auth type first.

Examples:

~~~bash
poly api-integrations configure crm --env sandbox
your-secret-provider | poly api-integrations configure crm --env sandbox --stdin --json
~~~

Interactive mode loads saved credentials and displays defaults in brackets. Client IDs and secrets are masked; the saved token URL is shown in full. Press Enter to keep a saved required value, or enter a replacement. Required fields are prompted again when neither a new value nor a saved value exists. Newly typed values are visible, like `aws configure`. Credentials location is selected from `header` and `body` using the arrow keys; The saved scope is shown in full; Enter keeps it, and `-` clears it. With no saved scope, Enter skips it.

~~~text
Client ID [******ABC]:
Client Secret [******DEF]:
Token URL [https://example.com/oauth/token]:
Scope [read:contacts] (Enter to keep, - to clear):
? Credentials location: (Use arrow keys)
 » header
   body
~~~

The command uses `POLY_STUDIO_ACCESS_TOKEN` when set, otherwise it reuses the regional Studio session saved from a previous run. It prompts for sign-in only when there is no unexpired session. Sessions are stored in the user's private ADK session file and kept separate from API-key login sessions. Your user needs permission to read and write secrets. Non-interactive use requires `--stdin` and either an explicit token or an unexpired cached session; stdin supplies a complete replacement for the selected environment.

The command supports basic authentication, API keys, OAuth client credentials, and JWT client assertions. For `oauth2`, stdin accepts `client_id`, `client_secret`, `access_token_url`, optional `scope`, and optional `credentials_location` (`header` or `body`). For `oauth2_client_credentials`, use `client_id`, `client_secret`, `token_url`, and optional `client_auth` (`client_secret_basic` or `client_secret_post`).

Only the selected environment's credentials are replaced. Other environments and existing secret metadata are preserved. Secret values are never printed or written to project files.

| Argument | Description |
|---|---|
| `integration` | Integration name or ID on the current branch. |

| Flag | Description |
|---|---|
| `--env` | Required: `sandbox`, `pre-release`, or `live`. |
| `--stdin` | Read a credentials JSON object from stdin. |
| `--private-key-file` | Read the JWT signing key from a PEM file. |
| `--token-env` | Environment variable holding the Studio access token; defaults to `POLY_STUDIO_ACCESS_TOKEN`. |

!!! warning "Credentials update immediately"
    Credentials are shared across project branches and take effect directly, including in `live`. No later push is needed.

`--json` output shape:

~~~json
{
  "success": true,
  "integration": "crm",
  "environment": "sandbox",
  "auth_type": "oauth2"
}
~~~
