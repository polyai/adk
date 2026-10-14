---
title: API integrations
description: Define external HTTP APIs in a project and call them from functions and flows without writing custom request code.
---

# API integrations

<p class="lead">
API integrations declare an external HTTP API in YAML, so functions and flows can call it as <code>conv.api.&lt;name&gt;.&lt;operation&gt;(...)</code> instead of hand-rolling request code.
</p>

## Location

~~~text
config/api_integrations.yaml
~~~

All integrations for the project live in this one file, listed under the `api_integrations` key. The file is optional — omit it if the project makes no external HTTP calls.

## What an API integration contains

<div class="grid cards" markdown>

-   **Identity**

    ---

    A name (the runtime namespace) and an optional description.

-   **Environments**

    ---

    Separate base URL and auth type per `sandbox`, `pre-release`, and `live`.

-   **Operations**

    ---

    The HTTP endpoints exposed as callable methods.

</div>

### Fields

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Identifier for the API. Becomes the runtime namespace: `conv.api.<name>`. Must match `^[a-z_][a-z0-9_]*$` — lowercase letters, digits, and underscores, starting with a letter or underscore. |
| `description` | No | Free-text note on what the API is used for. |
| `environments` | Yes | Per-environment base URL and auth type — see below. |
| `operations` | No | List of HTTP operations this API exposes — see below. |

### Environments

Each integration configures `sandbox`, `pre-release`, and `live` separately, so you can point at a staging API in sandbox and promote to production without touching code:

| Field | Description |
|---|---|
| `base_url` | Base URL for that environment, e.g. `https://api.example.com`. May be left empty if the environment isn't wired up yet. |
| `auth_type` | One of `none`, `basic`, `apiKey`, `oauth2`, `oauth2_client_credentials`, `jwt_client_assertion`. |

Credentials themselves are managed by Agent Studio, not stored in the YAML — see [Usage](#usage) below.

### Operations

Each entry is one HTTP endpoint:

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Operation name. Called at runtime as `conv.api.<api_name>.<name>(...)`. |
| `description` | No | What the operation does, up to 1000 characters. |
| `method` | Yes | One of `GET`, `POST`, `PATCH`, `PUT`, `DELETE`. |
| `resource` | Yes | Path template, e.g. `/tickets/{id}`. Path variables become call arguments. |
| `headers` | No | Default request headers sent on every call, as a map of header name to value. Headers passed at the call site override them. |

### Example

~~~yaml
api_integrations:
  - name: salesforce
    description: CRM and contact lookup
    environments:
      sandbox:
        base_url: https://sandbox-api.salesforce.com
        auth_type: oauth2
      pre-release:
        base_url: https://staging-api.salesforce.com
        auth_type: oauth2
      live:
        base_url: https://api.salesforce.com
        auth_type: oauth2
    operations:
      - name: get_contact
        description: Get a contact by its ID
        method: GET
        resource: /contacts/{contact_id}
        headers:
          Accept: application/json
      - name: update_contact
        method: PATCH
        resource: /contacts/{contact_id}
~~~

## Usage

- **Calling an operation** — `conv.api.<api_name>.<operation_name>(...)` from a function or flow. Path variables can be passed positionally or as keyword arguments.
- **Return value** — a `requests.Response`-like object; use `.status_code`, `.text`, and `.json()` as normal.
- **Extra request data** — pass `params`, `json`, `headers`, etc. as keyword arguments, same as a standard HTTP client. Headers passed here override the operation's default `headers`.
- **Authentication** — configured per environment at the API level; credentials are managed by Agent Studio and never appear in the YAML or in function/flow code.

~~~python
response = conv.api.salesforce.get_contact("123")
data = response.json()
return {"content": f"Status: {data.get('status', 'unknown')}."}
~~~

~~~python
response = conv.api.salesforce.update_contact(
    params={"id": "123"},
    json={"phone_number": "456"},
)
~~~

## Validation

- `name` is required and must match `^[a-z_][a-z0-9_]*$`.
- Each environment's `base_url` must be a valid `http(s)://` URL, or empty.
- `base_url` cannot be empty when `auth_type` is not `none`.
- `auth_type` must be one of `none`, `basic`, `apiKey`, `oauth2`, `oauth2_client_credentials`,
  `jwt_client_assertion`.
- Every operation needs a non-empty `name`, a `method` from the supported set, and a `resource` path matching a valid URL-path pattern (optionally with `{param}` placeholders).
- No two operations in the same integration may share both `name` and `method`.
- An operation's `description` can be at most 1000 characters.
- An operation can have at most 50 `headers`. Header names are case-insensitive and must be
  unique, and can't contain spaces, dots, colons, slashes or other separators.
- `Authorization` and `Host` can't be set as operation headers: they come from the environment's
  `auth_type` and `base_url`.
- Header values must be strings of at most 4096 characters, with no line breaks, control or
  non-ASCII characters, and no leading or trailing spaces. Quote values YAML would read as a
  number or boolean, e.g. `'2'`.

## Best practices

- name operations for what they do (`get_contact`, not `op1`)
- check `response.status_code` before trusting `response.json()` — a failed call still returns a response object
- keep credentials in Agent Studio's managed auth, never hard-coded in a function

## Related pages

<div class="grid cards" markdown>

-   **Functions**

    ---

    Call API integrations from global functions, lifecycle hooks, and function steps.
    [Open functions](./functions.md)

-   **Flows**

    ---

    Call API integrations from advanced-step and transition-function prompts.
    [Open flows](./flows.md)

-   **Tests**

    ---

    Mock an operation's response with `api_mocks` so a conversation that branches on it can be tested deterministically.
    [Open tests](./tests.md)

</div>
