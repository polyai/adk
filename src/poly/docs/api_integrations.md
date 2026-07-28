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
- **auth_type**: Authentication type (e.g. `none`, `basic`, `apiKey`, `oauth2`).

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