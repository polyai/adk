# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore


import typing


__all__ = ["Attachment"]


class Attachment:
    """An attachment to an Agent Response."""

    def __init__(
        self,
        content_url: str,
        content_type: typing.Literal["image", "weblink", "unspecified"],
        title: str | None = ...,
        preview_image_url: str | None = ...,
        call_to_action: str | None = ...,
    ): ...
    def to_dict(self):
        """Convert the Attachment to a dictionary."""
