# MCP Servers

## Purpose

MCP (Model Context Protocol) servers give the agent tools hosted outside the project. The agent connects to each server, discovers its tools, and can call the ones you enable. Use them when a service already exposes its operations over MCP and you don't want to wrap each one in a [function](functions.md) or an [API integration](api_integrations.md).

## Location

`config/mcp.yaml`. Servers are listed under the `mcp_servers` key. The file is optional.

## Structure

Each server the agent connects to:

- **provider_id**: Identifies the server, and is unique within the file. For a provider from the Agent Studio catalogue, use its id (e.g. `tavily`). For any other server, use any short key (e.g. `deepwiki`). Servers added in Agent Studio as custom servers show up as `custom:<number>`; keep that value, as changing it replaces the server with a new one.
- **url**: The server's `http(s)://` URL.
- **auth**: Optional. How to authenticate (see below).
- **timeout**: Optional. Request timeout in seconds, from 1 to 30.
- **enabled_functions**: Optional. The tool names the agent may call. Leave the key out to enable every tool the server offers; `[]` enables none.

### auth

Set one of these:

- **header** and **secret_name**: send the secret in this request header.
- **query_param** and **secret_name**: send the secret as this query parameter.
- **oauth**: OAuth client credentials, with **client_id**, **client_secret_name** and **token_url** required and **audience** and **scope** optional.

`secret_name` and `client_secret_name` are the names of secrets stored in Agent Studio. The secret values are never pulled or pushed. A secret is sent as the whole header or parameter value, so for a bearer token store `Bearer <token>`.

## Example

```yaml
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
  # Added in Agent Studio as a custom server; keep its provider_id as pulled
  - provider_id: custom:1791899588123
    url: https://tools.example.com/mcp
    auth:
      query_param: api_key
      secret_name: tools_api_key
```

## Notes

- The platform's tool discovery state (when tools were last listed and how many were found) is not stored in the YAML. Pushing a change keeps it as it is.
- Saved MCP profiles, which Agent Studio keeps so a disconnected provider can be reconnected, are not synced. Disconnecting a server in Agent Studio removes it from `mcp_servers` on the next pull.
