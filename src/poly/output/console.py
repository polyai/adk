"""Rich console output helpers for the ADK CLI.

Provides consistent, colorful terminal output with clean error formatting.

Copyright PolyAI Limited
"""

import json
import os
import sys
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
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

    current_resolution_paths = {tuple(r["path"]) for r in resolutions} if resolutions else set()

    for conflict in conflicts:
        visual = conflict.get("visual_path")
        if not visual and conflict.get("path"):
            visual = os.sep.join(conflict["path"])
        if show_type:
            if tuple(conflict.get("path", [])) in current_resolution_paths:
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
                f"([cyan]{deployment_type}[/cyan]) [bold][yellow]{version_hash}[/yellow][/bold] {badges_str}"
            )
            console.print(f"Date: {created_at}")
            console.print(f"By: {created_by}")
            console.print(f"Deployment ID: {deployment_id}")
            console.print(f"Artifact Version: {artifact_version}")
            console.print(f"Lambda Deployment Version: {lambda_deployment_version}")
            console.print(f"Client Environment: {client_env}")
            console.print(f"Message: {deployment_message}")
            console.print()

    if table:
        console.print(table)
        return


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
