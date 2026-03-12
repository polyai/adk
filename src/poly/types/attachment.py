# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from typing import Literal

__all__ = ["Attachment"]


class Attachment:
    """
    An attachment to an Agent Response.

    Attachments can be added to agent responses to provide additional context or information.
    They are currently only supported for WEBCHAT channels.
    """

    content_url: str
    content_type: Literal["image", "weblink", "unspecified"]
    title: str | None
    preview_image_url: str | None
    call_to_action: str | None

    def __init__(
        self,
        content_url: str,
        content_type: Literal["image", "weblink", "unspecified"],
        title: str | None = ...,
        preview_image_url: str | None = ...,
        call_to_action: str | None = ...,
    ) -> None: ...
    def to_dict(self) -> dict: ...
