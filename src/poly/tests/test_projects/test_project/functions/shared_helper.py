from _gen import *  # <AUTO GENERATED>


@func_description("A shared helper function that can be used by multiple flows.")
@func_parameter("value", "The value to process")
def shared_helper(conv: Conversation, value: str):
    """A shared helper function that can be used by multiple flows."""
    return f"Processed: {value}"
