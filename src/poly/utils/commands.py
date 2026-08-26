"""Builders for standalone platform commands.

Copyright PolyAI Limited
"""

from poly.handlers.protobuf.channels_pb2 import (
    Channel_UpdateStatus,
    ChannelStatus,
    WebChatChannel_UpdateStatus,
)
from poly.handlers.protobuf.commands_pb2 import Command
from poly.handlers.protobuf.flows_pb2 import Flow_ClearStepSettings


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


def create_command_clear_flow_settings(
    flow_id: str, step_id: str, cleared_fields: list[str]
) -> Command:
    """Create a command to clear flow settings."""
    return Command(
        type="clear_step_settings",
        clear_step_settings=Flow_ClearStepSettings(
            flow_id=flow_id,
            step_id=step_id,
            sections=cleared_fields,
        ),
    )
