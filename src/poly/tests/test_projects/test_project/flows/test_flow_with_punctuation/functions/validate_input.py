from _gen import *  # <AUTO GENERATED>


@func_description("Another validate_input with same name as other flow.")
@func_parameter("input_value", "The input value to validate")
def validate_input(conv: Conversation, flow: Flow, input_value: str):
    """Another validate_input with same name as other flow."""
    return input_value.isdigit()
