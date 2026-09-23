# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from __future__ import annotations

__all__ = ["Attachment"]

from typing import Any
import typing


class Attachment:
    content_url: Any
    content_type: Any
    title: Any
    preview_image_url: Any
    call_to_action: Any
    chart_spec: Any

    def __init__(
        self,
        content_url: str | None = None,
        content_type: typing.Literal[
            "image", "weblink", "video", "graph", "unspecified"
        ] = "unspecified",
        title: str | None = None,
        preview_image_url: str | None = None,
        call_to_action: str | None = None,
        chart_spec: dict | None = None,
    ) -> None: ...
    def to_dict(self): ...
