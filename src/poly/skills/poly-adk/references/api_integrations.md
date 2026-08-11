# API Integrations

## Purpose
Define external HTTP APIs and call them from functions/flows without writing custom request code — for fetching
or sending data to a CRM, ticketing, booking, or payments system, or calling internal services.

## Location
`config/api_integrations.yaml`, listed under the `api_integrations` key.

## Structure
| Field | Notes |
|---|---|
| `name` | Identifier; becomes the runtime namespace `conv.api.<name>` |
| `description` | Optional description |
| `environments` | Per-environment config (see below) |
| `operations` | List of HTTP operations |

## Environments
Separate config per: `sandbox` (draft), `pre_release`, `live`. Per environment:
| Field | Notes |
|---|---|
| `base_url` | Base URL for that environment |
| `auth_type` | `none`, `basic`, `apiKey`, `oauth2`, etc. |
Lets you test against staging in sandbox and promote without code changes.

## Operations
| Field | Notes |
|---|---|
| `name` | Operation name; runtime call is `conv.api.<api_name>.<operation_name>(...)` |
| `method` | `GET`, `POST`, `PUT`, `DELETE`, etc. |
| `resource` | Path template, e.g. `/tickets/{id}`; path variables become call arguments |

## Usage
- Call an operation with `conv.api.<api_name>.<operation_name>(...)`; path variables can be positional or keyword.
- Return value is a `requests.Response`-like object: `.status_code`, `.text`, `.json()`.
- Operations accept keyword args for `params`, `json`, `headers`, like a standard HTTP client.
- Auth is configured at the API level per environment; credentials are managed by Agent Studio, never stored in
  YAML or embedded in flows/functions.

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

In a function:
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
