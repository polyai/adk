"""Matching and planning for merging campaign node code on pull.

Copyright PolyAI Limited
"""

import os
from dataclasses import dataclass, field
from typing import Callable, Optional

from poly.resources.outbound_campaign import OutboundCampaignNode, campaign_folder_of

TRIGGER = "trigger"


@dataclass
class LocalCampaignCode:
    """The local function files, and the local nodes reading them, as found before a pull.

    Attributes:
        files: Every `.py` under a campaign's `functions/`, by path, with its contents.
        kept: The path each local node with a saved id reads, by node id.
        new: The type of each node added locally, by the path it reads.
    """

    files: dict[str, str] = field(default_factory=dict)
    kept: dict[str, str] = field(default_factory=dict)
    new: dict[str, Optional[str]] = field(default_factory=dict)

    def followed(self, follow: Callable[[str], str]) -> "LocalCampaignCode":
        """Return the same scan with every path passed through `follow`."""
        return LocalCampaignCode(
            files={follow(path): code for path, code in self.files.items()},
            kept={node_id: follow(path) for node_id, path in self.kept.items()},
            new={follow(path): node_type for path, node_type in self.new.items()},
        )

    def holder(self, path: str) -> Optional[str]:
        """The id of the saved node whose local version reads `path`, if any."""
        return next((node_id for node_id, held in self.kept.items() if held == path), None)

    def removed_owner(
        self, path: str, original: dict[str, OutboundCampaignNode], root: str
    ) -> Optional[str]:
        """The id of the saved node removed locally whose saved function file is `path`, if any."""
        return next(
            (
                node_id
                for node_id, node in original.items()
                if node_id not in self.kept and os.path.join(root, node.function_file) == path
            ),
            None,
        )


def _node_type(node: OutboundCampaignNode) -> Optional[str]:
    return node.data.get("type") if isinstance(node.data, dict) else None


def claim(
    incoming: dict[str, OutboundCampaignNode],
    original: dict[str, OutboundCampaignNode],
    local: LocalCampaignCode,
    root: str,
) -> dict[str, str]:
    """Return the local file holding each incoming node's local code, by node id.

    A node kept locally claims the file it reads. A saved trigger missing locally claims the
    one trigger added locally in its campaign, as push pairs them. Any other node missing
    locally claims a node added locally at its own path, if it has the same type.
    """
    claimed = {node_id: local.kept[node_id] for node_id in incoming if node_id in local.kept}

    def free(path: str) -> bool:
        return path not in claimed.values()

    for node_id, node in incoming.items():
        if node_id in claimed or node_id not in original or _node_type(node) != TRIGGER:
            continue
        folder = campaign_folder_of(node.function_file)
        heirs = [
            path
            for path, node_type in local.new.items()
            if node_type == TRIGGER and campaign_folder_of(path) == folder and free(path)
        ]
        if len(heirs) == 1:
            claimed[node_id] = heirs[0]

    for node_id, node in incoming.items():
        if node_id in claimed:
            continue
        path = os.path.join(root, node.function_file)
        if local.new.get(path, False) == _node_type(node) and free(path):
            claimed[node_id] = path
    return claimed


def plan(
    incoming: dict[str, OutboundCampaignNode],
    original: dict[str, OutboundCampaignNode],
    claimed: dict[str, str],
    root: str,
    force: bool,
) -> dict[str, list[str]]:
    """Return the files each incoming node's merged code is written to, by node id.

    Force writes only the incoming node's file. Otherwise a node renamed only locally keeps
    its local file, and a node renamed differently on each side gets both files, since either
    name may survive the conflict in `campaign.yaml`.
    """
    targets: dict[str, list[str]] = {}
    for node_id, node in incoming.items():
        path = os.path.join(root, node.function_file)
        saved = original.get(node_id)
        local_path = claimed.get(node_id)
        if force or saved is None or local_path is None or local_path == path:
            targets[node_id] = [path]
            continue
        saved_path = os.path.join(root, saved.function_file)
        if path == saved_path:
            targets[node_id] = [local_path]
        elif local_path != saved_path:
            targets[node_id] = [path, local_path]
        else:
            targets[node_id] = [path]
    return targets
