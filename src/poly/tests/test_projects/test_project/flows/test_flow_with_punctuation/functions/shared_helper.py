from _gen import *  # <AUTO GENERATED>


@func_description("Another helper with the same name as a function in another flow.")
@func_parameter("value", "The value to process")
def shared_helper(conv: Conversation, flow: Flow, value: str):
    """Another helper with the same name as a function in another flow."""
    return f"Punctuation flow helper: {value}"
