"""Rich console output helpers for the ADK CLI.

Provides consistent, colorful terminal output with clean error formatting.

Copyright PolyAI Limited
"""

import json
import os
import sys
from collections.abc import Callable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

# Global verbose flag — set by CLI before commands run
_verbose = False

_theme = Theme(
    {
        "info": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "red bold",
        "filename.new": "green",
        "filename.modified": "green",
        "filename.deleted": "red",
        "filename.conflict": "red bold",
        "label": "bold",
        "muted": "dim",
    }
)

console = Console(theme=_theme, stderr=False)
err_console = Console(theme=_theme, stderr=True)


def set_verbose(verbose: bool) -> None:
    """Enable or disable verbose (traceback) output."""
    global _verbose
    _verbose = verbose


# ── Helpers ──────────────────────────────────────────────────────────


def success(message: str) -> None:
    console.print(f"[success]{message}[/success]")


def error(message: str) -> None:
    err_console.print(f"[error]Error:[/error] {message}")


def warning(message: str) -> None:
    console.print(f"[warning]Warning:[/warning] {message}")


def info(message: str) -> None:
    console.print(f"[info]{message}[/info]")


def plain(message: str) -> None:
    console.print(message)


# ── Structured output ─────────────────────────────────────────────────


def print_status(
    region: str,
    account_id: str,
    project_id: str,
    last_updated: str,
    branch: str,
) -> None:
    """Print project status in a styled panel."""
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Key", style="label", no_wrap=True)
    table.add_column("Value")
    table.add_row("Region", region)
    table.add_row("Account ID", account_id)
    table.add_row("Project ID", project_id)
    table.add_row("Last Pulled", last_updated)
    table.add_row("Current Branch", branch)

    console.print(Panel(table, title="[bold]Project Status[/bold]", border_style="cyan"))


def print_file_list(title: str, files: list[str], style: str) -> None:
    """Print a labeled list of files in a given style."""
    if not files:
        return
    console.print(f"\n[label]{title}:[/label]")
    for f in files:
        console.print(f"  [{style}]{f}[/{style}]")


def print_diff(diff: str) -> None:
    """Print a unified diff with syntax highlighting."""
    console.print(Syntax(diff, "diff", theme="ansi_dark", line_numbers=False))


def print_agents(agents: list[dict[str, Any]]) -> None:
    """Print a table of agents.

    Args:
        agents: List of agent record dicts from the API.
    """
    table = Table(box=None, show_header=True, header_style="bold", padding=(0, 1))
    table.add_column("Agent ID", style="bold yellow", no_wrap=True)
    table.add_column("Name", no_wrap=True)
    table.add_column("Updated", no_wrap=True)
    table.add_column("Branches", justify="right", no_wrap=True)
    for agent in agents:
        updated = _format_iso_timestamp(agent.get("updatedAt", ""))
        branches = str(agent.get("branchCount", 0))
        table.add_row(
            agent.get("agentId", "—"),
            agent.get("agentName", "—"),
            updated,
            branches,
        )
    console.print(table)


def print_branches(branches: dict[str, str] | list[str], current_branch: str | None) -> None:
    """Print branch list with current branch highlighted."""
    console.print("[label]Branches:[/label]")
    items = branches.keys() if isinstance(branches, dict) else branches
    for name in items:
        if name == current_branch:
            console.print(f"  [success]* {name}[/success] [muted](current)[/muted]")
        else:
            console.print(f"    {name}")


def print_validation_errors(errors: list[str]) -> None:
    """Print validation errors in a styled list."""
    console.print("[error]Project configuration is invalid.[/error]")
    for e in errors:
        console.print(f"  [error]-[/error] {e}")


def print_turn_metadata(
    response: dict,
    show_functions: bool = False,
    show_flow: bool = False,
    show_state: bool = False,
) -> None:
    """Print per-turn metadata above the agent response.

    Each section is opt-in via its corresponding flag:
      - show_functions: tool/function calls made this turn with their arguments
      - show_flow: the active flow and step name when the agent is inside a flow
      - show_state: variables added, updated, or removed this turn
    """
    if not (show_functions or show_flow or show_state):
        return

    metadata = response.get("metadata") or {}
    if not metadata:
        return

    function_events: list[dict] = metadata.get("function_events") or []
    in_flow: str | None = metadata.get("in_flow")
    in_step: str | None = metadata.get("in_step")

    # Aggregate state changes across every function event in this turn
    # (only needed when the state panel is enabled).
    all_added: dict = {}
    all_updated: dict = {}
    all_removed: list = []
    if show_state:
        for event in function_events:
            sc = event.get("state_changes") or {}
            all_added.update(sc.get("added") or {})
            all_updated.update(sc.get("updated") or {})
            all_removed.extend(sc.get("removed") or [])

    # ── FUNCTIONS ───────────────────────────────────────────────────────
    if show_functions and function_events:
        fn_table = Table(show_header=False, box=None, padding=(0, 0), expand=False)
        fn_table.add_column("call", overflow="fold")
        for event in function_events:
            name = event.get("name") or ""
            args = event.get("arguments") or {}
            if args:
                args_str = ", ".join(
                    f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in args.items()
                )
            else:
                args_str = ""
            fn_table.add_row(f"[bold cyan]{name}[/bold cyan]({args_str})")
        console.print(
            Panel(
                fn_table,
                title="[bold]Functions[/bold]",
                border_style="cyan",
                padding=(0, 1),
            )
        )

    # ── STATE CHANGES ───────────────────────────────────────────────────
    state_rows: list[tuple[str, str]] = []
    if show_state:
        for k, v in all_added.items():
            raw = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
            if len(raw) > 120:
                raw = raw[:117] + "..."
            state_rows.append((f"[green]+ {k}[/green]", raw))
        for k, v in all_updated.items():
            value = v[-1] if isinstance(v, list) and v else v
            raw = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            if len(raw) > 120:
                raw = raw[:117] + "..."
            state_rows.append((f"[yellow]~ {k}[/yellow]", raw))
        for k in all_removed:
            state_rows.append((f"[red]- {k}[/red]", ""))

    if state_rows:
        state_table = Table(show_header=False, box=None, padding=(0, 1), expand=False)
        state_table.add_column("key", no_wrap=True)
        state_table.add_column("value", overflow="fold")
        for key_cell, val_cell in state_rows:
            state_table.add_row(key_cell, val_cell)
        console.print(
            Panel(
                state_table,
                title="[bold]State Changes[/bold]",
                border_style="yellow",
                padding=(0, 1),
            )
        )

    # ── FLOW / STEP ─────────────────────────────────────────────────────
    if show_flow and (in_flow or in_step):
        parts = []
        if in_flow:
            parts.append(f"Flow: [bold]{in_flow}[/bold]")
        if in_step:
            parts.append(f"Step: [bold]{in_step}[/bold]")
        console.print(
            Panel(
                "  |  ".join(parts),
                title="[bold]Flow / Step[/bold]",
                border_style="bright_magenta",
                padding=(0, 1),
            )
        )


# ── Merge ─────────────────────────────────────────────────────────────


def _merge_preview_cell(value: str) -> str:
    """Format a side value for display; empty string shows a dim placeholder."""
    if value == "":
        return "[dim italic](empty)[/dim italic]"
    return value


def print_merge_conflict_interactive_header(
    *,
    field_path: str,
    resource_key: str,
    conflict_index: int,
    conflict_total: int,
    auto_mergeable: bool,
    heavy: bool,
    base_value: str,
    branch_label: str,
    branch_value: str,
    main_value: str,
    existing_resolution: dict[str, Any] | None = None,
) -> None:
    """Rich panel for one interactive merge conflict (metadata + optional three-way preview)."""
    rows = Table(show_header=False, box=None, pad_edge=False, padding=(0, 1))
    rows.add_column(
        "Label", style="dim", justify="right", min_width=16, overflow="fold", no_wrap=False
    )
    rows.add_column("Value", overflow="fold")

    rows.add_row("Field", Text(field_path, style="bright_cyan"))
    # Only show resource when several fields conflict under the same parent (avoids repeating the path).
    if conflict_total > 1:
        rows.add_row(
            "Resource",
            Text.assemble(
                (resource_key, "default"),
                ("  ·  ", "dim"),
                (f"conflict {conflict_index} of {conflict_total} here", "muted"),
            ),
        )
    status_markup = (
        "[success]Auto-mergeable[/success]"
        if auto_mergeable
        else "[warning]Needs decision[/warning]"
    )
    rows.add_row("Status", status_markup)

    if existing_resolution:
        strategy = existing_resolution.get("strategy", "")
        value = existing_resolution.get("value")
        if value is not None:
            display = value if isinstance(value, str) and "\n" not in value else "value"
        else:
            display = strategy
        rows.add_row("Resolution", Text(display, style="bright_green"))

    body: Table | Group
    if heavy:
        note = Text(
            "Multiline or long values — choose a side, accept auto-merge, or use Edit to open your editor.",
            style="dim",
        )
        body = Group(rows, Text(""), note)
    else:
        rows.add_row("", "")
        # Same order as the CLI resolution menu: main, branch, original (then edit only in the menu).
        rows.add_row("Main", _merge_preview_cell(str(main_value)))
        rows.add_row(f"Branch ({branch_label})", _merge_preview_cell(str(branch_value)))
        rows.add_row("Original (base)", _merge_preview_cell(str(base_value)))
        body = rows

    console.print()
    console.print(
        Panel(
            body,
            title="[bold]Resolve conflict[/bold]",
            title_align="left",
            border_style="bright_blue",
            padding=(0, 1),
        )
    )


def output_merge_conflict_table(
    conflicts: list[dict],
    show_type: bool,
    resolutions: list[dict[str, str]] | None = None,
    panel_title: str = "Merge conflicts",
) -> None:
    """Print merge conflicts in a bordered table (optionally inside a titled panel).

    When ``show_type`` is True, expect enriched rows from ``enrich_branch_merge_conflicts``.
    """
    table = Table(
        show_header=True,
        header_style="bold dim",
        box=box.ROUNDED,
        border_style="yellow",
        padding=(0, 1),
        expand=True,
    )
    table.add_column("Conflict", style="bright_cyan", overflow="fold", no_wrap=False, min_width=20)
    if show_type:
        table.add_column("Status", width=18, no_wrap=True)
        table.add_column("In resource", justify="right", width=14)

    current_resolution_paths = (
        {os.sep.join(r["path"]) for r in resolutions} if resolutions else set()
    )

    for conflict in conflicts:
        visual = conflict.get("visual_path")
        if not visual and conflict.get("path"):
            visual = os.sep.join(conflict["path"])
        if show_type:
            if conflict.get("visual_path") in current_resolution_paths:
                status_cell = "[success]Resolution given[/success]"
            else:
                auto = conflict.get("can_auto_merge")
                status_cell = (
                    "[success]Auto-mergeable[/success]"
                    if auto
                    else "[warning]Needs decision[/warning]"
                )
            n = int(conflict.get("conflicts_in_resource") or 1)
            in_res = f"{n} conflict" + ("" if n == 1 else "s")
            table.add_row(visual, status_cell, in_res)
        else:
            table.add_row(visual)

    wrapped = Panel(
        table,
        title=f"[bold]{panel_title}[/bold]",
        title_align="left",
        border_style="bright_yellow",
        padding=(0, 1),
    )
    console.print()
    console.print(wrapped)


def edit_in_editor(initial_content: str, extension: str = ".txt", filename: str = "edit") -> str:
    """Open the user's editor with initial content and return the edited result.

    Uses $VISUAL, $EDITOR, or falls back to ``vi``.
    """
    import shlex
    import subprocess
    import tempfile

    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"

    safe_name = filename.replace(os.sep, "_").replace("/", "_")
    with tempfile.NamedTemporaryFile(
        prefix=f"{safe_name}_", suffix=extension, mode="w", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(initial_content)
        tmp_path = tmp.name

    try:
        subprocess.run([*shlex.split(editor), tmp_path], check=True)
        with open(tmp_path, encoding="utf-8") as f:
            edited = f.read()
    finally:
        os.unlink(tmp_path)

    if edited == initial_content:
        raise ValueError("No changes were made.")
    return edited


# ── TYPED MERGE EDITING ──────────────────────────────────────────────


def _validate_int(v: str) -> bool | str:
    """Questionary validator for integer input."""
    return True if v.lstrip("-").isdigit() else "Please enter a valid integer"


def _validate_float(v: str) -> bool | str:
    """Questionary validator for float input."""
    try:
        float(v)
        return True
    except ValueError:
        return "Please enter a valid number"


def _validate_json_list(v: str) -> bool | str:
    """Questionary validator for JSON list input."""
    try:
        return True if isinstance(json.loads(v), list) else "Please enter a valid JSON list"
    except json.JSONDecodeError:
        return "Please enter valid JSON"


def prompt_typed_edit(original: Any) -> Any | None:
    """Prompt the user for a custom value, using a type-appropriate questionary widget.

    Returns the edited value cast to the original type, or ``None`` if the user cancels.
    """
    import questionary

    if isinstance(original, bool):
        return questionary.confirm("Custom resolution (true/false)", default=original).ask()
    if isinstance(original, int):
        raw = questionary.text(
            "Custom resolution (integer)", default=str(original), validate=_validate_int
        ).ask()
        return int(raw) if raw is not None else None
    if isinstance(original, float):
        raw = questionary.text(
            "Custom resolution (number)", default=str(original), validate=_validate_float
        ).ask()
        return float(raw) if raw is not None else None
    if isinstance(original, list):
        raw = questionary.text(
            "Custom resolution (JSON list)",
            default=json.dumps(original),
            validate=_validate_json_list,
        ).ask()
        return json.loads(raw) if raw is not None else None
    return None


# ── DEPLOYMENTS ───────────────────────────────────────────────────────


def _format_deployment_timestamp(created_at: str) -> str:
    """Format a deployment timestamp into a compact string."""
    if not created_at:
        return "-"
    try:
        tz_str = created_at.split()[-1]  # "GMT"
        dt = datetime.strptime(created_at, "%a, %d %b %Y %H:%M:%S %Z")
        try:
            dt = dt.replace(tzinfo=ZoneInfo(tz_str))
        except ZoneInfoNotFoundError:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        dt = dt.astimezone()
        return dt.strftime("%d %b %y %H:%M %Z")
    except (TypeError, ValueError):
        return "-"


def print_deployments(
    versions: list[dict[str, Any]], active_deployment_hashes: dict[str, str], details: bool = False
) -> None:
    """Print deployments for the project.

    Args:
        versions: A list of deployment versions.
        active_deployment_hashes: A dictionary mapping deployment types to active version hashes.
        details: Whether to print detailed information for each deployment.
    """
    table = None
    if not details:
        table = Table(
            box=None,
            show_header=False,
            header_style="bold",
            padding=(0, 1),
        )
        table.add_column("Type", style="cyan", no_wrap=True)
        table.add_column("Hash", style="bold yellow", no_wrap=True, max_width=11)
        table.add_column("When", no_wrap=True)
        table.add_column("By", overflow="ellipsis", no_wrap=True)
        table.add_column("Message", overflow="fold")
        table.add_column("Active", overflow="fold")
    for version in versions:
        meta = version.get("deployment_metadata", {})
        deployment_message = meta.get("deployment_message") or "-"
        deployment_type = meta.get("deployment_type")
        created_at = version.get("created_at", "")
        created_by = version.get("created_by", "")
        version_hash = version.get("version_hash")

        badges = []
        if active_deployment_hashes.get("sandbox") == version_hash:
            badges.append("[bold bright blue]sandbox[/bold bright blue]")
        if active_deployment_hashes.get("pre-release") == version_hash:
            badges.append("[bold yellow]pre-release[/bold yellow]")
        if active_deployment_hashes.get("live") == version_hash:
            badges.append("[bold green]live[/bold green]")

        badges_str = " ".join(badges) if badges else ""
        if not details:
            date_compact = _format_deployment_timestamp(created_at)
            table.add_row(
                str(deployment_type or "—"),
                (version_hash or "")[:9],
                date_compact,
                str(created_by or "—"),
                deployment_message,
                badges_str,
            )
        else:
            deployment_id = version.get("id")
            client_env = version.get("client_env")
            artifact_version = version.get("artifact_version")
            lambda_deployment_version = version.get("function_deployment_version")
            console.print(
                f"([cyan]{deployment_type or '—'}[/cyan]) [bold][yellow]{(version_hash or '')[:9]}[/yellow][/bold] {badges_str}"
            )
            console.print(f"Date: {created_at}")
            console.print(f"By: {created_by or '—'}")
            console.print(f"Deployment ID: {deployment_id or '—'}")
            console.print(f"Artifact Version: {artifact_version or '—'}")
            console.print(f"Lambda Deployment Version: {lambda_deployment_version or '—'}")
            console.print(f"Client Environment: {client_env or '—'}")
            console.print(f"Message: {deployment_message}")
            console.print()

    if table:
        console.print(table)
        return


def print_deployment_show(
    deployment: dict[str, Any],
    active_deployment_hashes: dict[str, str],
    included_deployments: list[dict[str, Any]],
    is_rollback: bool = False,
) -> None:
    """Print detailed deployment metadata and included deployments.

    Args:
        deployment: Single deployment record dict.
        active_deployment_hashes: Mapping of env names to active version hashes.
        included_deployments: List of deployment versions included since predecessor.
        is_rollback: Whether this deployment is a rollback to an older version.
    """
    meta = deployment.get("deployment_metadata", {})
    version_hash = deployment.get("version_hash")
    deployment_type = meta.get("deployment_type")
    deployment_message = meta.get("deployment_message") or "-"
    created_at = deployment.get("created_at", "")
    created_by = deployment.get("created_by", "")
    deployment_id = deployment.get("id")
    client_env = deployment.get("client_env")
    artifact_version = deployment.get("artifact_version")
    lambda_deployment_version = deployment.get("function_deployment_version")

    badges = []
    if active_deployment_hashes.get("sandbox") == version_hash:
        badges.append("[bold bright blue]sandbox[/bold bright blue]")
    if active_deployment_hashes.get("pre-release") == version_hash:
        badges.append("[bold yellow]pre-release[/bold yellow]")
    if active_deployment_hashes.get("live") == version_hash:
        badges.append("[bold green]live[/bold green]")
    badges_str = " ".join(badges) if badges else ""

    console.print(
        f"([cyan]{deployment_type or '—'}[/cyan]) "
        f"[bold][yellow]{(version_hash or '')[:9]}[/yellow][/bold] {badges_str}"
    )
    console.print(f"Date: {created_at}")
    console.print(f"By: {created_by or '—'}")
    console.print(f"Deployment ID: {deployment_id or '—'}")
    console.print(f"Artifact Version: {artifact_version or '—'}")
    console.print(f"Lambda Deployment Version: {lambda_deployment_version or '—'}")
    console.print(f"Client Environment: {client_env or '—'}")
    console.print(f"Message: {deployment_message}")
    console.print()

    if not included_deployments:
        console.print("[muted]No intermediate deployments.[/muted]")
    else:
        count = len(included_deployments)
        label = "Reverted deployments" if is_rollback else "Included deployments"
        console.print(f"[label]{label} ({count}):[/label]")
        print_deployments(included_deployments, {})


# ── Conversations ────────────────────────────────────────────────────


def _format_iso_timestamp(ts: str) -> str:
    """Format an ISO 8601 timestamp into a compact local-time string."""
    try:
        dt = datetime.fromisoformat(ts).astimezone()
        return dt.strftime("%d %b %y %H:%M %Z")
    except (TypeError, ValueError):
        return ts


def _extract_summary_heading(short_summary: Any) -> str:
    """Extract the heading from a shortSummary field (may be a JSON string, dict, or plain string)."""
    if not short_summary:
        return "—"
    if isinstance(short_summary, dict):
        return short_summary.get("heading") or "—"
    text = str(short_summary)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed.get("heading") or "—"
    except (json.JSONDecodeError, TypeError):
        pass
    return text


def _format_duration(seconds: int | None) -> str:
    """Format duration in seconds to a human-readable string."""
    if seconds is None:
        return "—"
    m, s = divmod(seconds, 60)
    return f"{m}m{s:02d}s" if m else f"{s}s"


def print_conversations(
    conversations: list[dict[str, Any]],
    url_builder: Callable[[str], str] | None = None,
) -> None:
    """Print a table of conversation summaries.

    Args:
        conversations: List of conversation summary dicts.
        url_builder: Optional callable(conversation_id) -> str that returns a Studio URL.
    """
    show_variant = any(c.get("variantId") for c in conversations)

    table = Table(box=None, show_header=True, header_style="bold", padding=(0, 1))
    table.add_column("Conversation ID", style="bold yellow", no_wrap=True)
    table.add_column("Started", no_wrap=True)
    table.add_column("Duration", no_wrap=True, justify="right")
    table.add_column("From", no_wrap=True)
    table.add_column("Channel", no_wrap=True)
    if show_variant:
        table.add_column("Variant", no_wrap=True)
    table.add_column("Handoff", no_wrap=True)
    table.add_column("Summary", overflow="fold")

    for c in conversations:
        started = c.get("startedAt") or "—"
        if started != "—":
            started = _format_iso_timestamp(started)
        duration = _format_duration(c.get("duration"))
        from_number = c.get("fromNumber") or "—"
        channel = c.get("channel") or "—"
        handoff = ""
        if c.get("handoff"):
            dest = c.get("handoffDestination") or ""
            handoff = f"[yellow]{dest}[/yellow]" if dest else "[yellow]yes[/yellow]"
        summary = _extract_summary_heading(c.get("shortSummary"))

        cid = c.get("conversationId", "—")
        if url_builder and cid != "—":
            url = url_builder(cid)
            cid_display = f"[link={url}]{cid}[/link]"
        else:
            cid_display = cid

        row = [cid_display, started, duration, from_number, channel]
        if show_variant:
            row.append(c.get("variantId") or "—")
        row.extend([handoff, summary])
        table.add_row(*row)

    console.print(table)


def print_conversation_detail(conversation: dict[str, Any], studio_url: str | None = None) -> None:
    """Print detailed conversation information including turns.

    Args:
        conversation: The conversation detail dict from the API.
        studio_url: Optional Agent Studio URL for the conversation.
    """
    cid = conversation.get("conversationId", "—")
    if studio_url:
        cid_display = f"[link={studio_url}]{cid}[/link]"
    else:
        cid_display = cid
    console.print(f"[bold]Conversation[/bold] [yellow]{cid_display}[/yellow]")
    console.print()

    fields = [
        ("Channel", "channel"),
        ("Direction", "direction"),
        ("Language", "language"),
        ("From", "fromNumber"),
        ("To", "toNumber"),
        ("Started", "startedAt"),
        ("Finished", "finishedAt"),
        ("Duration", None),
        ("In Progress", "inProgress"),
        ("Variant", "variantId"),
        ("Deployment", "deploymentId"),
    ]
    for label, key in fields:
        if key is None:
            val = _format_duration(conversation.get("duration"))
        else:
            val = conversation.get(key)
            if val is None:
                continue
            if isinstance(val, bool):
                val = "yes" if val else "no"
            elif key in ("startedAt", "finishedAt"):
                val = _format_iso_timestamp(str(val))
            else:
                val = str(val)
        console.print(f"  [bold]{label}:[/bold] {val}")

    if conversation.get("handoff"):
        dest = conversation.get("handoffDestination") or "—"
        reason = conversation.get("handoffReason") or "—"
        console.print(f"  [bold]Handoff:[/bold] {dest} ({reason})")

    tags = conversation.get("tags")
    if tags:
        console.print(f"  [bold]Tags:[/bold] {', '.join(tags)}")

    score = conversation.get("polyScore")
    if score is not None:
        console.print(f"  [bold]PolyScore:[/bold] {score}")

    summary_heading = _extract_summary_heading(conversation.get("shortSummary"))
    if summary_heading != "—":
        console.print(f"\n  [bold]Summary:[/bold] {summary_heading}")

    note = conversation.get("note")
    if note:
        console.print(f"  [bold]Note:[/bold] {note}")

    turns = conversation.get("turns")
    if turns:
        console.print(f"\n[bold]Turns ({len(turns)}):[/bold]")
        for turn in turns:
            user_input = turn.get("user_input", "")
            agent_response = turn.get("agent_response", "")
            if user_input:
                console.print(f"  [green]user:[/green] {user_input}")
            if agent_response:
                console.print(f"  [cyan]agent:[/cyan] {agent_response}")

    console.print()


# ── Error handling ───────────────────────────────────────────────────

# Maps exception types to user-friendly prefixes
_ERROR_MESSAGES: dict[type, str] = {
    FileNotFoundError: "File not found",
    ValueError: "Invalid value",
    OSError: "System error",
    ConnectionError: "Connection failed",
    TimeoutError: "Request timed out",
    ImportError: "Missing dependency",
}


_POLY_LOGO = """\
        ●
    ●   ●   ●      ██████   ██████  ██   ██    ██   █████  ██
      ●   ●        ██   ██ ██    ██ ██    ██  ██   ██   ██ ██
    ●   ●   ●      ██████  ██    ██ ██     ████    ███████ ██
      ●   ●        ██      ██    ██ ██      ██     ██   ██ ██
    ●   ●   ●      ██       ██████  ██████  ██     ██   ██ ██
        ●\
"""


def print_welcome_message() -> None:
    """Display a welcome banner for the ADK onboarding flow."""
    console.print()
    console.print(
        Panel(
            f"[bold #D9EE50]{_POLY_LOGO}[/bold #D9EE50]",
            style="on black",
            border_style="#D9EE50",
            padding=(1, 6),
        )
    )
    console.print("[bold]Welcome to the PolyAI Agent Development Kit (ADK)![/bold]")
    console.print("Build and edit Agent Studio projects locally with the PolyAI ADK")
    console.print("Documentation: https://polyai.github.io/adk/")
    console.print()


def mask_api_key(key: str) -> str:
    """Display masked API key"""
    masked = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"
    return f"[yellow]{masked}[/yellow]"


def handle_exception(exc: Exception) -> None:
    """Print a clean error message, or full traceback in verbose mode."""
    if _verbose:
        err_console.print_exception(show_locals=False)
    else:
        # Try to find a user-friendly prefix
        prefix = None
        for exc_type, msg in _ERROR_MESSAGES.items():
            if isinstance(exc, exc_type):
                prefix = msg
                break

        # requests.HTTPError
        try:
            import requests

            if isinstance(exc, requests.HTTPError):
                prefix = "API request failed"
        except ImportError:
            pass

        if prefix:
            error(f"{prefix}: {exc}")
        else:
            error(str(exc))

        err_console.print("[muted]Run with --verbose for the full traceback.[/muted]")

    sys.exit(1)


# TESTING


_COMPACT_THRESHOLD = 20
_RECENT_COUNT = 10

_TEST_STATUS_STYLES = {
    "passed": ("Passed", "green"),
    "failed": ("Failed", "red"),
    "error": ("Error", "red"),
    "errored": ("Error", "red"),
    "timed_out": ("Timed Out", "red"),
}

_PENDING_STATUSES = {"pending", "running", "in_progress"}
_FAILURE_STATUSES = {"failed", "error", "errored", "timed_out"}
_ERROR_STATUSES = {"error", "errored", "timed_out"}


def _build_test_table(
    test_results: list[dict],
    test_names: dict[str, str],
    finished: bool = False,
) -> Table:
    """Build a Rich table for test run results (full mode, ≤ 20 tests)."""
    table = Table(show_header=False, show_edge=False, pad_edge=False)
    table.add_column("test", no_wrap=True)
    table.add_column("status", no_wrap=True)
    for entry in test_results:
        case_id = entry.get("testCaseId", "")
        name = test_names.get(case_id, case_id)
        status = entry.get("status", "pending")
        if finished and status in _PENDING_STATUSES:
            status = "error"
        label, style = _TEST_STATUS_STYLES.get(status, ("Pending", "yellow"))
        if status in _PENDING_STATUSES:
            status_cell = Spinner(
                "dots",
                text=f"[{style}]{label}[/{style}]",
                style=style,
            )
        else:
            status_cell = Text(f"{label}", style=style)
        table.add_row(name, status_cell)
    return table


def _build_compact_display(
    completed: list[dict],
    total: int,
    test_names: dict[str, str],
) -> Group:
    """Build the compact rolling display (> 20 tests)."""
    done = len(completed)
    passed = sum(1 for e in completed if e.get("status") not in _FAILURE_STATUSES)
    failed = sum(1 for e in completed if e.get("status") in _FAILURE_STATUSES)
    pending = total - done
    header = Spinner(
        "dots",
        text=(
            "Running tests: "
            f"Passed: [green]{passed}[/green]  "
            f"Failed: [red]{failed}[/red]  "
            f"Pending: [yellow]{pending}[/yellow]"
        ),
        style="info",
    )
    recent = completed[-_RECENT_COUNT:]
    lines: list[Text] = []
    if len(completed) > _RECENT_COUNT:
        lines.append(Text("  ...", style="dim"))
    for entry in recent:
        case_id = entry.get("testCaseId", "")
        name = test_names.get(case_id, case_id)
        status = entry.get("status", "")
        if status in _FAILURE_STATUSES:
            lines.append(Text(f"  ✗ {name}", style="red"))
        else:
            lines.append(Text(f"  ✓ {name}", style="green"))
    return Group(header, *lines)


def _print_test_failures(
    merged: list[dict],
    test_names: dict[str, str],
) -> None:
    """Print failed test details with assertion reasons."""
    failures = [e for e in merged if e.get("status") == "failed"]
    errors = [e for e in merged if e.get("status") in _ERROR_STATUSES]
    if not failures and not errors:
        return

    if errors:
        console.print()
        console.print("[error]Errors:[/error]")
        for entry in errors:
            case_id = entry.get("testCaseId", "")
            name = test_names.get(case_id, case_id)
            console.print(f"  [red]✗ {name}[/red] - [muted]{entry.get('status')}[/muted]")
            test_run_id = entry.get("testRunId", "")
            conv_id = entry.get("rawConversation", {}).get("id", "")
            console.print(f"    [muted]Test run ID: {test_run_id}[/muted]")
            console.print(f"    [muted]Conversation ID: {conv_id}[/muted]")

    if not failures:
        return

    console.print()
    console.print("[error]Failed:[/error]")
    for entry in failures:
        case_id = entry.get("testCaseId", "")
        name = test_names.get(case_id, case_id)
        console.print(f"  [red]✗ {name}[/red]")

        results = entry.get("results") or {}
        prompt_assertions = results.get("prompt_assertion_results") or []
        for assertion in prompt_assertions:
            if assertion.get("is_pass"):
                continue
            prompt = assertion.get("prompt", "")
            reason = assertion.get("reason", "")
            console.print(f"    {prompt}")
            console.print(f"    [muted]→ {reason}[/muted]")

        function_assertions = results.get("function_call_failures") or []
        for assertion in function_assertions:
            if assertion.get("is_pass"):
                continue
            function_name = assertion.get("name", "")
            failure_reason = assertion.get("failure_reason", "")
            function_error = assertion.get("error", "")
            console.print(f"    {function_name}()")
            console.print(f"    [muted]→ {failure_reason}[/muted]")
            if function_error:
                console.print(f"    [muted]→ {function_error}[/muted]")

        test_run_id = entry.get("testRunId", "")
        conv_id = entry.get("rawConversation", {}).get("id", "")
        console.print(f"    [muted]Test run ID: {test_run_id}[/muted]")
        console.print(f"    [muted]Conversation ID: {conv_id}[/muted]")

        console.print()


def poll_test_run_live(
    get_test_run: Callable[[str], dict],
    test_run_id: str,
    matched_tests: list,
    poll_interval: int = 5,
) -> dict:
    """Poll a test run with a live-updating display.

    Args:
        get_test_run: Callable that takes a test run ID and returns the run dict.
        test_run_id: The test run ID to poll.
        matched_tests: List of TestCase objects (must have resource_id and name).
        poll_interval: Seconds between polls.

    Returns:
        dict: The final test run response.
    """
    import time

    total = len(matched_tests)
    test_names = {t.resource_id: t.name for t in matched_tests}
    pending_results = [{"testCaseId": t.resource_id, "status": "pending"} for t in matched_tests]
    compact = total > _COMPACT_THRESHOLD

    seen_done: set[str] = set()
    completed_ordered: list[dict] = []

    merged = pending_results
    initial = (
        _build_compact_display([], total, test_names)
        if compact
        else _build_test_table(merged, test_names)
    )
    with Live(initial, console=console, refresh_per_second=10) as live:
        while True:
            time.sleep(poll_interval)
            result = get_test_run(test_run_id)
            test_results = result.get("testHistory", [])

            actual_by_id = {r.get("testCaseId"): r for r in test_results}
            merged = [actual_by_id.get(p.get("testCaseId"), p) for p in pending_results]

            for entry in merged:
                cid = entry.get("testCaseId", "")
                st = entry.get("status", "pending")
                if st not in _PENDING_STATUSES and cid not in seen_done:
                    seen_done.add(cid)
                    completed_ordered.append(entry)

            if compact:
                live.update(_build_compact_display(completed_ordered, total, test_names))
            else:
                live.update(_build_test_table(merged, test_names))

            status = result.get("status", "")
            if status not in _PENDING_STATUSES:
                if not compact:
                    live.update(_build_test_table(merged, test_names, finished=True))
                break

    _print_test_failures(merged, test_names)

    passed = result.get("passedCount", 0)
    failed = result.get("failedCount", 0)
    error_count = result.get("errorCount", 0)
    total_count = result.get("testCaseCount", total)

    if failed or error_count:
        error(
            f"Test run {result.get('status', 'unknown')}: "
            f"{passed}/{total_count} passed, "
            f"{failed} failed, {error_count} errors"
        )
    else:
        success(f"Test run {result.get('status', 'unknown')}: {passed}/{total_count} passed")

    return result
