from _gen import *  # <AUTO GENERATED>


@func_description("Calculate total amount.")
@func_parameter("amount", "The base amount to calculate from")
def calculate_total(conv: Conversation, flow: Flow, amount: float):
    """Calculate total amount."""
    return amount * 1.1
