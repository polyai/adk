"""Builders for standalone platform commands.

Copyright PolyAI Limited
"""

from poly.handlers.protobuf.channels_pb2 import (
    Channel_UpdateStatus,
    ChannelStatus,
    WebChatChannel_UpdateStatus,
)
from poly.handlers.protobuf.commands_pb2 import Command


def create_command_webchat_channel_update_status(enabled: bool) -> Command:
    """Create a Channel_UpdateStatus command with the given status."""
    if enabled:
        status = ChannelStatus.CREATED
    else:
        status = ChannelStatus.NOT_CREATED
    return Command(
        type="channel_update_status",
        channel_update_status=Channel_UpdateStatus(
            webchat=WebChatChannel_UpdateStatus(status=status),
        ),
    )
