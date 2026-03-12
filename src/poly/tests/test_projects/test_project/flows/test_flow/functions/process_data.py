from _gen import *  # <AUTO GENERATED>


@func_description("Process data in flow context.")
@func_parameter("data", "The data string to process")
def process_data(conv: Conversation, flow: Flow, data: str):
    """Process data in flow context."""
    conv.state.data_processed = True
    return f"Processed in flow: {data}"
