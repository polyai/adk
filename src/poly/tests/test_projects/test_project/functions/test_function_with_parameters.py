from _gen import *  # <AUTO GENERATED>


@func_description("Test function with parameters.")
@func_parameter("param1", "First parameter as string")
@func_parameter("param2", "Second parameter as integer")
def test_function_with_parameters(conv: Conversation, param1: str, param2: int):
    """Test function with parameters."""
    return f"Result: {param1} - {param2}"
