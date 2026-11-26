"""Live changes to outbound campaigns

Copyright PolyAI Limited
"""

import uuid
from typing import Any

from poly.handlers.protobuf import outbound_campaigns_pb2
from poly.handlers.protobuf.commands_pb2 import Command
from poly.handlers.sdk import SourcererSDK


class CampaignHandler:
    """Send publish, pause, resume and archive commands for campaigns to main."""

    def __init__(self, region: str, account_id: str, project_id: str):
        self.sdk = SourcererSDK(
            region=region,
            account_id=account_id,
            project_id=project_id,
            branch_id="main",
        )

    def publish(self, campaign_id: str) -> dict[str, Any]:
        """Publish the campaign's draft to live."""
        return self._send(
            Command(
                type="outbound_campaign_publish",
                outbound_campaign_publish=outbound_campaigns_pb2.OutboundCampaign_Publish(
                    id=campaign_id
                ),
            )
        )

    def pause(self, campaign_id: str) -> dict[str, Any]:
        """Pause the live campaign."""
        return self._send(
            Command(
                type="outbound_campaign_pause",
                outbound_campaign_pause=outbound_campaigns_pb2.OutboundCampaign_Pause(
                    id=campaign_id
                ),
            )
        )

    def resume(self, campaign_id: str) -> dict[str, Any]:
        """Resume the paused live campaign."""
        return self._send(
            Command(
                type="outbound_campaign_resume",
                outbound_campaign_resume=outbound_campaigns_pb2.OutboundCampaign_Resume(
                    id=campaign_id
                ),
            )
        )

    def archive(self, campaign_id: str) -> dict[str, Any]:
        """Archive the campaign."""
        return self._send(
            Command(
                type="outbound_campaign_archive_definition",
                outbound_campaign_archive_definition=(
                    outbound_campaigns_pb2.OutboundCampaign_ArchiveDefinition(id=campaign_id)
                ),
            )
        )

    def _send(self, command: Command) -> dict[str, Any]:
        command.metadata.CopyFrom(self.sdk.create_metadata())
        command.command_id = str(uuid.uuid4())
        self.sdk.add_command_to_queue(command)
        return self.sdk.send_command_batch()
