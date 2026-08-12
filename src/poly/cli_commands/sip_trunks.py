"""SIP Trunking command family.

Copyright PolyAI Limited
"""

import os
import stat
import tempfile
from argparse import (
    ArgumentParser,
    Namespace,
    RawTextHelpFormatter,
    _SubParsersAction,
)
from getpass import getpass
from io import StringIO
from typing import Any

from ruamel.yaml import YAML

from poly.cli_commands.base import BaseCommand, Parents
from poly.cli_commands.shared import read_project_config
from poly.handlers.sip_trunking_api import SIPTrunkingAPIHandler
from poly.output.json_output import json_print


class SIPTrunksCommand(BaseCommand):
    """Manage account-level SIP trunks and their extensions."""

    command = "sip-trunks"

    _REGION_ALIASES = {
        "eu": "euw-1",
        "euw-1": "euw-1",
        "uk": "uk-1",
        "uk-1": "uk-1",
        "us": "us-1",
        "us-1": "us-1",
    }

    @staticmethod
    def _add_context_arguments(parser: ArgumentParser) -> None:
        parser.add_argument(
            "--account-id",
            help="PolyAI account ID. Defaults to the current project's account.",
        )
        parser.add_argument(
            "--region",
            type=str.lower,
            choices=list(SIPTrunksCommand._REGION_ALIASES),
            help="Account region (eu, uk, or us). Defaults to the current project's region.",
        )

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``sip-trunks`` subcommand tree."""
        parser = subparsers.add_parser(
            cls.command,
            parents=[parents.verbose],
            help="Manage SIP trunks and extensions.",
            description=(
                "Manage account-level SIP trunks and extension routing.\n\n"
                "Account and region default to the current ADK project.\n\n"
                "Examples:\n"
                "  adk sip-trunks manage\n"
                "  adk sip-trunks list --output\n"
                "  adk sip-trunks get <trunk-id>\n"
                "  adk sip-trunks delete <trunk-id>\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        actions = parser.add_subparsers(dest="sip_trunks_subcommand", required=True)
        leaf_parents = [parents.path, parents.json, parents.verbose]

        list_parser = actions.add_parser("list", parents=leaf_parents, help="List SIP trunks.")
        cls._add_context_arguments(list_parser)
        list_parser.add_argument(
            "-o",
            "--output",
            nargs="?",
            const="__account_default__",
            help=(
                "Write reusable YAML to FILE. When passed without FILE, writes "
                "sip-trunks.yaml in the account directory."
            ),
        )
        list_parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite an existing output file.",
        )

        manage_parser = actions.add_parser(
            "manage",
            parents=leaf_parents,
            help="Create or update SIP trunks from an account-level YAML file.",
            description=(
                "Create or update SIP trunks declared in sip-trunks.yaml.\n"
                "Resources omitted from the file are left unchanged."
            ),
        )
        cls._add_context_arguments(manage_parser)
        manage_parser.add_argument(
            "-f",
            "--file",
            dest="file_path",
            help=(
                "Configuration file. Defaults to the nearest sip-trunks.yaml "
                "found from --path towards the filesystem root."
            ),
        )
        manage_parser.add_argument(
            "--rotate-auth",
            metavar="TRUNK_ID",
            help=(
                "Prompt for and rotate credentials for this YAML-declared trunk. "
                "Normal manage operations never resend existing credentials."
            ),
        )
        manage_parser.add_argument(
            "-y",
            "--yes",
            action="store_true",
            help="Apply the displayed changes without prompting for confirmation.",
        )

        get_parser = actions.add_parser("get", parents=leaf_parents, help="Get a SIP trunk.")
        cls._add_context_arguments(get_parser)
        get_parser.add_argument("trunk_id", help="SIP trunk ID.")

        delete_parser = actions.add_parser(
            "delete", parents=leaf_parents, help="Delete a SIP trunk."
        )
        cls._add_context_arguments(delete_parser)
        delete_parser.add_argument("trunk_id", help="SIP trunk ID.")

    @classmethod
    def _resolve_context(cls, args: Namespace) -> tuple[str, str]:
        base_path = os.path.abspath(args.path)
        if os.path.isfile(base_path):
            base_path = os.path.dirname(base_path)
        project = read_project_config(base_path)
        account_dir = os.path.dirname(project.root_path) if project else base_path
        return cls._infer_account_context(
            account_dir,
            current_project=project,
            account_id=args.account_id,
            region=args.region,
        )

    @classmethod
    def _infer_account_context(
        cls,
        account_dir: str,
        *,
        current_project: Any = None,
        account_id: str | None = None,
        region: str | None = None,
    ) -> tuple[str, str]:
        """Infer an account's region from project metadata below its directory."""
        yaml = YAML(typ="safe")
        discovered: list[tuple[str, str, str]] = []
        if current_project:
            discovered.append(
                (str(current_project.account_id), str(current_project.region), current_project.root_path)
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
            matching_regions = {item[1] for item in discovered if item[0] == account_id}
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

        normalized_region = cls._REGION_ALIASES.get(region.lower())
        if normalized_region is None:
            raise ValueError(f"Unsupported SIP Trunking region: {region}")
        return normalized_region, account_id

    @staticmethod
    def _find_manage_file(base_path: str, file_path: str | None) -> str:
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

    @staticmethod
    def _persist_trunk_response(
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
                    f"Refusing to replace SIP trunk '{local_name}' ID {existing_id} with "
                    f"{trunk_id}."
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

    @classmethod
    def _load_manage_config(cls, args: Namespace) -> tuple[str, str, str, list[dict[str, Any]]]:
        config_path = cls._find_manage_file(args.path, args.file_path)
        yaml = YAML(typ="safe")
        with open(config_path, encoding="utf-8") as config_file:
            config = yaml.load(config_file) or {}
        if isinstance(config, dict) and "region" in config:
            raise ValueError(
                "Do not set 'region' in sip-trunks.yaml; it is inferred from account project "
                "metadata. Remove it; use --region only to override the inferred value."
            )

        project = read_project_config(args.path)
        region, account_id = cls._infer_account_context(
            os.path.dirname(config_path),
            current_project=project,
            account_id=args.account_id or (config.get("account_id") if isinstance(config, dict) else None),
            region=args.region,
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
            trunks = [
                {"name": local_name, **trunk}
                for local_name, trunk in trunks.items()
                if isinstance(trunk, dict)
            ]
        if not isinstance(trunks, list) or not all(isinstance(trunk, dict) for trunk in trunks):
            raise ValueError("sip-trunks.yaml must contain a list of SIP trunk mappings.")
        return config_path, region, str(account_id), trunks

    @staticmethod
    def _reject_yaml_secret(config: dict[str, Any], field: str) -> None:
        for key in (field, f"{field}_env"):
            if key in config:
                raise ValueError(
                    f"Do not store '{key}' in sip-trunks.yaml; credentials are prompted "
                    "only when they are required."
                )

    @classmethod
    def _managed_trunk_data(
        cls, local_name: str, config: dict[str, Any], *, create: bool
    ) -> tuple[dict[str, Any], bool]:
        if not isinstance(config, dict):
            raise ValueError(f"SIP trunk '{local_name}' must contain a mapping.")
        data: dict[str, Any] = {}
        for field in ("name", "sip_cidr", "rtp_cidr", "encrypted"):
            if field in config:
                data[field] = config[field]
        data.setdefault("name", local_name)

        if create:
            missing = [field for field in ("sip_cidr", "rtp_cidr") if field not in data]
            if missing:
                raise ValueError(
                    f"SIP trunk '{local_name}' is missing required field(s): {', '.join(missing)}"
                )

        secret_supplied = False
        inbound_auth = config.get("inbound_auth")
        if inbound_auth is not None:
            if not isinstance(inbound_auth, dict):
                raise ValueError(f"SIP trunk '{local_name}' inbound_auth must be a mapping.")
            auth_type = inbound_auth.get("type")
            if auth_type == "none":
                data["_disable_auth"] = True
            elif auth_type == "digest":
                cls._reject_yaml_secret(inbound_auth, "password")
                username = inbound_auth.get("username")
                if not username:
                    raise ValueError(
                        f"SIP trunk '{local_name}' digest auth requires a username."
                    )
                auth_data = {"username": username}
                data["inbound"] = {"sip_auth": auth_data}
            elif auth_type == "token":
                cls._reject_yaml_secret(inbound_auth, "token")
                data["inbound"] = {"sip_token_auth": {}}
            else:
                raise ValueError(
                    f"SIP trunk '{local_name}' inbound_auth.type must be digest, token, or none."
                )
        else:
            # Backwards-compatible reader for the initial preview schema.
            inbound = config.get("inbound")
        if inbound_auth is None and inbound is not None:
            if not isinstance(inbound, dict):
                raise ValueError(
                    f"SIP trunk '{local_name}' inbound configuration must be a mapping."
                )
            digest = inbound.get("sip_auth")
            token_auth = inbound.get("sip_token_auth")
            if digest is not None and token_auth is not None:
                raise ValueError(
                    f"SIP trunk '{local_name}' cannot use SIP digest and token auth together."
                )
            if digest is not None:
                if not isinstance(digest, dict):
                    raise ValueError("'sip_auth' must be a mapping.")
                cls._reject_yaml_secret(digest, "password")
                username = digest.get("username")
                if not username:
                    raise ValueError(
                        f"SIP trunk '{local_name}' digest auth requires a username."
                    )
                auth_data = {"username": username}
                data["inbound"] = {"sip_auth": auth_data}
            elif token_auth is not None:
                if not isinstance(token_auth, dict):
                    raise ValueError("'sip_token_auth' must be a mapping.")
                cls._reject_yaml_secret(token_auth, "token")
                data["inbound"] = {"sip_token_auth": {}}
        return data, secret_supplied

    @staticmethod
    def _prompt_auth_secret(
        local_name: str,
        current: dict[str, Any] | None,
        desired: dict[str, Any],
        *,
        rotate: bool,
    ) -> bool:
        """Prompt and add a secret only when the API operation requires one."""
        desired_inbound = desired.get("inbound")
        if not desired_inbound:
            if rotate:
                raise ValueError(
                    f"SIP trunk '{local_name}' must declare digest or token authentication "
                    "to rotate credentials."
                )
            return False

        current_inbound = (current or {}).get("inbound") or {}
        if "sip_auth" in desired_inbound:
            desired_auth = desired_inbound["sip_auth"]
            current_auth = current_inbound.get("sip_auth") or {}
            required = (
                current is None
                or rotate
                or not current_auth.get("enabled")
                or current_auth.get("username") != desired_auth.get("username")
            )
            if not required:
                return False
            secret = getpass(f"SIP password for {local_name}: ")
            if not secret:
                raise ValueError(f"A SIP password is required for trunk '{local_name}'.")
            desired_auth["password"] = secret
            return True

        if "sip_token_auth" in desired_inbound:
            current_auth = current_inbound.get("sip_token_auth") or {}
            required = current is None or rotate or not current_auth.get("enabled")
            if not required:
                return False
            secret = getpass(f"SIP token for {local_name}: ")
            if not secret:
                raise ValueError(f"A SIP token is required for trunk '{local_name}'.")
            desired_inbound["sip_token_auth"]["token"] = secret
            return True

        if rotate:
            raise ValueError(
                f"SIP trunk '{local_name}' must declare digest or token authentication "
                "to rotate credentials."
            )
        return False

    @staticmethod
    def _managed_agent_data(local_name: str, config: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(config, dict):
            raise ValueError(f"Extension '{local_name}' must contain a mapping.")
        missing = [field for field in ("agent_id", "client_env") if not config.get(field)]
        if missing:
            raise ValueError(
                f"Extension '{local_name}' is missing required field(s): {', '.join(missing)}"
            )
        if config["client_env"] not in {"sandbox", "pre-release", "live"}:
            raise ValueError(
                f"Extension '{local_name}' client_env must be sandbox, pre-release, or live."
            )
        agent = {"agent_id": config["agent_id"], "client_env": config["client_env"]}
        if "variant_id" in config:
            agent["variant_id"] = config["variant_id"]
        return agent

    @classmethod
    def _normalized_extensions(cls, desired_extensions: Any) -> list[dict[str, Any]] | None:
        """Validate and normalize extension configuration without making API calls."""
        if desired_extensions is None:
            return None
        if isinstance(desired_extensions, dict):
            desired_extensions = [
                {"extension": extension, **config}
                for extension, config in desired_extensions.items()
                if isinstance(config, dict)
            ]
        if not isinstance(desired_extensions, list) or not all(
            isinstance(config, dict) for config in desired_extensions
        ):
            raise ValueError("'extensions' must be a list of extension mappings.")

        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for extension_config in desired_extensions:
            if "extension" not in extension_config:
                raise ValueError("Each extension needs an 'extension' value.")
            extension = str(extension_config["extension"])
            if extension in seen:
                raise ValueError(f"Extension '{extension}' is declared more than once.")
            seen.add(extension)
            normalized.append(
                {
                    "extension": extension,
                    "agent": cls._managed_agent_data(extension, extension_config),
                }
            )
        return normalized

    @staticmethod
    def _trunk_patch(
        current: dict[str, Any], desired: dict[str, Any], *, secret_supplied: bool
    ) -> dict[str, Any]:
        patch: dict[str, Any] = {}
        for field in ("name", "sip_cidr", "rtp_cidr", "encrypted"):
            if field in desired and current.get(field) != desired[field]:
                patch[field] = desired[field]

        if desired.get("_disable_auth"):
            current_inbound = current.get("inbound") or {}
            if (current_inbound.get("sip_auth") or {}).get("enabled"):
                patch["inbound"] = {"sip_auth": {"disable": True}}
            elif (current_inbound.get("sip_token_auth") or {}).get("enabled"):
                patch["inbound"] = {"sip_token_auth": {"disable": True}}
            return patch

        desired_inbound = desired.get("inbound")
        if desired_inbound:
            current_inbound = current.get("inbound") or {}
            if "sip_auth" in desired_inbound:
                desired_auth = desired_inbound["sip_auth"]
                current_auth = current_inbound.get("sip_auth") or {}
                if (
                    secret_supplied
                    or not current_auth.get("enabled")
                    or (
                        "username" in desired_auth
                        and current_auth.get("username") != desired_auth["username"]
                    )
                ):
                    patch["inbound"] = desired_inbound
            elif "sip_token_auth" in desired_inbound:
                current_auth = current_inbound.get("sip_token_auth") or {}
                if secret_supplied or not current_auth.get("enabled"):
                    patch["inbound"] = desired_inbound
        return patch

    @classmethod
    def _manage_extensions(
        cls,
        region: str,
        account_id: str,
        trunk_id: str,
        desired_extensions: Any,
    ) -> tuple[int, int, int, int]:
        normalized = cls._normalized_extensions(desired_extensions)
        if normalized is None:
            return 0, 0, 0, 0

        response = SIPTrunkingAPIHandler.list_extensions(region, account_id, trunk_id)
        existing_items = response.get("extensions", [])
        if not isinstance(existing_items, list):
            raise ValueError("Expected the SIP Trunking API to return an extensions list.")
        existing = {str(item.get("extension")): item for item in existing_items}

        created = 0
        updated = 0
        desired_numbers: set[str] = set()
        for extension_config in normalized:
            extension = extension_config["extension"]
            desired_numbers.add(extension)
            desired_agent = extension_config["agent"]
            current = existing.get(extension)
            if current is None:
                SIPTrunkingAPIHandler.create_extension(
                    region,
                    account_id,
                    trunk_id,
                    {"extension": extension, "agent": desired_agent},
                )
                created += 1
                continue

            current_agent = current.get("agent") or {}
            comparable_current = {
                "agent_id": current_agent.get("agent_id"),
                "client_env": current_agent.get("client_env"),
            }
            comparable_desired = {
                "agent_id": desired_agent["agent_id"],
                "client_env": desired_agent["client_env"],
            }
            if "variant_id" in desired_agent:
                comparable_current["variant_id"] = current_agent.get("variant_id") or ""
                comparable_desired["variant_id"] = desired_agent["variant_id"] or ""
            if comparable_current != comparable_desired:
                SIPTrunkingAPIHandler.update_extension(
                    region,
                    account_id,
                    trunk_id,
                    extension,
                    {"agent": desired_agent},
                )
                updated += 1

        deleted = 0
        for extension in sorted(existing.keys() - desired_numbers):
            SIPTrunkingAPIHandler.delete_extension(region, account_id, trunk_id, extension)
            deleted += 1
        return len(normalized), created, updated, deleted

    @staticmethod
    def _auth_type(inbound: dict[str, Any]) -> str:
        if (inbound.get("sip_auth") or {}).get("enabled"):
            return "digest"
        if (inbound.get("sip_token_auth") or {}).get("enabled"):
            return "token"
        return "none"

    @classmethod
    def _preview_manage(cls, args: Namespace) -> list[dict[str, str]]:
        """Validate and calculate changes without prompting or writing anything."""
        config_path, region, account_id, desired_trunks = cls._load_manage_config(args)
        rotate_auth = getattr(args, "rotate_auth", None)
        if rotate_auth and not any(trunk.get("id") == rotate_auth for trunk in desired_trunks):
            raise ValueError(
                f"Cannot rotate SIP trunk '{rotate_auth}': its ID is not declared in "
                f"{config_path}."
            )

        response = SIPTrunkingAPIHandler.list_trunks(region, account_id)
        existing_items = response.get("sip_trunks", [])
        if not isinstance(existing_items, list):
            raise ValueError("Expected the SIP Trunking API to return a sip_trunks list.")
        by_id = {item.get("id"): item for item in existing_items if item.get("id")}
        by_name: dict[str, list[dict[str, Any]]] = {}
        for item in existing_items:
            by_name.setdefault(str(item.get("name")), []).append(item)

        changes: list[dict[str, str]] = []
        for index, trunk_config in enumerate(desired_trunks):
            local_name = str(
                trunk_config.get("id") or trunk_config.get("name") or f"sip_trunks[{index}]"
            )
            desired, _ = cls._managed_trunk_data(local_name, trunk_config, create=False)
            normalized_extensions = cls._normalized_extensions(trunk_config.get("extensions"))
            configured_id = trunk_config.get("id")
            current = by_id.get(configured_id) if configured_id else None
            if configured_id and current is None:
                raise ValueError(
                    f"SIP trunk '{local_name}' references unknown remote ID '{configured_id}'."
                )
            if current is None:
                matches = by_name.get(str(desired["name"]), [])
                if len(matches) > 1:
                    raise ValueError(
                        f"Multiple remote SIP trunks are named '{desired['name']}'; add an id "
                        f"to '{local_name}' in sip-trunks.yaml."
                    )
                current = matches[0] if matches else None

            if current is None:
                cls._managed_trunk_data(local_name, trunk_config, create=True)
                changes.append(
                    {"action": "create", "resource": f"trunk {desired['name']}", "diff": "+ trunk"}
                )
                for extension in normalized_extensions or []:
                    agent = extension["agent"]
                    changes.append(
                        {
                            "action": "create",
                            "resource": f"extension {extension['extension']}",
                            "diff": (
                                f"+ {agent['agent_id']} ({agent['client_env']})"
                                + (
                                    f", variant {agent['variant_id']}"
                                    if agent.get("variant_id")
                                    else ""
                                )
                            ),
                        }
                    )
                continue

            patch = cls._trunk_patch(current, desired, secret_supplied=False)
            for field, value in patch.items():
                if field == "inbound":
                    old_value = cls._auth_type(current.get("inbound") or {})
                    if desired.get("_disable_auth"):
                        new_value = "none"
                    elif "sip_auth" in (desired.get("inbound") or {}):
                        new_value = "digest"
                    else:
                        new_value = "token"
                    desired_auth = (desired.get("inbound") or {}).get("sip_auth") or {}
                    current_auth = (current.get("inbound") or {}).get("sip_auth") or {}
                    if (
                        old_value == new_value == "digest"
                        and current_auth.get("username") != desired_auth.get("username")
                    ):
                        detail = (
                            f"digest username: {current_auth.get('username')!r} -> "
                            f"{desired_auth.get('username')!r} (credential required)"
                        )
                    else:
                        detail = f"authentication: {old_value} -> {new_value}"
                else:
                    detail = f"{field}: {current.get(field)!r} -> {value!r}"
                changes.append(
                    {"action": "update", "resource": f"trunk {current['id']}", "diff": detail}
                )

            if rotate_auth == current.get("id"):
                desired_inbound = desired.get("inbound") or {}
                if not desired_inbound:
                    raise ValueError(
                        f"SIP trunk '{local_name}' must declare digest or token authentication "
                        "to rotate credentials."
                    )
                changes.append(
                    {
                        "action": "rotate",
                        "resource": f"trunk {current['id']}",
                        "diff": "~ authentication credential (value hidden)",
                    }
                )

            inbound = current.get("inbound") or {}
            metadata = {
                "id": current.get("id"),
                "hostname": inbound.get("hostname"),
            }
            for field, value in metadata.items():
                if value is not None and trunk_config.get(field) != value:
                    changes.append(
                        {
                            "action": "write YAML",
                            "resource": f"trunk {current['id']}",
                            "diff": f"{field}: {trunk_config.get(field)!r} -> {value!r}",
                        }
                    )
            inbound_auth = trunk_config.get("inbound_auth")
            realm = (inbound.get("sip_auth") or {}).get("realm")
            if (
                isinstance(inbound_auth, dict)
                and inbound_auth.get("type") == "digest"
                and realm is not None
                and inbound_auth.get("realm") != realm
            ):
                changes.append(
                    {
                        "action": "write YAML",
                        "resource": f"trunk {current['id']}",
                        "diff": f"realm: {inbound_auth.get('realm')!r} -> {realm!r}",
                    }
                )

            if normalized_extensions is None:
                continue
            extension_response = SIPTrunkingAPIHandler.list_extensions(
                region, account_id, current["id"]
            )
            existing_extensions = extension_response.get("extensions", [])
            if not isinstance(existing_extensions, list):
                raise ValueError("Expected the SIP Trunking API to return an extensions list.")
            by_extension = {
                str(item.get("extension")): item for item in existing_extensions
            }
            desired_numbers = {extension["extension"] for extension in normalized_extensions}
            for extension in normalized_extensions:
                number = extension["extension"]
                desired_agent = extension["agent"]
                existing = by_extension.get(number)
                if existing is None:
                    changes.append(
                        {
                            "action": "create",
                            "resource": f"extension {number}",
                            "diff": f"+ {desired_agent['agent_id']} ({desired_agent['client_env']})",
                        }
                    )
                    continue
                current_agent = existing.get("agent") or {}
                comparable_current = {
                    "agent_id": current_agent.get("agent_id"),
                    "client_env": current_agent.get("client_env"),
                }
                comparable_desired = {
                    "agent_id": desired_agent["agent_id"],
                    "client_env": desired_agent["client_env"],
                }
                if "variant_id" in desired_agent:
                    comparable_current["variant_id"] = current_agent.get("variant_id") or ""
                    comparable_desired["variant_id"] = desired_agent["variant_id"] or ""
                if comparable_current != comparable_desired:
                    changes.append(
                        {
                            "action": "update",
                            "resource": f"extension {number}",
                            "diff": f"agent: {comparable_current!r} -> {comparable_desired!r}",
                        }
                    )
            for number in sorted(by_extension.keys() - desired_numbers):
                changes.append(
                    {
                        "action": "delete",
                        "resource": f"extension {number}",
                        "diff": f"- from trunk {current['id']}",
                    }
                )
        return changes

    @staticmethod
    def _print_manage_diff(changes: list[dict[str, str]]) -> None:
        from rich import box
        from rich.table import Table

        from poly.output.console import console

        table = Table(title="SIP trunk changes", box=box.SIMPLE, header_style="bold")
        table.add_column("Action")
        table.add_column("Resource")
        table.add_column("Diff")
        for change in changes:
            table.add_row(change["action"], change["resource"], change["diff"])
        console.print(table)

    @classmethod
    def manage(cls, args: Namespace) -> dict[str, Any]:
        """Create or update YAML-declared trunks without deleting omitted resources."""
        config_path, region, account_id, desired_trunks = cls._load_manage_config(args)
        rotate_auth = getattr(args, "rotate_auth", None)
        if rotate_auth and not any(trunk.get("id") == rotate_auth for trunk in desired_trunks):
            raise ValueError(
                f"Cannot rotate SIP trunk '{rotate_auth}': its ID is not declared in "
                f"{config_path}."
            )
        response = SIPTrunkingAPIHandler.list_trunks(region, account_id)
        existing_items = response.get("sip_trunks", [])
        if not isinstance(existing_items, list):
            raise ValueError("Expected the SIP Trunking API to return a sip_trunks list.")

        by_id = {item.get("id"): item for item in existing_items if item.get("id")}
        by_name: dict[str, list[dict[str, Any]]] = {}
        for item in existing_items:
            by_name.setdefault(str(item.get("name")), []).append(item)

        results: list[dict[str, Any]] = []
        for index, trunk_config in enumerate(desired_trunks):
            local_name = str(
                trunk_config.get("id") or trunk_config.get("name") or f"sip_trunks[{index}]"
            )
            desired, secret_supplied = cls._managed_trunk_data(
                local_name, trunk_config, create=False
            )
            configured_id = trunk_config.get("id")
            current = by_id.get(configured_id) if configured_id else None
            if configured_id and current is None:
                raise ValueError(
                    f"SIP trunk '{local_name}' references unknown remote ID '{configured_id}'."
                )
            if current is None:
                matches = by_name.get(str(desired["name"]), [])
                if len(matches) > 1:
                    raise ValueError(
                        f"Multiple remote SIP trunks are named '{desired['name']}'; add an id "
                        f"to '{local_name}' in sip-trunks.yaml."
                    )
                current = matches[0] if matches else None

            if current is None:
                create_data, _ = cls._managed_trunk_data(local_name, trunk_config, create=True)
                create_data.pop("_disable_auth", None)
                cls._prompt_auth_secret(
                    local_name,
                    None,
                    create_data,
                    rotate=False,
                )
                current = SIPTrunkingAPIHandler.create_trunk(region, account_id, create_data)
                created_id = current.get("id")
                if not created_id:
                    raise ValueError(
                        f"Created SIP trunk '{local_name}', but the API returned no trunk ID."
                    )
                trunk_config["id"] = created_id
                status = "created"
            else:
                rotate = rotate_auth == current.get("id")
                secret_supplied = cls._prompt_auth_secret(
                    local_name,
                    current,
                    desired,
                    rotate=rotate,
                )
                patch = cls._trunk_patch(current, desired, secret_supplied=secret_supplied)
                if patch:
                    current = SIPTrunkingAPIHandler.update_trunk(
                        region, account_id, current["id"], patch
                    )
                    status = "updated"
                else:
                    status = "unchanged"

            metadata_updated = cls._persist_trunk_response(
                config_path, index, local_name, current
            )

            (
                extensions_total,
                extensions_created,
                extensions_updated,
                extensions_deleted,
            ) = cls._manage_extensions(
                region, account_id, current["id"], trunk_config.get("extensions")
            )
            if status == "unchanged" and (
                extensions_created or extensions_updated or extensions_deleted
            ):
                status = "updated"
            elif status == "unchanged" and metadata_updated:
                status = "metadata updated"
            results.append(
                {
                    "key": local_name,
                    "id": current.get("id"),
                    "name": current.get("name", desired["name"]),
                    "status": status,
                    "hostname": (current.get("inbound") or {}).get("hostname"),
                    "extensions_total": extensions_total,
                    "extensions_created": extensions_created,
                    "extensions_updated": extensions_updated,
                    "extensions_deleted": extensions_deleted,
                }
            )

        return {
            "success": True,
            "config_file": config_path,
            "account_id": account_id,
            "region": region,
            "trunks": results,
        }

    @classmethod
    def export_config(cls, region: str, account_id: str) -> dict[str, Any]:
        """Build reusable YAML configuration from all live account trunks."""
        response = SIPTrunkingAPIHandler.list_trunks(region, account_id)
        trunks = response.get("sip_trunks", [])
        if not isinstance(trunks, list):
            raise ValueError("Expected the SIP Trunking API to return a sip_trunks list.")

        exported: list[dict[str, Any]] = []
        for trunk in trunks:
            trunk_id = trunk.get("id")
            if not trunk_id:
                raise ValueError("A SIP trunk returned by the API is missing its ID.")
            config: dict[str, Any] = {
                "id": trunk_id,
                "name": trunk.get("name"),
                "sip_cidr": trunk.get("sip_cidr", []),
                "rtp_cidr": trunk.get("rtp_cidr", []),
                "encrypted": trunk.get("encrypted", True),
            }
            inbound = trunk.get("inbound") or {}
            hostname = inbound.get("hostname")
            if hostname:
                config["hostname"] = hostname
            sip_auth = inbound.get("sip_auth") or {}
            token_auth = inbound.get("sip_token_auth") or {}
            if sip_auth.get("enabled"):
                config["inbound_auth"] = {
                    "type": "digest",
                    "username": sip_auth.get("username"),
                }
                if sip_auth.get("realm") is not None:
                    config["inbound_auth"]["realm"] = sip_auth["realm"]
            elif token_auth.get("enabled"):
                # Tokens are intentionally never returned by the API.
                config["inbound_auth"] = {"type": "token"}
            else:
                config["inbound_auth"] = {"type": "none"}

            extension_response = SIPTrunkingAPIHandler.list_extensions(region, account_id, trunk_id)
            extension_items = extension_response.get("extensions", [])
            if not isinstance(extension_items, list):
                raise ValueError("Expected the SIP Trunking API to return an extensions list.")
            config["extensions"] = [
                {
                    "extension": str(item["extension"]),
                    **{
                        key: value
                        for key, value in (item.get("agent") or {}).items()
                        if key in {"agent_id", "client_env", "variant_id"}
                    },
                }
                for item in extension_items
            ]
            exported.append(config)

        return {"account_id": account_id, "sip_trunks": exported}

    @staticmethod
    def _yaml_string(data: Any) -> str:
        yaml = YAML()
        yaml.default_flow_style = False
        stream = StringIO()
        yaml.dump(data, stream)
        return stream.getvalue()

    @staticmethod
    def _default_export_path(args: Namespace, account_id: str) -> str:
        project = read_project_config(args.path)
        if project:
            return os.path.join(os.path.dirname(project.root_path), "sip-trunks.yaml")
        base_path = os.path.abspath(args.path)
        if os.path.basename(base_path) != account_id:
            base_path = os.path.join(base_path, account_id)
        return os.path.join(base_path, "sip-trunks.yaml")

    @classmethod
    def _write_export(cls, args: Namespace, account_id: str, data: dict[str, Any]) -> str:
        output_path = (
            cls._default_export_path(args, account_id)
            if args.output == "__account_default__"
            else os.path.abspath(args.output)
        )
        if os.path.exists(output_path) and not args.force:
            raise FileExistsError(
                f"Refusing to overwrite {output_path}. Pass --force to replace it."
            )
        parent = os.path.dirname(output_path)
        if not os.path.isdir(parent):
            raise FileNotFoundError(f"Output directory does not exist: {parent}")
        with open(output_path, "w", encoding="utf-8") as output_file:
            output_file.write(cls._yaml_string(data["sip_trunks"]))
        return output_path

    @staticmethod
    def _print_result(result: dict[str, Any], *, output_json: bool) -> None:
        if output_json:
            json_print(result)
            return
        from poly.output.console import console

        console.print_json(data=result)

    @staticmethod
    def _print_manage_result(result: dict[str, Any], *, output_json: bool) -> None:
        if output_json:
            json_print(result)
            return
        from rich import box
        from rich.table import Table

        from poly.output.console import console, info

        changed_trunks = [trunk for trunk in result["trunks"] if trunk["status"] != "unchanged"]
        if not changed_trunks:
            info("Nothing changed.")
            return

        info(f"Managed SIP trunks from {result['config_file']}")
        table = Table(box=box.SIMPLE, header_style="bold")
        table.add_column("Key")
        table.add_column("Status")
        table.add_column("Trunk ID")
        table.add_column("Hostname")
        table.add_column("Extensions")
        table.add_column("Changes")
        for trunk in changed_trunks:
            extension_changes = (
                trunk["extensions_created"]
                + trunk["extensions_updated"]
                + trunk.get("extensions_deleted", 0)
            )
            table.add_row(
                trunk["key"],
                trunk["status"],
                trunk["id"] or "—",
                trunk["hostname"] or "—",
                str(trunk["extensions_total"]),
                str(extension_changes),
            )
        console.print(table)

    @staticmethod
    def _auth_summary(inbound: dict[str, Any]) -> str:
        sip_auth = inbound.get("sip_auth") or {}
        token_auth = inbound.get("sip_token_auth") or {}
        if sip_auth.get("enabled"):
            username = sip_auth.get("username")
            return f"digest ({username})" if username else "digest"
        if token_auth.get("enabled"):
            return "token"
        return "none"

    @classmethod
    def _print_list_table(cls, config: dict[str, Any]) -> None:
        from rich import box
        from rich.table import Table

        from poly.output.console import console

        table = Table(box=box.SIMPLE, header_style="bold")
        table.add_column("Name")
        table.add_column("Trunk ID")
        table.add_column("Hostname")
        table.add_column("Encrypted")
        table.add_column("Auth")
        table.add_column("Extensions", justify="right")
        for trunk in config["sip_trunks"]:
            auth = trunk.get("inbound_auth") or {"type": "none"}
            auth_summary = str(auth.get("type", "none"))
            if auth_summary == "digest" and auth.get("username"):
                auth_summary += f" ({auth['username']})"
            table.add_row(
                trunk.get("name") or "—",
                trunk.get("id") or "—",
                trunk.get("hostname") or "—",
                "yes" if trunk.get("encrypted") else "no",
                auth_summary,
                str(len(trunk.get("extensions") or [])),
            )
        console.print(table)

    @classmethod
    def _print_get_table(cls, trunk: dict[str, Any], extensions: list[dict[str, Any]]) -> None:
        from rich import box
        from rich.table import Table

        from poly.output.console import console

        inbound = trunk.get("inbound") or {}
        details = Table(box=box.SIMPLE, show_header=False)
        details.add_column("Field", style="bold")
        details.add_column("Value")
        details.add_row("Name", str(trunk.get("name") or "—"))
        details.add_row("Trunk ID", str(trunk.get("id") or "—"))
        details.add_row("Hostname", str(inbound.get("hostname") or "—"))
        details.add_row("Encrypted", "yes" if trunk.get("encrypted") else "no")
        details.add_row("Authentication", cls._auth_summary(inbound))
        details.add_row("SIP CIDRs", ", ".join(trunk.get("sip_cidr") or []) or "—")
        details.add_row("RTP CIDRs", ", ".join(trunk.get("rtp_cidr") or []) or "—")
        details.add_row("Created", str(trunk.get("created_at") or "—"))
        details.add_row("Updated", str(trunk.get("updated_at") or "—"))
        console.print(details)

        extension_table = Table(
            title="Extensions", box=box.SIMPLE, header_style="bold", title_justify="left"
        )
        extension_table.add_column("Extension")
        extension_table.add_column("Agent ID")
        extension_table.add_column("Environment")
        extension_table.add_column("Variant")
        for extension in extensions:
            agent = extension.get("agent") or {}
            extension_table.add_row(
                str(extension.get("extension") or "—"),
                str(agent.get("agent_id") or "—"),
                str(agent.get("client_env") or "—"),
                str(agent.get("variant_id") or "—"),
            )
        console.print(extension_table)

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to a SIP trunk API operation."""
        action = args.sip_trunks_subcommand
        if action == "manage":
            changes = cls._preview_manage(args)
            if not changes:
                if args.json:
                    json_print({"success": True, "changed": False, "trunks": []})
                else:
                    from poly.output.console import info

                    info("Nothing changed.")
                return
            if args.json and not args.yes:
                raise ValueError("sip-trunks manage --json requires --yes when changes exist.")
            if not args.json:
                cls._print_manage_diff(changes)
            if not args.yes:
                import questionary

                confirmed = questionary.confirm(
                    "Apply these SIP trunk changes?", default=False, auto_enter=False
                ).ask()
                if not confirmed:
                    from poly.output.console import info

                    info("Aborted. No changes were applied.")
                    return
            result = cls.manage(args)
            cls._print_manage_result(result, output_json=args.json)
            return

        region, account_id = cls._resolve_context(args)
        if action == "list":
            result = cls.export_config(region, account_id)
            if args.output:
                output_path = cls._write_export(args, account_id, result)
                if args.json:
                    json_print(
                        {
                            "success": True,
                            "output_path": output_path,
                            "trunk_count": len(result["sip_trunks"]),
                        }
                    )
                else:
                    from poly.output.console import success

                    success(f"Wrote {len(result['sip_trunks'])} SIP trunk(s) to {output_path}")
            elif args.json:
                json_print(result)
            else:
                cls._print_list_table(result)
            return
        elif action == "get":
            result = SIPTrunkingAPIHandler.get_trunk(region, account_id, args.trunk_id)
            if not args.json:
                extension_response = SIPTrunkingAPIHandler.list_extensions(
                    region, account_id, args.trunk_id
                )
                extensions = extension_response.get("extensions", [])
                if not isinstance(extensions, list):
                    raise ValueError("Expected the SIP Trunking API to return an extensions list.")
                cls._print_get_table(result, extensions)
                return
        else:
            SIPTrunkingAPIHandler.delete_trunk(region, account_id, args.trunk_id)
            result = {"success": True, "trunk_id": args.trunk_id}

        cls._print_result(result, output_json=args.json)
