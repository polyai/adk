---
title: MCP servers
description: Connect the agent to MCP (Model Context Protocol) servers and choose which of their tools it may call.
---

# MCP servers

<p class="lead">
MCP servers give the agent tools hosted outside the project. Declare each server in YAML, choose which of its tools the agent may call, and keep the connection settings under version control like any other resource.
</p>

## Location

~~~text
config/mcp.yaml
~~~

Connected servers are listed under the `mcp_servers` key and saved provider profiles under `mcp_profiles`. The file is optional; omit it if the agent uses no MCP servers.

## What MCP config contains

<div class="grid cards" markdown>

-   **Servers**

    ---

    The MCP servers the agent connects to, with the tools it may call on each.

-   **Profiles**

    ---

    Saved connection settings per provider, offered as the defaults when a server for that provider is connected in Agent Studio.

</div>

### Server fields

| Field | Required | Description |
|---|---|---|
| `provider_id` | Yes | Which MCP provider this server is for. Identifies the server in the file. |
| `url` | Yes | The server's `http(s)://` URL. |
| `auth` | No | How to authenticate. See [Authentication](#authentication). |
| `timeout` | No | Request timeout in seconds, from 1 to 30. |
| `enabled_functions` | No | Tool names the agent may call. Leave the key out to enable every tool the server offers; `[]` enables none. |

### Profile fields

| Field | Required | Description |
|---|---|---|
| `provider_id` | Yes | The provider these settings are for. Identifies the profile in the file. |
| `url` | Yes | The server's `http(s)://` URL. |
| `auth` | No | How to authenticate. See [Authentication](#authentication). |
| `timeout` | No | Request timeout in seconds, from 1 to 30. |

### Authentication

`auth` uses one of three methods:

| Method | Fields |
|---|---|
| Header | `header` (the header name) and `secret_name` |
| Query parameter | `query_param` (the parameter name) and `secret_name` |
| OAuth client credentials | `oauth`, with `client_id` and `token_url`, and optionally `client_secret_name`, `audience` and `scope` |

`secret_name` and `client_secret_name` name secrets stored in Agent Studio. The secret values are never pulled to or pushed from your machine.

### Example

~~~yaml
mcp_servers:
  - provider_id: ticketing
    url: https://mcp.ticketing.example.com/v1
    auth:
      header: Authorization
      secret_name: ticketing_mcp_token
    timeout: 15
    enabled_functions:
      - search_tickets
      - create_ticket
  - provider_id: internal-tools
    url: https://internal.example.com/mcp
    auth:
      oauth:
        client_id: my-client
        client_secret_name: internal_mcp_oauth_secret
        token_url: https://internal.example.com/oauth/token
        scope: tools:read

mcp_profiles:
  - provider_id: ticketing
    url: https://mcp.ticketing.example.com/v1
    auth:
      header: Authorization
      secret_name: ticketing_mcp_token
    timeout: 15
~~~

!!! info "Tool discovery state stays on the platform"
    Agent Studio records when it last listed a server's tools and how many it found. That state isn't written to `mcp.yaml`, and pushing a change to a server keeps it as it is.

## Validation

- `provider_id` and `url` are required, and `url` must be an `http(s)://` URL.
- `provider_id` must be unique within `mcp_servers`, and within `mcp_profiles`.
- `auth` sets only one of `header`, `query_param` and `oauth`.
- `header` and `query_param` need `secret_name`, and `secret_name` needs one of them.
- `oauth` needs `client_id` and `token_url`, and `token_url` must be an `http(s)://` URL.
- `timeout`, if set, is between 1 and 30.
- `enabled_functions` entries must be non-empty and unique.

## Best practices

- list the tools the agent needs in `enabled_functions` rather than enabling everything, so a server adding a tool doesn't change what the agent can do
- keep credentials in Agent Studio secrets and refer to them by name; never put a token in the URL

## Related pages

<div class="grid cards" markdown>

-   **API integrations**

    ---

    Define plain HTTP APIs the agent calls from functions and flows.
    [Open API integrations](./api_integrations.md)

-   **Functions**

    ---

    Write Python tools when an operation needs custom logic.
    [Open functions](./functions.md)

</div>
