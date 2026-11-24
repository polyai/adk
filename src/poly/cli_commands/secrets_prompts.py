"""Interactive prompts for account secret metadata and write-only values.

Copyright PolyAI Limited
"""

from argparse import Namespace

import questionary
from questionary import Choice, Question

from poly.output.console import info, project_label
from poly.project import SecretUpdate


def _ask(question: Question):
    answer = question.ask()
    if answer is None:
        raise ValueError("Secret input cancelled.")
    return answer


def _secret_choices(records: list[dict]) -> list[Choice]:
    return [
        Choice(f"{record['display_name']} ({record['value_type']})", record["display_name"])
        for record in records
    ]


def pick_secret(records: list[dict]) -> str:
    """Pick an existing secret or enter an unused name once."""
    new = object()
    selected = _ask(
        questionary.select(
            "Secret", choices=[Choice("New secret…", new), *_secret_choices(records)]
        )
    )
    if selected is not new:
        return selected
    names = {record["display_name"] for record in records}
    return _ask(
        questionary.text(
            "New secret name",
            validate=lambda name: bool(name.strip())
            and name not in names
            or "Enter a nonempty, unused secret name.",
        )
    )


def pick_secrets_to_delete(records: list[dict]) -> list[str]:
    """Select zero or more account secrets to delete."""
    if not records:
        info("No account secrets to delete.")
        return []
    return _ask(questionary.checkbox("Select secrets to delete", choices=_secret_choices(records)))


def _pick_access(names: dict[str, str], current: list[str]) -> list[str]:
    ids = dict.fromkeys([*names, *current])
    if not ids:
        info("No projects are available to select.")
        return []
    choices = [
        Choice(project_label(pid, names), pid, checked=pid in current)
        for pid in sorted(ids, key=lambda pid: (names.get(pid, pid).casefold(), pid))
    ]
    return _ask(questionary.checkbox("Projects with access", choices=choices))


def prompt_fields(
    args: Namespace, existing: dict | None, names: dict[str, str], project_id: str
) -> bool:
    """Collect unspecified creation fields or the edits selected for an existing secret."""
    access_given = args.projects is not None or args.no_projects or args.grant or args.revoke
    if existing is None:
        if args.value_type is None:
            args.value_type = _ask(questionary.select("Type", choices=["single", "key-value"]))
        if args.description is None:
            args.description = _ask(questionary.text("Description (optional)"))
        if not access_given:
            selected = _pick_access(names, [project_id])
            if selected != [project_id]:
                args.projects = selected
        return True

    if (
        args.value_type
        or args.description is not None
        or access_given
        or args.replace_value
        or args.delete_keys
    ):
        return True
    fields = _ask(
        questionary.checkbox(
            "What do you want to change?",
            choices=[
                Choice("Value or type", "value"),
                Choice("Description", "description"),
                Choice("Project access", "access"),
            ],
        )
    )
    if "value" in fields:
        has_keys = existing["value_type"] == "key-value"
        target = "single" if has_keys else "key-value"
        keys = ", ".join(existing.get("keys") or [])
        replaced = f"keys {keys}" if keys else "the stored value"
        action = _ask(
            questionary.select(
                "How do you want to change the value?",
                choices=[
                    Choice("Edit keys" if has_keys else "Replace single value", "edit"),
                    Choice(f"Convert to {target} (replaces {replaced})", "convert"),
                ],
            )
        )
        if action == "convert":
            args.value_type = target
        else:
            args.replace_value = True
    if "description" in fields:
        current_description = existing.get("description") or ""
        description = _ask(questionary.text("Description", default=current_description))
        if description != current_description:
            args.description = description
    if "access" in fields:
        current = existing.get("access_config") or []
        selected = _pick_access(names, current)
        # Deltas leave existing grants to inaccessible or deleted projects intact.
        args.grant = [pid for pid in selected if pid not in current]
        args.revoke = [pid for pid in current if pid not in selected]
    return bool("value" in fields or args.description is not None or args.grant or args.revoke)


def _new_key_values() -> dict:
    values = {}
    while True:
        key = _ask(
            questionary.text(
                "Key (leave empty to finish)",
                validate=lambda key: (key not in values and bool(key or values))
                or "Enter a new key, or finish after adding a key.",
            )
        )
        if not key:
            return values
        values[key] = _ask(questionary.password(f"Value for {key}"))


def _edit_keys(update: SecretUpdate) -> dict | None:
    stored = set(update.existing.get("keys") or [])
    changes = {}
    while True:
        active = (
            (stored | changes.keys())
            - set(update.delete_keys)
            - {key for key, value in changes.items() if value is None}
        )
        choices = [Choice(f"Update {key}", ("update", key)) for key in sorted(active)]
        choices.append(Choice("Add a key", "add"))
        if active:
            choices.append(Choice("Delete keys…", "delete"))
        choices.append(Choice("Done", "done"))
        action = _ask(questionary.select("Keys", choices=choices))
        if action == "done":
            if not active and update.existing.get("keys") is not None:
                info("Keep at least one key. Add a key or restore one before finishing.")
                continue
            return changes or None
        if action == "delete":
            removed = _ask(questionary.checkbox("Keys to delete", choices=sorted(active)))
            for key in removed:
                if key in stored:
                    changes[key] = None
                else:
                    changes.pop(key)
            continue
        if action == "add":
            key = _ask(
                questionary.text(
                    "Key name",
                    validate=lambda key: bool(key)
                    and key not in active
                    and key not in update.delete_keys
                    or "Choose an unused key name or select the key to update it.",
                )
            )
        else:
            _, key = action
        changes[key] = _ask(questionary.password(f"Value for {key}"))


def prompt_value(update: SecretUpdate) -> str | dict | None:
    """Collect a hidden value or key changes without retrieving stored values."""
    if update.value_type == "single":
        return _ask(
            questionary.password(
                "Secret value", validate=lambda value: bool(value) or "Enter a value."
            )
        )
    if update.patches_keys:
        return _edit_keys(update)
    return _new_key_values()
