# Copyright PolyAI Limited
__all__ = ["Attachment"]

from typing import Any
import typing

class Attachment:
    content_url: Any
    content_type: Any
    title: Any
    preview_image_url: Any
    call_to_action: Any
    def __init__(
        self,
        content_url: str,
        content_type: typing.Literal["image", "weblink", "unspecified"],
        title: str | None = None,
        preview_image_url: str | None = None,
        call_to_action: str | None = None,
    ) -> None: ...
    def to_dict(self): ...
