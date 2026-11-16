from _gen import *  # <AUTO GENERATED>


@func_description("Another shared helper with same name as global and other flow.")
@func_parameter("value", "The value to process")
def shared_helper(conv: Conversation, flow: Flow, value: str):
    """Another shared helper with same name as global and other flow."""
    return f"Punctuation flow helper: {value}"
