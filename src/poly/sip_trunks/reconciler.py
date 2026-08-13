"""Plan and apply account-level SIP trunk reconciliation.

Copyright PolyAI Limited
"""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Literal, Protocol

from poly.handlers.sip_trunking_api import SIPTrunkingAPIHandler
from poly.sip_trunks.config import file_digest


@dataclass(frozen=True)
class PlanChange:
    """One user-visible change in a SIP trunk management plan."""

    action: str
    resource: str
    diff: str

    def as_dict(self) -> dict[str, str]:
        """Return the shape used by JSON and table output."""
        return {
            "action": self.action,
            "resource": self.resource,
            "diff": self.diff,
        }


@dataclass(frozen=True)
class ExtensionOperation:
    """A previously compared extension mutation."""

    action: Literal["create", "update", "delete"]
    extension: str
    payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class TrunkOperation:
    """A previously compared trunk mutation and its extension operations."""

    config_index: int
    local_name: str
    desired: dict[str, Any]
    current: dict[str, Any] | None
    action: Literal["create", "update", "unchanged"]
    payload: dict[str, Any]
    credential_required: bool
    rotate_auth: bool
    extensions_total: int
    extension_operations: tuple[ExtensionOperation, ...]


@dataclass(frozen=True)
class ManagePlan:
    """A single remote-state snapshot that can be previewed and then applied."""

    config_path: str
    region: str
    account_id: str
    trunks: tuple[TrunkOperation, ...]
    changes: tuple[PlanChange, ...]
    source_digest: str | None = None


class AuthPrompt(Protocol):
    """Secret callback implemented by the interactive CLI layer."""

    def __call__(
        self,
        local_name: str,
        current: dict[str, Any] | None,
        desired: dict[str, Any],
        *,
        rotate: bool,
    ) -> bool: ...


def reject_yaml_secret(config: dict[str, Any], field: str) -> None:
    """Reject secrets and environment-variable references in managed YAML."""
    for key in (field, f"{field}_env"):
        if key in config:
            raise ValueError(
                f"Do not store '{key}' in sip-trunks.yaml; credentials are prompted "
                "only when they are required."
            )


def managed_trunk_data(
    local_name: str, config: dict[str, Any], *, create: bool
) -> tuple[dict[str, Any], bool]:
    """Translate one YAML trunk entry to a secret-free API payload."""
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

    inbound_auth = config.get("inbound_auth")
    if inbound_auth is not None:
        if not isinstance(inbound_auth, dict):
            raise ValueError(f"SIP trunk '{local_name}' inbound_auth must be a mapping.")
        reject_yaml_secret(inbound_auth, "password")
        reject_yaml_secret(inbound_auth, "token")
        auth_type = inbound_auth.get("type")
        if auth_type == "none":
            data["_disable_auth"] = True
        elif auth_type == "digest":
            username = inbound_auth.get("username")
            if not username:
                raise ValueError(f"SIP trunk '{local_name}' digest auth requires a username.")
            data["inbound"] = {"sip_auth": {"username": username}}
        elif auth_type == "token":
            data["inbound"] = {"sip_token_auth": {}}
        else:
            raise ValueError(
                f"SIP trunk '{local_name}' inbound_auth.type must be digest, token, or none."
            )
    else:
        # Backwards-compatible reader for the initial preview schema.
        inbound = config.get("inbound")
        if inbound is not None:
            if not isinstance(inbound, dict):
                raise ValueError(
                    f"SIP trunk '{local_name}' inbound configuration must be a mapping."
                )
            reject_yaml_secret(inbound, "password")
            reject_yaml_secret(inbound, "token")
            digest = inbound.get("sip_auth")
            token_auth = inbound.get("sip_token_auth")
            if digest is not None and token_auth is not None:
                raise ValueError(
                    f"SIP trunk '{local_name}' cannot use SIP digest and token auth together."
                )
            if digest is not None:
                if not isinstance(digest, dict):
                    raise ValueError("'sip_auth' must be a mapping.")
                reject_yaml_secret(digest, "password")
                reject_yaml_secret(digest, "token")
                username = digest.get("username")
                if not username:
                    raise ValueError(f"SIP trunk '{local_name}' digest auth requires a username.")
                data["inbound"] = {"sip_auth": {"username": username}}
            elif token_auth is not None:
                if not isinstance(token_auth, dict):
                    raise ValueError("'sip_token_auth' must be a mapping.")
                reject_yaml_secret(token_auth, "password")
                reject_yaml_secret(token_auth, "token")
                data["inbound"] = {"sip_token_auth": {}}
    # Kept in the return type for compatibility with the original helper. YAML
    # secrets are always rejected, so this is necessarily false during planning.
    return data, False


def managed_agent_data(local_name: str, config: dict[str, Any]) -> dict[str, Any]:
    """Validate and translate an extension's agent target."""
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


def normalized_extensions(desired_extensions: Any) -> list[dict[str, Any]] | None:
    """Validate extensions, preserving omitted versus an authoritative empty list."""
    if desired_extensions is None:
        return None
    if isinstance(desired_extensions, dict):
        if not all(isinstance(config, dict) for config in desired_extensions.values()):
            raise ValueError("Every extension value must be a mapping.")
        desired_extensions = [
            {"extension": extension, **config} for extension, config in desired_extensions.items()
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
        raw_extension = extension_config["extension"]
        if (
            raw_extension is None
            or isinstance(raw_extension, bool)
            or (isinstance(raw_extension, str) and not raw_extension.strip())
        ):
            raise ValueError("Each extension needs a non-empty 'extension' value.")
        extension = str(raw_extension)
        if extension in seen:
            raise ValueError(f"Extension '{extension}' is declared more than once.")
        seen.add(extension)
        normalized.append(
            {
                "extension": extension,
                "agent": managed_agent_data(extension, extension_config),
            }
        )
    return normalized


def trunk_patch(
    current: dict[str, Any], desired: dict[str, Any], *, secret_supplied: bool
) -> dict[str, Any]:
    """Calculate a PATCH body without reading remote state again."""
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


def auth_type(inbound: dict[str, Any]) -> str:
    """Return the public auth type for an API inbound object."""
    if (inbound.get("sip_auth") or {}).get("enabled"):
        return "digest"
    if (inbound.get("sip_token_auth") or {}).get("enabled"):
        return "token"
    return "none"


def credential_required(
    current: dict[str, Any] | None,
    desired: dict[str, Any],
    *,
    rotate: bool,
) -> bool:
    """Return whether applying a desired auth state requires a new secret."""
    desired_inbound = desired.get("inbound")
    if not desired_inbound:
        if rotate:
            raise ValueError("Digest or token authentication must be declared to rotate it.")
        return False

    current_inbound = (current or {}).get("inbound") or {}
    if "sip_auth" in desired_inbound:
        current_auth = current_inbound.get("sip_auth") or {}
        desired_auth = desired_inbound["sip_auth"]
        return bool(
            current is None
            or rotate
            or not current_auth.get("enabled")
            or current_auth.get("username") != desired_auth.get("username")
        )
    if "sip_token_auth" in desired_inbound:
        current_auth = current_inbound.get("sip_token_auth") or {}
        return bool(current is None or rotate or not current_auth.get("enabled"))
    return False


def _comparable_agents(
    current_agent: dict[str, Any], desired_agent: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    current = {
        "agent_id": current_agent.get("agent_id"),
        "client_env": current_agent.get("client_env"),
    }
    desired = {
        "agent_id": desired_agent["agent_id"],
        "client_env": desired_agent["client_env"],
    }
    if "variant_id" in desired_agent:
        current["variant_id"] = current_agent.get("variant_id") or ""
        desired["variant_id"] = desired_agent["variant_id"] or ""
    return current, desired


def _extension_plan(
    normalized: list[dict[str, Any]],
    existing_items: list[dict[str, Any]],
    trunk_id: str,
) -> tuple[tuple[ExtensionOperation, ...], tuple[PlanChange, ...]]:
    existing: dict[str, dict[str, Any]] = {}
    for item in existing_items:
        if not isinstance(item, dict):
            raise ValueError("A SIP extension returned by the API is missing its extension.")
        returned_extension = item.get("extension")
        if returned_extension is None or returned_extension == "":
            raise ValueError("A SIP extension returned by the API is missing its extension.")
        extension = str(returned_extension)
        if extension in existing:
            raise ValueError(
                f"The SIP Trunking API returned extension '{extension}' more than once."
            )
        existing[extension] = item
    operations: list[ExtensionOperation] = []
    changes: list[PlanChange] = []
    desired_numbers: set[str] = set()

    for extension_config in normalized:
        extension = extension_config["extension"]
        desired_numbers.add(extension)
        desired_agent = extension_config["agent"]
        current = existing.get(extension)
        if current is None:
            operations.append(
                ExtensionOperation(
                    "create",
                    extension,
                    {"extension": extension, "agent": desired_agent},
                )
            )
            variant = (
                f", variant {desired_agent['variant_id']}"
                if desired_agent.get("variant_id")
                else ""
            )
            changes.append(
                PlanChange(
                    "create",
                    f"extension {extension}",
                    f"+ {desired_agent['agent_id']} ({desired_agent['client_env']}){variant}",
                )
            )
            continue

        current_agent, comparable_desired = _comparable_agents(
            current.get("agent") or {}, desired_agent
        )
        if current_agent != comparable_desired:
            operations.append(ExtensionOperation("update", extension, {"agent": desired_agent}))
            changes.append(
                PlanChange(
                    "update",
                    f"extension {extension}",
                    f"agent: {current_agent!r} -> {comparable_desired!r}",
                )
            )

    for extension in sorted(existing.keys() - desired_numbers):
        operations.append(ExtensionOperation("delete", extension))
        changes.append(PlanChange("delete", f"extension {extension}", f"- from trunk {trunk_id}"))
    return tuple(operations), tuple(changes)


def _trunk_changes(
    current: dict[str, Any], desired: dict[str, Any], patch: dict[str, Any]
) -> list[PlanChange]:
    changes: list[PlanChange] = []
    for field, value in patch.items():
        if field == "inbound":
            old_value = auth_type(current.get("inbound") or {})
            if desired.get("_disable_auth"):
                new_value = "none"
            elif "sip_auth" in (desired.get("inbound") or {}):
                new_value = "digest"
            else:
                new_value = "token"
            desired_auth = (desired.get("inbound") or {}).get("sip_auth") or {}
            current_auth = (current.get("inbound") or {}).get("sip_auth") or {}
            if old_value == new_value == "digest" and current_auth.get(
                "username"
            ) != desired_auth.get("username"):
                detail = (
                    f"digest username: {current_auth.get('username')!r} -> "
                    f"{desired_auth.get('username')!r} (credential required)"
                )
            else:
                detail = f"authentication: {old_value} -> {new_value}"
        else:
            detail = f"{field}: {current.get(field)!r} -> {value!r}"
        changes.append(PlanChange("update", f"trunk {current['id']}", detail))
    return changes


def _metadata_changes(trunk_config: dict[str, Any], current: dict[str, Any]) -> list[PlanChange]:
    changes: list[PlanChange] = []
    inbound = current.get("inbound") or {}
    metadata = {"id": current.get("id"), "hostname": inbound.get("hostname")}
    for field, value in metadata.items():
        if value is not None and trunk_config.get(field) != value:
            changes.append(
                PlanChange(
                    "write YAML",
                    f"trunk {current['id']}",
                    f"{field}: {trunk_config.get(field)!r} -> {value!r}",
                )
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
            PlanChange(
                "write YAML",
                f"trunk {current['id']}",
                f"realm: {inbound_auth.get('realm')!r} -> {realm!r}",
            )
        )
    return changes


def build_manage_plan(
    config_path: str,
    region: str,
    account_id: str,
    desired_trunks: list[dict[str, Any]],
    *,
    rotate_auth: str | None = None,
    source_digest: str | None = None,
) -> ManagePlan:
    """Read remote state once and construct the exact operations to apply."""
    if rotate_auth and not any(trunk.get("id") == rotate_auth for trunk in desired_trunks):
        raise ValueError(
            f"Cannot rotate SIP trunk '{rotate_auth}': its ID is not declared in {config_path}."
        )

    # Validate every local declaration before making any remote request.
    validated: list[
        tuple[int, dict[str, Any], str, dict[str, Any], list[dict[str, Any]] | None]
    ] = []
    declared_ids: set[str] = set()
    declared_names: list[tuple[str, bool]] = []
    for index, trunk_config in enumerate(desired_trunks):
        local_name = str(
            trunk_config.get("id") or trunk_config.get("name") or f"sip_trunks[{index}]"
        )
        desired, _ = managed_trunk_data(local_name, trunk_config, create=False)
        extensions = normalized_extensions(trunk_config.get("extensions"))
        configured_id = trunk_config.get("id")
        if configured_id:
            normalized_id = str(configured_id)
            if normalized_id in declared_ids:
                raise ValueError(f"SIP trunk ID '{normalized_id}' is declared more than once.")
            declared_ids.add(normalized_id)
        declared_names.append((str(desired["name"]), not bool(configured_id)))
        validated.append((index, trunk_config, local_name, desired, extensions))

    name_counts: dict[str, int] = {}
    for name, _ in declared_names:
        name_counts[name] = name_counts.get(name, 0) + 1
    ambiguous_name = next(
        (name for name, idless in declared_names if idless and name_counts[name] > 1), None
    )
    if ambiguous_name is not None:
        raise ValueError(
            f"SIP trunk name '{ambiguous_name}' is declared more than once without an ID."
        )

    response = SIPTrunkingAPIHandler.list_trunks(region, account_id)
    existing_items = response.get("sip_trunks", [])
    if not isinstance(existing_items, list):
        raise ValueError("Expected the SIP Trunking API to return a sip_trunks list.")
    if not all(isinstance(item, dict) for item in existing_items):
        raise ValueError("Expected each SIP trunk returned by the API to be a mapping.")
    by_id = {item.get("id"): item for item in existing_items if item.get("id")}
    by_name: dict[str, list[dict[str, Any]]] = {}
    for item in existing_items:
        by_name.setdefault(str(item.get("name")), []).append(item)

    operations: list[TrunkOperation] = []
    changes: list[PlanChange] = []
    claimed_remote_ids: set[str] = set()
    for index, trunk_config, local_name, desired, extensions in validated:
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

        rotate = bool(current and rotate_auth == current.get("id"))
        if rotate and not desired.get("inbound"):
            raise ValueError(
                f"SIP trunk '{local_name}' must declare digest or token authentication "
                "to rotate credentials."
            )
        if current is None:
            create_data, _ = managed_trunk_data(local_name, trunk_config, create=True)
            create_data.pop("_disable_auth", None)
            needs_credential = credential_required(None, create_data, rotate=False)
            extension_operations, extension_changes = _extension_plan(
                extensions or [], [], "new trunk"
            )
            trunk_change = PlanChange("create", f"trunk {desired['name']}", "+ trunk")
            changes.append(trunk_change)
            changes.extend(extension_changes)
            operations.append(
                TrunkOperation(
                    config_index=index,
                    local_name=local_name,
                    desired=create_data,
                    current=None,
                    action="create",
                    payload=create_data,
                    credential_required=needs_credential,
                    rotate_auth=False,
                    extensions_total=len(extensions or []),
                    extension_operations=extension_operations,
                )
            )
            continue

        current_id = current.get("id")
        if not current_id:
            raise ValueError(f"Remote SIP trunk '{desired['name']}' is missing its ID.")
        current_id = str(current_id)
        if current_id in claimed_remote_ids:
            raise ValueError(f"SIP trunk '{current_id}' is targeted by more than one YAML entry.")
        claimed_remote_ids.add(current_id)
        needs_credential = credential_required(current, desired, rotate=rotate)
        patch = trunk_patch(current, desired, secret_supplied=False)
        changes.extend(_trunk_changes(current, desired, patch))
        if rotate:
            changes.append(
                PlanChange(
                    "rotate",
                    f"trunk {current_id}",
                    "~ authentication credential (value hidden)",
                )
            )
        changes.extend(_metadata_changes(trunk_config, current))

        if extensions is None:
            extension_operations: tuple[ExtensionOperation, ...] = ()
            extension_changes: tuple[PlanChange, ...] = ()
            extensions_total = 0
        else:
            extension_response = SIPTrunkingAPIHandler.list_extensions(
                region, account_id, current_id
            )
            existing_extensions = extension_response.get("extensions", [])
            if not isinstance(existing_extensions, list):
                raise ValueError("Expected the SIP Trunking API to return an extensions list.")
            extension_operations, extension_changes = _extension_plan(
                extensions, existing_extensions, current_id
            )
            extensions_total = len(extensions)
            changes.extend(extension_changes)

        action: Literal["update", "unchanged"] = (
            "update" if patch or needs_credential else "unchanged"
        )
        operations.append(
            TrunkOperation(
                config_index=index,
                local_name=local_name,
                desired=desired,
                current=current,
                action=action,
                payload=patch,
                credential_required=needs_credential,
                rotate_auth=rotate,
                extensions_total=extensions_total,
                extension_operations=extension_operations,
            )
        )

    return ManagePlan(
        config_path=config_path,
        region=region,
        account_id=account_id,
        trunks=tuple(operations),
        changes=tuple(changes),
        source_digest=source_digest,
    )


def apply_manage_plan(
    plan: ManagePlan,
    *,
    prompt_auth_secret: AuthPrompt,
    persist_trunk_response: Callable[[str, int, str, dict[str, Any]], bool],
) -> dict[str, Any]:
    """Apply stored operations without rediscovering or recomparing remote state."""

    def ensure_source_unchanged() -> None:
        if plan.source_digest and file_digest(plan.config_path) != plan.source_digest:
            raise ValueError(
                f"{plan.config_path} changed after the SIP trunk preview. Run manage again "
                "to review the current file."
            )

    ensure_source_unchanged()

    # Collect all required credentials before the first remote or local write,
    # while keeping their values outside the printable plan.
    prepared: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for operation in plan.trunks:
        desired = deepcopy(operation.desired)
        payload = deepcopy(operation.payload)
        if operation.credential_required:
            secret_supplied = prompt_auth_secret(
                operation.local_name,
                operation.current,
                desired,
                rotate=operation.rotate_auth,
            )
            if not secret_supplied:
                raise ValueError(
                    f"A credential is required for SIP trunk '{operation.local_name}'."
                )
            payload["inbound"] = desired["inbound"]
        prepared.append((desired, payload))

    # A user may spend time entering multiple credentials. Recheck after the
    # prompts so an edit made during that interval cannot be applied unseen.
    ensure_source_unchanged()

    results: list[dict[str, Any]] = []
    for operation, (desired, payload) in zip(plan.trunks, prepared, strict=True):
        if operation.action == "create":
            current = SIPTrunkingAPIHandler.create_trunk(plan.region, plan.account_id, payload)
            if not current.get("id"):
                raise ValueError(
                    f"Created SIP trunk '{operation.local_name}', but the API returned no trunk ID."
                )
            status = "created"
        elif operation.action == "update":
            assert operation.current is not None
            current = SIPTrunkingAPIHandler.update_trunk(
                plan.region,
                plan.account_id,
                operation.current["id"],
                payload,
            )
            status = "updated"
        else:
            assert operation.current is not None
            current = operation.current
            status = "unchanged"

        metadata_updated = persist_trunk_response(
            plan.config_path,
            operation.config_index,
            operation.local_name,
            current,
        )
        trunk_id = current["id"]
        counts = {"create": 0, "update": 0, "delete": 0}
        for extension_operation in operation.extension_operations:
            if extension_operation.action == "create":
                assert extension_operation.payload is not None
                SIPTrunkingAPIHandler.create_extension(
                    plan.region,
                    plan.account_id,
                    trunk_id,
                    deepcopy(extension_operation.payload),
                )
            elif extension_operation.action == "update":
                assert extension_operation.payload is not None
                SIPTrunkingAPIHandler.update_extension(
                    plan.region,
                    plan.account_id,
                    trunk_id,
                    extension_operation.extension,
                    deepcopy(extension_operation.payload),
                )
            else:
                SIPTrunkingAPIHandler.delete_extension(
                    plan.region,
                    plan.account_id,
                    trunk_id,
                    extension_operation.extension,
                )
            counts[extension_operation.action] += 1

        if status == "unchanged" and any(counts.values()):
            status = "updated"
        elif status == "unchanged" and metadata_updated:
            status = "metadata updated"
        results.append(
            {
                "key": operation.local_name,
                "id": current.get("id"),
                "name": current.get("name", desired["name"]),
                "status": status,
                "hostname": (current.get("inbound") or {}).get("hostname"),
                "extensions_total": operation.extensions_total,
                "extensions_created": counts["create"],
                "extensions_updated": counts["update"],
                "extensions_deleted": counts["delete"],
            }
        )

    return {
        "success": True,
        "config_file": plan.config_path,
        "account_id": plan.account_id,
        "region": plan.region,
        "trunks": results,
    }


def export_config(region: str, account_id: str) -> dict[str, Any]:
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
