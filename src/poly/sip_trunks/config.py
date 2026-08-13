"""Configuration discovery and YAML persistence for account-level SIP trunks.

Copyright PolyAI Limited
"""

import os
import stat
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from io import StringIO
from typing import Any

from ruamel.yaml import YAML

from poly.cli_commands.shared import read_project_config

ACCOUNT_DEFAULT_OUTPUT = "__account_default__"
SIP_TRUNK_REGIONS = ("us-1", "euw-1", "uk-1")
SIP_TRUNK_REGION_ALIASES = {
    "us": "us-1",
    "eu": "euw-1",
    "uk": "uk-1",
}


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


def normalize_sip_trunk_region(region: str) -> str:
    """Normalize a region supported by the SIP Trunking API."""
    candidate = region.strip().lower()
    normalized = SIP_TRUNK_REGION_ALIASES.get(candidate, candidate)
    if normalized not in SIP_TRUNK_REGIONS:
        raise ValueError(f"Unsupported SIP Trunking region: {region}")
    return normalized


def file_digest(path: str) -> str:
    """Return a stable digest used to detect edits between preview and apply."""
    with open(path, "rb") as source_file:
        return sha256(source_file.read()).hexdigest()


def _is_within(path: str, directory: str) -> bool:
    """Return whether path is inside directory on the current platform."""
    normalized_path = os.path.normcase(os.path.abspath(path))
    normalized_directory = os.path.normcase(os.path.abspath(directory))
    try:
        return os.path.commonpath((normalized_path, normalized_directory)) == normalized_directory
    except ValueError:
        # Windows paths on different drives have no common path.
        return False


def resolve_account_context(
    path: str,
    *,
    account_id: str | None = None,
    region: str | None = None,
) -> AccountContext:
    """Resolve account context from the current project or account directory."""
    base_path = os.path.abspath(path)
    if os.path.isfile(base_path):
        base_path = os.path.dirname(base_path)
    project = read_project_config(base_path)
    account_dir = os.path.dirname(project.root_path) if project else base_path
    return infer_account_context(
        account_dir,
        current_project=project,
        account_id=account_id,
        region=region,
    )


def infer_account_context(
    account_dir: str,
    *,
    current_project: Any = None,
    account_id: str | None = None,
    region: str | None = None,
) -> AccountContext:
    """Infer an account's region from project metadata below its directory."""
    yaml = YAML(typ="safe")
    discovered: list[tuple[str, str, str]] = []
    if current_project:
        discovered.append(
            (
                str(current_project.account_id),
                str(current_project.region),
                current_project.root_path,
            )
        )

    if os.path.isdir(account_dir):
        for entry in os.scandir(account_dir):
            if not entry.is_dir():
                continue
            project_path = os.path.join(entry.path, "project.yaml")
            if not os.path.isfile(project_path):
                continue
            with open(project_path, encoding="utf-8") as project_file:
                project_data = yaml.load(project_file) or {}
            if not isinstance(project_data, dict):
                continue
            project_account = project_data.get("account_id")
            project_region = project_data.get("region")
            if project_account and project_region:
                context = (str(project_account), str(project_region), entry.path)
                if context not in discovered:
                    discovered.append(context)

    discovered_accounts = {item[0] for item in discovered}
    if account_id is None:
        if current_project:
            account_id = str(current_project.account_id)
        elif len(discovered_accounts) == 1:
            account_id = discovered_accounts.pop()
        else:
            account_id = os.path.basename(os.path.abspath(account_dir))
    if not account_id:
        raise ValueError("An account ID is required.")

    if region is None:
        matching_regions = {
            normalize_sip_trunk_region(item[1]) for item in discovered if item[0] == account_id
        }
        if len(matching_regions) > 1:
            regions = ", ".join(sorted(matching_regions))
            raise ValueError(
                f"Projects for account '{account_id}' disagree on region ({regions}). "
                "Fix their project.yaml files or pass --region explicitly."
            )
        if matching_regions:
            region = matching_regions.pop()
        else:
            raise ValueError(
                f"Could not infer the region for account '{account_id}'. Run from one of "
                "its projects or pass --region."
            )

    normalized_region = normalize_sip_trunk_region(region)
    return AccountContext(region=normalized_region, account_id=account_id)


def find_manage_file(base_path: str, file_path: str | None) -> str:
    """Find the explicitly selected or nearest account-level SIP trunk file."""
    if file_path:
        resolved = os.path.abspath(file_path)
        if not os.path.isfile(resolved):
            raise FileNotFoundError(f"SIP trunk configuration not found: {resolved}")
        return resolved

    current = os.path.abspath(base_path)
    if os.path.isfile(current):
        current = os.path.dirname(current)
    while True:
        candidate = os.path.join(current, "sip-trunks.yaml")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    raise FileNotFoundError(
        "No sip-trunks.yaml found. Create it in the account directory or pass --file."
    )


def load_manage_config(
    path: str,
    *,
    file_path: str | None = None,
    account_id: str | None = None,
    region: str | None = None,
) -> LoadedManageConfig:
    """Load a SIP trunk YAML file and resolve its account context."""
    config_path = find_manage_file(path, file_path)
    yaml = YAML(typ="safe")
    with open(config_path, "rb") as config_file:
        source = config_file.read()
    config = yaml.load(source.decode("utf-8")) or {}
    source_digest = sha256(source).hexdigest()
    if isinstance(config, dict) and "region" in config:
        raise ValueError(
            "Do not set 'region' in sip-trunks.yaml; it is inferred from account project "
            "metadata. Remove it; use --region only to override the inferred value."
        )

    project = read_project_config(path)
    if project and not _is_within(config_path, os.path.dirname(project.root_path)):
        # An explicit file from another account must not inherit the current
        # project's account or region.
        project = None
    context = infer_account_context(
        os.path.dirname(config_path),
        current_project=project,
        account_id=account_id or (config.get("account_id") if isinstance(config, dict) else None),
        region=region,
    )

    if isinstance(config, list):
        trunks = config
    elif isinstance(config, dict):
        # Read the initial wrapped format as a migration convenience.
        trunks = config.get("sip_trunks", [])
    else:
        raise ValueError("sip-trunks.yaml must contain a list of SIP trunk mappings.")
    if isinstance(trunks, dict):
        # Read the initial preview format as a migration convenience.
        if not all(isinstance(trunk, dict) for trunk in trunks.values()):
            raise ValueError("Every SIP trunk value must be a mapping.")
        trunks = [{"name": local_name, **trunk} for local_name, trunk in trunks.items()]
    if not isinstance(trunks, list) or not all(isinstance(trunk, dict) for trunk in trunks):
        raise ValueError("sip-trunks.yaml must contain a list of SIP trunk mappings.")
    return LoadedManageConfig(
        path=config_path,
        region=context.region,
        account_id=context.account_id,
        trunks=trunks,
        source_digest=source_digest,
    )


def persist_trunk_response(
    config_path: str,
    trunk_index: int,
    local_name: str,
    trunk: dict[str, Any],
) -> bool:
    """Save useful API-generated fields while preserving YAML formatting and comments."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    with open(config_path, encoding="utf-8") as config_file:
        config = yaml.load(config_file)
    if isinstance(config, list):
        trunks = config
        if trunk_index >= len(trunks) or not isinstance(trunks[trunk_index], dict):
            raise ValueError(f"Could not find SIP trunk '{local_name}' to save metadata.")
        entry = trunks[trunk_index]
    elif isinstance(config, dict) and isinstance(config.get("sip_trunks"), list):
        # Preserve the initial wrapped schema when updating an existing file.
        trunks = config["sip_trunks"]
        if trunk_index >= len(trunks) or not isinstance(trunks[trunk_index], dict):
            raise ValueError(f"Could not find SIP trunk '{local_name}' to save metadata.")
        entry = trunks[trunk_index]
    elif isinstance(config, dict) and isinstance(config.get("sip_trunks"), dict):
        trunks = config["sip_trunks"]
        keys = list(trunks)
        if trunk_index >= len(keys) or not isinstance(trunks[keys[trunk_index]], dict):
            raise ValueError(f"Could not find SIP trunk '{local_name}' to save metadata.")
        entry = trunks[keys[trunk_index]]
    else:
        raise ValueError("sip-trunks.yaml must contain a list of SIP trunk mappings.")

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


def yaml_string(data: Any) -> str:
    """Serialize SIP trunk configuration as block-style YAML."""
    yaml = YAML()
    yaml.default_flow_style = False
    stream = StringIO()
    yaml.dump(data, stream)
    return stream.getvalue()


def default_export_path(path: str, account_id: str) -> str:
    """Return the account-level default path for a SIP trunk export."""
    project = read_project_config(path)
    if project and str(project.account_id) == account_id:
        return os.path.join(os.path.dirname(project.root_path), "sip-trunks.yaml")
    if project:
        accounts_root = os.path.dirname(os.path.dirname(project.root_path))
        return os.path.join(accounts_root, account_id, "sip-trunks.yaml")
    base_path = os.path.abspath(path)
    if os.path.basename(base_path) != account_id:
        base_path = os.path.join(base_path, account_id)
    return os.path.join(base_path, "sip-trunks.yaml")


def write_export(
    path: str,
    account_id: str,
    data: dict[str, Any],
    *,
    output: str | None = ACCOUNT_DEFAULT_OUTPUT,
    force: bool = False,
) -> str:
    """Write an API export in the reusable top-level-list YAML format."""
    output_path = (
        default_export_path(path, account_id)
        if output in {None, ACCOUNT_DEFAULT_OUTPUT}
        else os.path.abspath(output)
    )
    if os.path.exists(output_path) and not force:
        raise FileExistsError(f"Refusing to overwrite {output_path}. Pass --force to replace it.")
    parent = os.path.dirname(output_path)
    if not os.path.isdir(parent):
        raise FileNotFoundError(f"Output directory does not exist: {parent}")
    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(yaml_string(data["sip_trunks"]))
    return output_path
