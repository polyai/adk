from _gen import *  # <AUTO GENERATED>


def process_payment(conv: Conversation, flow: Flow):
    """Process payment for the customer."""
    # Process payment logic here
    conv.state.customer_name = "John Doe"
    conv.state.payment_success = True
    return "Payment processed"
