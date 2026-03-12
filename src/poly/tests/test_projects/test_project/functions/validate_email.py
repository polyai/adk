from _gen import *  # <AUTO GENERATED>


@func_description("Validate email format.")
@func_parameter("email", "The email address to validate")
def validate_email(conv: Conversation, email: str):
    """Validate email format."""
    return "@" in email and "." in email.split("@")[1]
