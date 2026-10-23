# API Integrations

## Purpose

API integrations let you define external HTTP APIs in your project and call them from [functions](functions.md) and [flows](flows.md) without writing custom request code. Use them when your agent needs to:

- Fetch or send data to an external system (CRM, ticketing, booking, payments)
- Call internal services with a shared, inspectable definition
- Avoid maintaining custom HTTP logic inside function code

## Location

`config/api_integrations.yaml`. Integrations are listed under the `api_integrations` key.

## Structure

Each API integration has:

- **name**: Identifier for the API. Becomes the namespace at runtime: `conv.api.<name>`.
- **description**: Optional description of what the API is used for.
- **environments**: Per-environment config (see below).
- **operations**: List of HTTP operations (method, name, resource path).

## Environments

Each integration supports separate configuration for:

- **sandbox** (draft)
- **pre_release**
- **live**

Per environment you set:

- **base_url**: Base URL for that environment (e.g. `https://website.com`).
- **auth_type**: Authentication type (`none`, `basic`, `apiKey`, `oauth2`, `oauth2_client_credentials` or `jwt_client_assertion`).

This lets you test against staging in sandbox and promote without changing code.

## Operations

Each operation is one HTTP endpoint. You define:

- **name**: Operation name; used at runtime as `conv.api.<api_name>.<operation_name>(...)`.
- **method**: HTTP method (e.g. `GET`, `POST`, `PUT`, `DELETE`).
- **resource**: Path template (e.g. `/tickets/{id}`). Path variables are exposed as arguments when calling the operation.

## Usage

- **In functions and flows**: Call an operation with `conv.api.<api_name>.<operation_name>(...)`. Path variables can be positional or keyword arguments.
- **Return value**: Calls return a `requests.Response`-like object — use `response.status_code`, `response.text`, `response.json()` as usual.
- **Query, body, headers**: Operations accept keyword arguments for `params`, `json`, `headers`, etc., similar to a standard HTTP client.
- **Authentication**: Configured at the API level per environment; credentials are managed by Agent Studio and are not stored in the YAML or embedded in flows and functions.

## Example

```yaml
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
        method: PATCH
        resource: /contacts/{contact_id}
```

In a function you might call:

```python
response = conv.api.salesforce.get_contact("123")
data = response.json()
return {"content": f"Status: {data.get('status', 'unknown')}."}
```

```python
response = conv.api.salesforce.update_contact(
    params={"id": "123"},
    json={"phone_number": "456"}
)
```

## Testing with mocked responses

A conversation that branches on an operation's response (e.g. slot negotiation, availability checks) needs that response to be deterministic to test reliably. Test cases can mock an operation's response per test — see [Tests: API mocks](tests.md#api-mocks).

## Set credentials from the CLI

Push the integration definition first, including its base URL and auth type for the target environment. Then run this from the local project:

```bash
poly api-integrations configure salesforce --env sandbox
```

The command shows saved values in brackets, masking client IDs and secrets and displaying the full token URL; Enter keeps a saved required value. Newly typed values are visible, like `aws configure`. Missing required fields are prompted again, and credentials location uses an arrow-key picker. Scope is optional; Enter skips it. The command uses `POLY_STUDIO_ACCESS_TOKEN` if set, otherwise reuses a cached regional Studio session until it expires. It prompts for sign-in only when no unexpired session exists. Your Studio user needs permission to read and write secrets; the ADK API key is also needed to look up the integration.

For automation, supply a Studio access token through `POLY_STUDIO_ACCESS_TOKEN` (or choose another variable with `--token-env`) and pipe a JSON object with `--stdin`:

```bash
your-secret-provider | poly api-integrations configure salesforce --env sandbox --stdin --json
```

For `oauth2`, the input object has this shape (replace the placeholders):

```json
{
  "client_id": "<client-id>",
  "client_secret": "<client-secret>",
  "access_token_url": "https://example.com/oauth/token",
  "scope": "",
  "credentials_location": "header"
}
```

For `oauth2_client_credentials`, use `client_id`, `client_secret`, `token_url`, and optionally `client_auth` (`client_secret_basic` by default, or `client_secret_post`). The command also supports basic auth, API keys, and JWT client assertions. For JWT signing keys, use `--private-key-file path/to/key.pem` or the `private_key` field on stdin.

You can select an integration by name or ID. `--env` accepts `sandbox`, `pre-release`, or `live`. Each write replaces the selected environment's credentials and preserves other environments and secret metadata. Credentials are shared across project branches and take effect directly in Studio; this command does not require a later push. Secret values are not printed or saved to project files.
