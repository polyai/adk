# SMS Templates

## Purpose

SMS templates define text messages the agent can send during a conversation (e.g. confirmation texts, links, verification codes). They support dynamic content via variables.

## Location

`config/sms_templates.yaml`. Templates are listed under the `sms_templates` key.

## Structure

Each template has:
- **name**: Identifier. Referenced in prompts as `{{twilio_sms:template_name}}`.
- **text**: Message body. Use `{{vrbl:variable_name}}` for dynamic values from `conv.state`.
- **env_phone_numbers** (optional): Per-environment sender phone numbers:
  - **sandbox**: Phone number for sandbox environment
  - **pre_release**: Phone number for pre-release environment
  - **live**: Phone number for production

## Example
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

- **In rules / topics / flows**: Use `{{twilio_sms:template_name}}` to instruct the LLM to send the SMS at the right moment.
- **In code**: Call a function that triggers the SMS via `conv` or the platform API.
- **Variables**: Set the referenced variables in `conv.state` before the SMS is triggered, so the template can resolve `{{vrbl:...}}` placeholders.

## Best practices
- Set state variables (e.g. `conv.state.customer_name`) before the SMS is sent.
- Use separate templates for different purposes (confirmation, verification, follow-up).
- Configure `env_phone_numbers` to use different sender numbers per environment.
