from _gen import *  # <AUTO GENERATED>


@func_description("Validate input in flow.")
@func_parameter("input_value", "The input value to validate")
def validate_input(conv: Conversation, flow: Flow, input_value: str):
    """Validate input in flow."""
    return len(input_value) > 0
