"""Configuration discovery and YAML persistence for account-level SIP trunks.

Copyright PolyAI Limited
"""

import os
import stat
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from poly.project import AgentStudioProject

PROJECT_DEFAULT_OUTPUT = "__project_default__"
SIP_TRUNK_REGIONS = ("us-1", "euw-1", "uk-1")


@dataclass(frozen=True)
class AccountContext:
    """Resolved API context for an account-level SIP trunk operation."""

    region: str
    account_id: str


@dataclass(frozen=True)
class LoadedManageConfig:
    """Validated SIP trunk configuration plus its resolved API context."""

    path: str
    region: str
    account_id: str
    trunks: list[dict[str, Any]]
    source_digest: str


def validate_sip_trunk_region(region: str) -> str:
    """Validate a canonical ADK region supported by the SIP Trunking API."""
    if region not in SIP_TRUNK_REGIONS:
        raise ValueError(f"Unsupported SIP Trunking region: {region}")
    return region


def file_digest(path: str) -> str:
    """Return a stable digest used to detect edits between preview and apply."""
    with open(path, "rb") as source_file:
        return sha256(source_file.read()).hexdigest()


def _read_project_config(path: str) -> "AgentStudioProject | None":
    """Use the shared project lookup from an absolute directory path."""
    from poly.cli_commands.shared import read_project_config

    base_path = os.path.abspath(path)
    if os.path.isfile(base_path):
        base_path = os.path.dirname(base_path)
    return read_project_config(base_path)


def resolve_account_context(
    path: str,
    *,
    account_id: str | None = None,
    region: str | None = None,
) -> AccountContext:
    """Resolve explicit overrides or account and region from the current project."""
    if account_id is None or region is None:
        project = _read_project_config(path)
        if project is None:
            raise ValueError(
                "No project configuration found. Run from an ADK project or pass both "
                "--account-id and --region."
            )
        if account_id is None:
            account_id = project.account_id
        if region is None:
            region = project.region

    if not account_id:
        raise ValueError("An account ID is required.")
    return AccountContext(region=validate_sip_trunk_region(region), account_id=account_id)


def find_manage_file(base_path: str, file_path: str | None) -> str:
    """Find an explicit file, or check the project root and its immediate parent."""
    if file_path:
        resolved = os.path.abspath(file_path)
        if not os.path.isfile(resolved):
            raise FileNotFoundError(f"SIP trunk configuration not found: {resolved}")
        return resolved

    project = _read_project_config(base_path)
    if project is None:
        raise ValueError(
            "No project configuration found. Run from an ADK project or pass --file "
            "to select the SIP trunk configuration explicitly."
        )
    project_root = os.path.abspath(project.root_path)
    for directory in (project_root, os.path.dirname(project_root)):
        candidate = os.path.join(directory, "sip-trunks.yaml")
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError(
        "No sip-trunks.yaml found in the project root or its immediate parent. "
        "Create it there or pass --file."
    )


def load_manage_config(
    path: str,
    *,
    file_path: str | None = None,
    account_id: str | None = None,
    region: str | None = None,
) -> LoadedManageConfig:
    """Load a SIP trunk YAML file and resolve its account context."""
    from poly.resources.resource_utils import load_yaml

    context = resolve_account_context(path, account_id=account_id, region=region)
    config_path = find_manage_file(path, file_path)
    with open(config_path, "rb") as config_file:
        source = config_file.read()
    config = load_yaml(source.decode("utf-8"))
    source_digest = sha256(source).hexdigest()
    if config is None:
        config = []
    if isinstance(config, dict) and "region" in config:
        raise ValueError(
            "Do not set 'region' in sip-trunks.yaml; it is read from the current project. "
            "Remove it; use --region only to override the project region."
        )
    if not isinstance(config, list) or not all(isinstance(trunk, dict) for trunk in config):
        raise ValueError("sip-trunks.yaml must contain a top-level list of SIP trunk mappings.")

    return LoadedManageConfig(
        path=config_path,
        region=context.region,
        account_id=context.account_id,
        trunks=config,
        source_digest=source_digest,
    )


def persist_trunk_response(
    config_path: str,
    trunk_index: int,
    local_name: str,
    trunk: dict[str, Any],
) -> bool:
    """Save useful API-generated fields while preserving YAML formatting and comments."""
    from ruamel.yaml import YAML

    # Round-trip YAML retains comments and quotes when updating the user's file.
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    with open(config_path, encoding="utf-8") as config_file:
        config = yaml.load(config_file)
    if not isinstance(config, list):
        raise ValueError("sip-trunks.yaml must contain a top-level list of SIP trunk mappings.")
    if trunk_index >= len(config) or not isinstance(config[trunk_index], dict):
        raise ValueError(f"Could not find SIP trunk '{local_name}' to save metadata.")
    entry = config[trunk_index]

    changed = False
    trunk_id = trunk.get("id")
    if trunk_id:
        existing_id = entry.get("id")
        if existing_id and existing_id != trunk_id:
            raise ValueError(
                f"Refusing to replace SIP trunk '{local_name}' ID {existing_id} with {trunk_id}."
            )
        if existing_id != trunk_id:
            if hasattr(entry, "insert"):
                entry.insert(0, "id", trunk_id)
            else:
                entry["id"] = trunk_id
            changed = True

    inbound = trunk.get("inbound") or {}
    returned_fields = {"hostname": inbound.get("hostname")}
    for field, value in returned_fields.items():
        if value is not None and entry.get(field) != value:
            entry[field] = value
            changed = True

    inbound_auth = entry.get("inbound_auth")
    if isinstance(inbound_auth, dict) and inbound_auth.get("type") == "digest":
        realm = (inbound.get("sip_auth") or {}).get("realm")
        if realm is not None and inbound_auth.get("realm") != realm:
            inbound_auth["realm"] = realm
            changed = True

    if not changed:
        return False

    file_mode = stat.S_IMODE(os.stat(config_path).st_mode)
    temporary_path = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=os.path.dirname(config_path),
            prefix=".sip-trunks-",
            suffix=".yaml.tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name
            yaml.dump(config, temporary_file)
        os.chmod(temporary_path, file_mode)
        os.replace(temporary_path, config_path)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)
    return True


def default_export_path(path: str) -> str:
    """Return the default SIP trunk export path in the current project root."""
    project = _read_project_config(path)
    if project is None:
        raise ValueError(
            "No project configuration found. Run from an ADK project or pass --output FILE."
        )
    return os.path.join(os.path.abspath(project.root_path), "sip-trunks.yaml")


def write_export(
    path: str,
    data: dict[str, Any],
    *,
    output: str | None = PROJECT_DEFAULT_OUTPUT,
    force: bool = False,
) -> str:
    """Write an API export in the reusable top-level-list YAML format."""
    from poly.resources.resource_utils import dump_yaml

    output_path = (
        default_export_path(path)
        if output in {None, PROJECT_DEFAULT_OUTPUT}
        else os.path.abspath(output)
    )
    if os.path.exists(output_path) and not force:
        raise FileExistsError(f"Refusing to overwrite {output_path}. Pass --force to replace it.")
    parent = os.path.dirname(output_path)
    if not os.path.isdir(parent):
        raise FileNotFoundError(f"Output directory does not exist: {parent}")
    with open(output_path, "w", encoding="utf-8") as output_file:
        dump_yaml(data["sip_trunks"], output_file)
    return output_path
