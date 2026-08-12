# SMS Templates

## Purpose
Text messages the agent can send during a conversation (confirmations, links, verification codes), with dynamic
content via variables.

## Location
`config/sms_templates.yaml`, listed under the `sms_templates` key.

## Structure
| Field | Notes |
|---|---|
| `name` | Identifier; referenced as `{{twilio_sms:template_name}}` |
| `text` | Message body; use `{{vrbl:variable_name}}` for dynamic values from `conv.state` |
| `env_phone_numbers` (optional) | Per-environment sender numbers: `sandbox`, `pre_release`, `live` |

```yaml
sms_templates:
  - name: booking_confirmation
    text: "Hi {{vrbl:customer_name}}, your booking for {{vrbl:booking_date}} is confirmed. Reference: {{vrbl:booking_ref}}"
    env_phone_numbers:
      sandbox: "+15551234567"
      live: "+15559876543"
  - name: verification_code
    text: "Your verification code is {{vrbl:verification_code}}. It expires in 10 minutes."
```

## Usage
- In rules/topics/flows: `{{twilio_sms:template_name}}` instructs the LLM to send it at the right moment.
- In code: call a function that triggers the SMS via `conv` or the platform API.
- Variables: set the referenced state (e.g. `conv.state.customer_name`) before the SMS is triggered, so
  `{{vrbl:...}}` resolves.

## Best practices
Set state variables before sending; use separate templates per purpose (confirmation, verification, follow-up);
configure `env_phone_numbers` per environment.
