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
- **description**: Optional note on what the operation does (up to 1000 characters).
- **method**: HTTP method (e.g. `GET`, `POST`, `PUT`, `DELETE`).
- **resource**: Path template (e.g. `/tickets/{id}`). Path variables are exposed as arguments when calling the operation.
- **headers**: Optional mapping of header name to value, sent on every call to the operation (up to 50). `Authorization` and `Host` come from the environment config and can't be set here. Quote a value YAML would otherwise read as a number, date, list or mapping (`X-Version: '1.10'`).
- **request_query_schema**: Optional JSON Schema (2020-12) for the query parameters, written as a YAML mapping.
- **request_body_schema**: Optional JSON Schema for the request body. Not allowed on `GET` or `DELETE`.
- **response_schemas**: Optional mapping from a response key to a JSON Schema for that response body. Keys are a status code (`'200'`), a status class (`'4XX'`) or `default`. An unquoted `200:` is read as the text `'200'`, and `poly pull` writes status keys quoted.
- **schema_source**: Where the schemas came from: `observed`, `openapi` or `default`. Hand-written schemas are `manual`, the default, which the file never spells out: a schema without the key is pushed as `manual`, and `poly pull` omits the key for one. Editing a schema without changing its `schema_source` pushes it as `manual`, and the next `poly pull` drops the key.

The optional fields are omitted from the file when empty, and removing one from the file clears it in Agent Studio on the next push.

Schemas are nested YAML, not JSON strings, so quote values YAML would otherwise type for you (`type: "null"`, a `pattern` or `const` that looks like a date or number). Each schema must pass the JSON Schema 2020-12 meta-schema, nest objects and arrays at most 64 levels deep and stay under 64 KB as compact JSON. A `pattern` is a JavaScript regular expression, which Agent Studio checks on push.

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