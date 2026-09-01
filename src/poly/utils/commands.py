"""Builders for standalone platform commands.

Copyright PolyAI Limited
"""

from typing import Callable, TypeAlias

from poly.handlers.protobuf.channels_pb2 import (
    Channel_UpdateStatus,
    ChannelStatus,
    WebChatChannel_UpdateStatus,
)
from poly.handlers.protobuf.commands_pb2 import Command
from poly.handlers.protobuf.flows_pb2 import Flow_ClearStepSettings
from poly.handlers.protobuf.handoff_pb2 import Handoff_SetDefault
from poly.handlers.protobuf.variant_pb2 import Variant_SetDefaultVariant
from poly.resources import Handoff, Resource, Variant

ResourceMap: TypeAlias = dict[type[Resource], dict[str, Resource]]


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


def create_command_handoff_set_default(handoff_id: str) -> Command:
    """Create a command to make a handoff the default."""
    return Command(
        type="handoff_set_default",
        handoff_set_default=Handoff_SetDefault(id=handoff_id),
    )


def create_command_variant_set_default(variant_id: str) -> Command:
    """Create a command to make a variant the default."""
    return Command(
        type="variant_set_default_variant",
        variant_set_default_variant=Variant_SetDefaultVariant(id=variant_id),
    )


# is_default is not part of any create or update proto, so a resource that can be
# "the default" needs a separate command once it exists on the platform.
SET_DEFAULT_COMMAND_BUILDERS = {
    Handoff: create_command_handoff_set_default,
    Variant: create_command_variant_set_default,
}


def queue_set_default_commands(
    new_resources: ResourceMap,
    updated_resources: ResourceMap,
    commands: list[Command],
    queue_command: Callable[..., None],
) -> None:
    """Queue a set-default command for every new or updated default resource.

    is_default is not part of the create or update protos, so the platform needs a
    separate command. Queue these after the creates and updates, so that the resource
    already exists by the time the platform applies them.

    Args:
        new_resources (ResourceMap): New resources being pushed.
        updated_resources (ResourceMap): Updated resources being pushed.
        commands (list[Command]): Command list to append to, kept in send order.
        queue_command (Callable[..., None]): Callback that queues a single command.
    """
    for resource_dict in (new_resources, updated_resources):
        for resource_type, build_command in SET_DEFAULT_COMMAND_BUILDERS.items():
            for resource in resource_dict.get(resource_type, {}).values():
                if resource.is_default:
                    command = build_command(resource.resource_id)
                    queue_command(command)
                    commands.append(command)
