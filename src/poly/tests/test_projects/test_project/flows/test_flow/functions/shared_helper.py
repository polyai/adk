from _gen import *  # <AUTO GENERATED>


@func_description("A helper function with the same name as a function in another flow.")
@func_parameter("value", "The value to process")
def shared_helper(conv: Conversation, flow: Flow, value: str):
    """A helper function with the same name as a function in another flow."""
    return f"Flow-specific helper: {value}"
