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

| Field | Description |
|---|---|
| `name` | Operation name. Called at runtime as `conv.api.<api_name>.<name>(...)`. |
| `description` | Optional note on what the operation does, up to 1000 characters. |
| `method` | One of `GET`, `POST`, `PATCH`, `PUT`, `DELETE`. |
| `resource` | Path template, e.g. `/tickets/{id}`. Path variables become call arguments. |
| `headers` | Optional mapping of header name to value, sent on every call to the operation. Up to 50 headers. `Authorization` and `Host` come from the environment config and can't be set here. |
| `request_query_schema` | Optional [JSON Schema](https://json-schema.org/draft/2020-12){ target="_blank" rel="noopener" } for the query parameters, written as a YAML mapping. |
| `request_body_schema` | Optional JSON Schema for the request body. Not allowed on `GET` or `DELETE`. |
| `response_schemas` | Optional mapping from a response key to a JSON Schema for that response body. Keys are a status code (`'200'`), a status class (`'4XX'`) or `default`. An unquoted `200:` is read as the text `'200'`, and `poly pull` writes status keys quoted. |
| `schema_source` | Where the schemas came from: `observed`, `openapi` or `default`. Hand-written schemas are `manual`, the default, which the file never spells out: a schema without the key is pushed as `manual`, and `poly pull` omits the key for one. Editing a schema without changing its `schema_source` pushes it as `manual`, and the next `poly pull` drops the key. |

The optional fields are omitted from the file when empty, and removing one from the file clears it in Agent Studio on the next push.

Schemas are nested YAML, not JSON strings, so quote values YAML would otherwise type for you: `type: "null"`, a `pattern` or `const` that looks like a date or a number. Schemas written in Agent Studio or imported from an OpenAPI document pull down unchanged and push back as they were.

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
        method: GET
        resource: /contacts/{contact_id}
      - name: update_contact
        description: Change a contact's phone number
        method: PATCH
        resource: /contacts/{contact_id}
        headers:
          Content-Type: application/json
        request_body_schema:
          type: object
          required: [phone_number]
          properties:
            phone_number:
              type: string
        response_schemas:
          '200':
            type: object
            properties:
              id:
                type: string
              phone_number:
                type: string
          default:
            type: object
            properties:
              error:
                type: string
~~~

## Usage

- **Calling an operation** — `conv.api.<api_name>.<operation_name>(...)` from a function or flow. Path variables can be passed positionally or as keyword arguments.
- **Return value** — a `requests.Response`-like object; use `.status_code`, `.text`, and `.json()` as normal.
- **Extra request data** — pass `params`, `json`, `headers`, etc. as keyword arguments, same as a standard HTTP client.
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
- An operation's `description` is at most 1000 characters.
- Header names are HTTP tokens (letters, digits and ``!#$%&'*+-^_`|~``), unique ignoring case, and never `Authorization` or `Host`. Values are text, so quote one YAML would otherwise read as a number, date, list or mapping (`X-Version: '1.10'`); `true` and `false` are sent as written. Values are ASCII with no line breaks or control characters, don't start or end with a space, and are at most 4096 characters. An operation has at most 50 headers.
- Each schema is a mapping that passes the JSON Schema 2020-12 meta-schema, nests objects and arrays at most 64 levels deep, and is at most 64 KB as compact JSON. A `$schema` keyword, if present, must be `https://json-schema.org/draft/2020-12/schema`.
- `request_body_schema` is not allowed on `GET` or `DELETE` operations.
- `response_schemas` keys match `^([1-5]\d{2}|[1-5]XX|default)$`.
- `schema_source` is one of `default`, `manual`, `observed`, `openapi`.
- `$ref`, `$id` and `$schema` values must be valid URIs. The ADK does not check this locally; Agent Studio refuses them on push.
- A `pattern` must compile as a JavaScript regular expression with the `u` flag. Agent Studio checks this on push; `poly validate` does not, since Python's regex syntax differs.

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
