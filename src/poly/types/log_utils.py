# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore


__all__ = ["ConversationLogger"]


class ConversationLogger:
    """Logging utility for Conversation objects"""

    def __init__(self): ...
    def info(self, content: str, is_pii: bool = ..., **kwargs):
        """Log an info message"""

    def warning(self, content: str, is_pii: bool = ..., **kwargs):
        """Log a warning message"""

    def error(self, content: str, is_pii: bool = ..., **kwargs):
        """Log an error message"""
