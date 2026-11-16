from _gen import *  # <AUTO GENERATED>


@func_description("A shared helper function with same name as global function.")
@func_parameter("value", "The value to process")
def shared_helper(conv: Conversation, flow: Flow, value: str):
    """A shared helper function with same name as global function."""
    return f"Flow-specific helper: {value}"
