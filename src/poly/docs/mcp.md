# MCP Servers

## Purpose

MCP (Model Context Protocol) servers give the agent tools hosted outside the project. The agent connects to each server, discovers its tools, and can call the ones you enable. Use them when a service already exposes its operations over MCP and you don't want to wrap each one in a [function](functions.md) or an [API integration](api_integrations.md).

## Location

`config/mcp.yaml`. Connected servers are listed under `mcp_servers` and saved provider profiles under `mcp_profiles`. The file is optional.

## Structure

### mcp_servers

Each server the agent connects to:

- **provider_id**: Which MCP provider this server is for. Unique within `mcp_servers`.
- **url**: The server's `http(s)://` URL.
- **auth**: Optional. How to authenticate (see below).
- **timeout**: Optional. Request timeout in seconds, from 1 to 30.
- **enabled_functions**: Optional. The tool names the agent may call. Leave the key out to enable every tool the server offers; `[]` enables none.

### mcp_profiles

Saved connection settings per provider, used as the defaults when a server for that provider is connected in Agent Studio. Same fields as a server except `enabled_functions`. `provider_id` is unique within `mcp_profiles`.

### auth

Set one of these:

- **header** and **secret_name**: send the secret in this request header.
- **query_param** and **secret_name**: send the secret as this query parameter.
- **oauth**: OAuth client credentials, with **client_id** and **token_url** required and **client_secret_name**, **audience** and **scope** optional.

`secret_name` and `client_secret_name` name secrets stored in Agent Studio. The secret values are never pulled or pushed.

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

mcp_profiles:
  - provider_id: ticketing
    url: https://mcp.ticketing.example.com/v1
    auth:
      header: Authorization
      secret_name: ticketing_mcp_token
    timeout: 15
```

## Notes

- The platform's tool discovery state (when tools were last listed and how many were found) is not stored in the YAML. Pushing a change keeps it as it is.
- MCP servers only reach a deployed agent when integrations are enabled for the account. If a pushed server has no effect on calls, check that with PolyAI before debugging the YAML.
