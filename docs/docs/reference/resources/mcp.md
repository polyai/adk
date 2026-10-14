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

Servers are listed under the `mcp_servers` key. The file is optional; omit it if the agent uses no MCP servers.

## What an MCP server contains

Each entry is one server the agent connects to: where it is, how to authenticate, and which of its tools the agent may call.

### Fields

| Field | Required | Description |
|---|---|---|
| `provider_id` | Yes | Identifies the server. For a provider from the Agent Studio catalogue, use its id (e.g. `tavily`); for any other server, use any short key (e.g. `deepwiki`). |
| `url` | Yes | The server's `http(s)://` URL. |
| `auth` | No | How to authenticate. See [Authentication](#authentication). |
| `timeout` | No | Request timeout in seconds, from 1 to 30. |
| `enabled_functions` | No | Tool names the agent may call. Leave the key out to enable every tool the server offers; `[]` enables none. |

!!! warning "Changing `provider_id` replaces the server"
    Servers added in Agent Studio as custom servers show up with a `provider_id` like `custom:1791899588123`. Keep that value: a different `provider_id` is pushed as a new server, and the old one is deleted.

### Authentication

`auth` uses one of three methods:

| Method | Fields |
|---|---|
| Header | `header` (the header name) and `secret_name` |
| Query parameter | `query_param` (the parameter name) and `secret_name` |
| OAuth client credentials | `oauth`, with `client_id`, `client_secret_name` and `token_url`, and optionally `audience` and `scope` |

`secret_name` and `client_secret_name` are the names of secrets stored in Agent Studio. The secret values are never pulled to or pushed from your machine. A secret is sent as the whole header or parameter value, so for a bearer token store `Bearer <token>` as the secret.

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
~~~

!!! info "Tool discovery state stays on the platform"
    Agent Studio records when it last listed a server's tools and how many it found. That state isn't written to `mcp.yaml`, and pushing a change to a server keeps it as it is.

!!! note "Saved profiles aren't synced"
    Agent Studio keeps a saved profile for a disconnected provider so it can be reconnected. Profiles hold the same settings as a server, so the ADK doesn't sync them. Disconnecting a server in Agent Studio removes it from `mcp_servers` on the next pull.

## Validation

- `provider_id` and `url` are required, and `url` must be an `http(s)://` URL.
- `provider_id` must be unique within `mcp_servers`.
- `auth` sets only one of `header`, `query_param` and `oauth`.
- `header` and `query_param` need `secret_name`, and `secret_name` needs one of them.
- `oauth` needs `client_id`, `client_secret_name` and `token_url`, and `token_url` must be an `http(s)://` URL.
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
