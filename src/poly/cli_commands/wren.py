"""Wren command: interactive AI-assisted agent editing via Wren.

Copyright PolyAI Limited
"""

import logging
import sys
from argparse import SUPPRESS, ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

import requests

from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.output.json_output import json_print
from poly.project import AgentStudioProject
from poly.utils import retrieve_api_key

logger = logging.getLogger(__name__)

_APPLY_TOOLS = frozenset({"apply", "push"})

_ABORT_REASONS: dict[str, str] = {
    "user_aborted": "Run aborted.",
    "usage_limit_reached": "Run stopped: usage limit reached.",
    "user_input_timeout": "Run stopped: timed out waiting for input.",
    "content_filter_blocked": "Run stopped by content filter.",
}

_ERROR_MESSAGES: dict[str, str] = {
    "llm_rate_limited": "Wren is rate-limited — try again in a moment.",
    "llm_unavailable": "The Wren service is unavailable — try again.",
    "llm_internal": "The Wren service is unavailable — try again.",
    "llm_stream_interrupted": "The response stream was interrupted — try again.",
    "llm_invalid_request": "Wren sent an invalid request to the model — try rephrasing.",
    "file_resolution_failed": "Wren couldn't resolve an attached file.",
    "usage_tracking_failed": "Usage tracking failed — try again.",
    "conversation_not_found": "Session not found — check --session-id or start a new session.",
    "invalid_request": "Wren rejected the request as invalid.",
    "internal": "The Wren service hit an internal error — try again.",
    "run_in_progress": "A run is already in progress for this session — wait for it to finish.",
    "unauthorized": "Not authorized for this project. Check your login (poly login) and project access.",
}


@dataclass
class TurnResult:
    """Result of a single wren turn."""

    session_id: str | None = None
    changes_applied: bool = False
    fatal: bool = False
    suspended: bool = False
    pending_input: dict[str, Any] | None = None
    branch_info: dict[str, str] | None = None
    messages: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, Any] | None = None
    error: dict[str, str] | None = None
    changes: dict[str, int] | None = None
    report: dict[str, str] | None = None


def _follow_branch(
    project: AgentStudioProject, branch_id: str, action: str, json_mode: bool
) -> dict[str, str]:
    """Move the local project onto the branch Wren created or switched to."""
    from poly.output.console import info, plain, warning

    branch_info = {"id": branch_id, "action": action}
    try:
        name = project.wren.follow_branch(branch_id)
    except Exception as e:
        # The session carries on remotely either way; pulls just miss Wren's branch.
        branch_info["error"] = str(e)
        if not json_mode:
            warning(f"Couldn't move the local project to Wren's branch {branch_id}: {e}")
        return branch_info

    if name:
        branch_info["name"] = name
    if not json_mode:
        label = f"{name} ({branch_id})" if name else branch_id
        info(f"⏇ Branch {action}: [bold]{label}[/bold]")
        plain("[muted]  Local project now tracks this branch.[/muted]")
    return branch_info


def _parse_apply_changes(result: Any) -> dict[str, int]:
    """Parse apply/push tool result into change counts."""
    counts: dict[str, int] = {"modified": 0, "added": 0, "deleted": 0}
    if isinstance(result, dict):
        details = result.get("details", {})
        if isinstance(details, dict):
            changes = details.get("changes", [])
            if isinstance(changes, list) and changes:
                for item in changes:
                    kind = str(item.get("changeType", item.get("kind", "modified"))).lower()
                    if "add" in kind:
                        counts["added"] += 1
                    elif "delet" in kind or "remov" in kind:
                        counts["deleted"] += 1
                    else:
                        counts["modified"] += 1
                return counts
        content = result.get("content", [])
        if isinstance(content, list) and content:
            text = ""
            if isinstance(content[0], dict):
                text = content[0].get("text", "")
            elif isinstance(content[0], str):
                text = content[0]
            if text:
                current_kind = "modified"
                for line in text.splitlines():
                    stripped = line.strip().rstrip(":")
                    lower = stripped.lower()
                    if lower in ("modified", "added", "deleted"):
                        current_kind = lower
                    elif stripped:
                        counts[current_kind] = counts.get(current_kind, 0) + 1
                if any(counts.values()):
                    return counts
    return counts


def _extract_report(tool_result: Any) -> tuple[str, str]:
    """Pull the markdown report text and title out of a submit_report result."""
    if not isinstance(tool_result, dict):
        return "", ""
    details = tool_result.get("details") or {}
    title = str(details.get("title", "")) if isinstance(details, dict) else ""
    content = tool_result.get("content") or []
    text = ""
    if isinstance(content, list) and content and isinstance(content[0], dict):
        text = content[0].get("text", "")
    return text, title


def _mermaid_live_url(code: str) -> str:
    """Build a mermaid.live view URL rendering the given diagram source."""
    import base64
    import json
    import zlib

    state = json.dumps({"code": code, "mermaid": {"theme": "default"}})
    compressed = zlib.compress(state.encode("utf-8"), 9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
    return f"https://mermaid.live/view#pako:{encoded}"


def _print_mermaid_links(markdown_text: str) -> None:
    """Print clickable mermaid.live links for any mermaid blocks in the text."""
    import re

    from poly.output.console import console

    blocks = re.findall(r"```mermaid\s*\n(.*?)```", markdown_text, flags=re.DOTALL)
    for i, code in enumerate(b for b in blocks if b.strip()):
        label = "view diagram" if len(blocks) == 1 else f"view diagram {i + 1}"
        console.print(f"  [muted]⧉ [link={_mermaid_live_url(code)}]{label} ↗[/link][/muted]")


def _print_markdown_panel(title: str, content: str) -> None:
    """Render markdown content in a titled panel (report/plan cards)."""
    from rich.markdown import Markdown
    from rich.panel import Panel

    from poly.output.console import console

    console.print()
    console.print(Panel(Markdown(content), title=f"[bold]{title}[/bold]", border_style="cyan"))
    _print_mermaid_links(content)


def _tool_activity(message: Any) -> str | None:
    """Describe a message's tool calls for the spinner.

    Prefers the calls' human-readable ui_description arguments (e.g. "Planning
    10 hotel FAQ topics"); falls back to tool names.
    """
    content = message.get("content", []) if isinstance(message, dict) else []
    names: list[str] = []
    descriptions: list[str] = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") not in ("toolCall", "tool_use"):
            continue
        name = block.get("name") or block.get("toolName", "")
        if name:
            names.append(name)
        arguments = block.get("arguments") or block.get("input") or {}
        description = arguments.get("ui_description") if isinstance(arguments, dict) else None
        if description:
            descriptions.append(str(description))
    if descriptions:
        return f"{' · '.join(descriptions)}…"
    if names:
        return f"Running: {', '.join(names)}…"
    return None


def _format_change_summary(counts: dict[str, int]) -> str:
    """Format change counts into a summary string."""
    total = sum(counts.values())
    if total == 0:
        return ""
    parts = []
    for kind in ("modified", "added", "deleted"):
        n = counts.get(kind, 0)
        if n:
            parts.append(f"{n} {kind}")
    return f"✔ Applied {total} change{'s' if total != 1 else ''} to the branch ({', '.join(parts)})"


class _TurnDisplay:
    """Owns the console's single live region: a spinner or a streaming message.

    Rich allows one Live display at a time, so the spinner and the live
    markdown message are mutually exclusive. When disabled (JSON mode) nothing
    is printed but message text still accumulates; when stdout is not a
    terminal, message deltas fall back to raw streaming.
    """

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled
        self._spinner: Any = None
        self._live: Any = None
        self._buffer = ""
        self._raw_prefix_printed = False

    @staticmethod
    def _is_tty() -> bool:
        from poly.output.console import console

        return console.is_terminal

    def spin(self, text: str) -> None:
        """Start or retext the spinner (no-op while a message is rendering)."""
        if not self._enabled or self._live is not None or not self._is_tty():
            return
        from poly.output.console import console

        if self._spinner is not None:
            self._spinner.update(text)
        else:
            self._spinner = console.status(text, spinner="dots")
            self._spinner.__enter__()

    def _stop_spinner(self) -> None:
        if self._spinner is not None:
            try:
                self._spinner.__exit__(None, None, None)
            except Exception:
                pass
            self._spinner = None

    def start_message(self) -> None:
        """Reset the message buffer for a new wren message."""
        self._buffer = ""

    def append_delta(self, delta: str) -> None:
        """Append streamed text, rendering the message live as markdown."""
        self._buffer += delta
        if not self._enabled:
            return
        from poly.output.console import console

        if not self._is_tty():
            # Piped output: plain streaming, no live region.
            if not self._raw_prefix_printed:
                self._stop_spinner()
                console.print("[bold]Wren:[/bold] ", end="")
                self._raw_prefix_printed = True
            console.print(delta, end="", highlight=False, markup=False)
            return

        from rich.markdown import Markdown

        if self._live is None:
            self._stop_spinner()
            from rich.live import Live

            console.print()
            console.print("[bold]Wren:[/bold]")
            self._live = Live(
                Markdown(self._buffer),
                console=console,
                refresh_per_second=8,
                vertical_overflow="visible",
            )
            self._live.start()
        else:
            self._live.update(Markdown(self._buffer))

    def end_message(self) -> str:
        """Finish the current message and return its full text."""
        text = self._buffer
        self._buffer = ""
        if self._live is not None:
            try:
                from rich.markdown import Markdown

                self._live.update(Markdown(text))
                self._live.stop()
            except Exception:
                pass
            self._live = None
        elif self._raw_prefix_printed:
            from poly.output.console import console

            console.print()
        self._raw_prefix_printed = False
        return text

    def clear(self) -> None:
        """Stop any live output (spinner or in-flight message)."""
        self._stop_spinner()
        if self._live is not None or self._raw_prefix_printed:
            self.end_message()


def _print_header(
    workspace: str,
    project_id: str,
    branch: str | None,
    session_id: str | None = None,
    hints: bool = True,
) -> None:
    """Print the Wren header panel and key hints."""
    from rich.panel import Panel
    from rich.table import Table

    from poly.output.console import console

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="label", no_wrap=True)
    table.add_column()
    table.add_row("Workspace", workspace)
    table.add_row("Project", project_id)
    if branch:
        table.add_row("Branch", branch)
    if session_id:
        table.add_row("Session", session_id)
    console.print(Panel(table, title="[bold]Wren[/bold]", border_style="cyan", expand=False))
    if hints:
        console.print("[muted]  Enter send · Ctrl+J newline · /usage cost · /exit quit[/muted]")


def _format_cost(usage: dict[str, Any]) -> str:
    """Describe a session's spend so far, e.g. "$0.4210 over 12 steps"."""
    steps = usage.get("totalSteps", 0)
    return f"${usage.get('costUsd', 0):.4f} over {steps} step{'s' if steps != 1 else ''}"


def _add_usage(total: dict[str, Any], turn: dict[str, Any] | None) -> None:
    """Add one turn's usage into a session total, in place."""
    if turn:
        total["totalSteps"] = total.get("totalSteps", 0) + turn.get("totalSteps", 0)
        total["costUsd"] = total.get("costUsd", 0) + turn.get("costUsd", 0)


def _print_exit_summary(session_id: str | None, usage: dict[str, Any] | None = None) -> None:
    """Print the session's cost and how to resume it."""
    from poly.output.console import plain

    if usage and usage.get("totalSteps"):
        plain(f"\n[muted]  cost: {_format_cost(usage)}[/muted]")
    if session_id:
        plain(
            f"[muted]  session {session_id} — resume with: "
            f"poly wren chat --session-id {session_id}[/muted]"
        )


_FREEFORM_CHOICE = "Other (type an answer)"

# Questions the CLI can't answer, declined so the run doesn't stall. Each kind's
# decline has its own shape on the server.
_DECLINE_VALUES: dict[str, dict[str, Any]] = {
    "secret": {"created": False, "reason": "cancelled"},
    "edit-secret": {"updated": False, "reason": "cancelled"},
    "delete-secret": {"deleted": False, "reason": "cancelled"},
    "api-credentials": {"configured": False, "reason": "cancelled"},
}

_DECLINE_MESSAGES: dict[str, str] = {
    "secret": "Secrets can't be managed from the CLI",
    "edit-secret": "Secrets can't be managed from the CLI",
    "delete-secret": "Secrets can't be managed from the CLI",
    "api-credentials": "API credentials can't be set from the CLI",
}


def _collect_question_answers(event: dict[str, Any]) -> dict[str, Any] | None:
    """Collect answers for a question gate as typed answer items."""
    import questionary

    from poly.output.console import plain

    questions = event.get("questions", [])
    if not questions:
        return None

    plain("[info]Wren needs input:[/info]")
    if event.get("context"):
        from rich.markdown import Markdown

        from poly.output.console import console

        console.print(Markdown(str(event["context"])))
    answers: list[dict[str, Any]] = []
    for q in questions:
        question_text = q.get("question", "")
        options = [str(o) for o in q.get("options", []) or []]
        # allowFreeform defaults to True when absent: never trap the user in a
        # fixed option list on an older server that doesn't send the field.
        allow_freeform = q.get("allowFreeform", True)
        allow_multiple = q.get("allowMultiple", False)

        if options and allow_multiple:
            selected = questionary.checkbox(question_text, choices=options).ask()
            if selected is None:
                return None
            answers.append({"selected": [str(s) for s in selected]})
            continue

        if options:
            choices = options + ([_FREEFORM_CHOICE] if allow_freeform else [])
            answer = questionary.select(question_text, choices=choices).ask()
            if answer is None:
                return None
            if answer != _FREEFORM_CHOICE:
                answers.append({"selected": [str(answer)]})
                continue
            # Fall through to a free-text prompt.

        text = questionary.text(question_text).ask()
        if text is None:
            return None
        answers.append({"selected": [], "freeform": str(text)})

    return {"inputKind": "question", "value": {"answers": answers}}


def _collect_user_input(event: dict[str, Any]) -> dict[str, Any] | None:
    """Interactively collect a user-input gate response via questionary.

    Returns a typed answer ({"inputKind", "value"}) matching the server's
    userInputAnswerSchema, ready to send back as an input_response message,
    or None if the user cancelled (the run stays paused).
    """
    import questionary
    from rich.markdown import Markdown
    from rich.panel import Panel

    from poly.output.console import console, plain, warning

    input_kind = event.get("inputKind", "")

    if input_kind == "question":
        return _collect_question_answers(event)

    elif input_kind == "plan":
        title = event.get("title", "Plan")
        content = event.get("content", "")
        plain(f"\n[bold]{title}[/bold]")
        if content:
            console.print(Panel(Markdown(content), border_style="cyan"))
        choice = questionary.select(
            "Proceed with this plan?",
            choices=["Approve", "Give feedback", "Cancel"],
        ).ask()
        if choice is None or choice == "Cancel":
            return None
        if choice == "Approve":
            return {"inputKind": "plan", "value": {"approved": True}}
        feedback = questionary.text("Your feedback:").ask()
        if feedback is None:
            return None
        return {"inputKind": "plan", "value": {"approved": False, "feedback": str(feedback)}}

    elif input_kind == "config-change":
        return _collect_config_change(event)

    elif input_kind in _DECLINE_VALUES:
        # Wren learns the CLI can't do this and records it as a blocker.
        warning(
            f"{_DECLINE_MESSAGES[input_kind]} — declining this request. "
            "Set it up in Agent Studio, then ask Wren to continue."
        )
        return {"inputKind": input_kind, "value": _DECLINE_VALUES[input_kind]}

    return None


def _collect_config_change(event: dict[str, Any]) -> dict[str, Any] | None:
    """Show a configuration write Wren wants to make and ask whether to apply it."""
    import questionary

    from poly.output.console import plain, warning

    env = event.get("clientEnv", "")
    target = event.get("target", "values")
    summary = event.get("summary") or {}

    plain(f"\n[bold]Wren wants to change the {target} of the {env} configuration[/bold]")
    if event.get("reason"):
        plain(f"  {event['reason']}")
    for key in event.get("keys") or []:
        counts = key.get("counts") or {}
        detail = ", ".join(
            f"{counts[status]} {status}"
            for status in ("added", "changed", "removed")
            if counts.get(status)
        )
        line = f"  {key.get('status', 'changed')}: {key.get('label') or key.get('key', '')}"
        plain(f"{line} ({detail})" if detail else line)

    if env == "live":
        warning("This writes straight to live.")
    removals = (summary.get("removed") or 0) + (summary.get("removedLeaves") or 0)
    if removals:
        warning(f"This removes {removals} existing value{'s' if removals != 1 else ''}.")

    approved = questionary.confirm("Apply this change?", default=False).ask()
    if approved is None:
        return None
    if not approved:
        return {"inputKind": "config-change", "value": {"approved": False, "reason": "cancelled"}}
    value: dict[str, Any] = {"approved": True}
    if removals:
        value["acknowledgedRemovals"] = True
    return {"inputKind": "config-change", "value": value}


def _render_events(
    events: Iterable[dict[str, Any]],
    result: TurnResult,
    display: _TurnDisplay,
    *,
    verbose: bool = False,
    json_mode: bool = False,
    first_turn: bool = True,
    on_branch_change: Callable[[str, str], dict[str, str] | None] | None = None,
    on_changes_applied: Callable[[], None] | None = None,
) -> None:
    """Render a stream of wren events to the console, updating result.

    The event source may be the live SSE generator or a replayed conversation;
    side effects (branch switching) go through on_branch_change so replays can
    render without touching any API.
    """
    from poly.output.console import error, plain, warning

    sampling_state: dict[str, dict[str, int]] = {}
    # Last tool activity description — carried into subagent turn_starts so the
    # spinner shows what dispatched them (e.g. "Planning 10 hotel FAQ topics…")
    # instead of a generic "Subagent working…".
    last_activity: str | None = None

    for event in events:
        event_type = event.get("type", "")
        depth = event.get("depth", 0) or 0

        if event_type == "session_init":
            result.session_id = event.get("sessionId") or result.session_id
            if verbose and first_turn and not json_mode and result.session_id:
                display.clear()
                plain(f"[muted]  session: {result.session_id}[/muted]")

        elif event_type == "turn_start":
            if depth == 0:
                display.spin("Thinking…")
            else:
                display.spin(last_activity or "Subagent working…")

        elif event_type == "message_start":
            if depth == 0:
                display.start_message()

        elif event_type == "message_delta":
            if depth != 0:
                continue
            delta = event.get("delta", "")
            if delta:
                display.append_delta(delta)

        elif event_type == "message_end":
            if depth == 0:
                text = display.end_message()
                if text.strip():
                    result.messages.append(text)
                    if not json_mode:
                        _print_mermaid_links(text)
            activity = _tool_activity(event.get("message", {}))
            if activity:
                last_activity = activity
                display.spin(activity)

        elif event_type == "turn_end":
            pass

        elif event_type == "tool_execution_end":
            tool_name = event.get("toolName", "unknown")
            is_error = event.get("isError", False)
            tool_result = event.get("result")
            result.tool_calls.append({"toolName": tool_name, "isError": is_error})

            if tool_name in _APPLY_TOOLS:
                display.clear()
                if is_error:
                    if not json_mode:
                        warning("Apply failed — wren may retry.")
                else:
                    counts = _parse_apply_changes(tool_result)
                    total = sum(counts.values())
                    if total > 0:
                        result.changes_applied = True
                        result.changes = counts
                        if not json_mode:
                            plain(f"[success]{_format_change_summary(counts)}[/success]")
                        if on_changes_applied is not None:
                            on_changes_applied()
                    else:
                        if not json_mode:
                            plain("[muted]Workspace already up to date.[/muted]")
            elif tool_name == "submit_report" and not is_error:
                report_text, report_title = _extract_report(tool_result)
                if report_text:
                    result.report = {"title": report_title, "text": report_text}
                    if not json_mode:
                        display.clear()
                        _print_markdown_panel(report_title or "Report", report_text)
            elif is_error:
                # Subagents routinely probe for files that don't exist and
                # recover on their own — only their failures are verbose-only.
                if depth == 0 or verbose:
                    display.clear()
                    if not json_mode:
                        warning(f"  ✗ {tool_name} failed")
                else:
                    logger.debug("Subagent tool failed: %s", tool_name)
            elif verbose and not json_mode:
                display.clear()
                plain(f"[muted]  ✓ {tool_name}[/muted]")

        elif event_type == "branch_change":
            branch_id = event.get("branch", "")
            action = event.get("action", "")
            if branch_id and on_branch_change is not None:
                display.clear()
                result.branch_info = on_branch_change(branch_id, action)

        elif event_type == "auto_pull":
            reason = event.get("reason", "")
            is_error = event.get("isError", False)
            if is_error and not json_mode:
                display.clear()
                warning("Wren workspace sync failed.")
            elif reason != "initial" and verbose and not json_mode:
                display.clear()
                plain(f"[muted]  workspace synced ({reason})[/muted]")

        elif event_type == "session_rename":
            title = event.get("title", "")
            if title and not json_mode:
                display.clear()
                plain(f'[muted]  ✎ "{title}"[/muted]')

        elif event_type == "complete":
            display.clear()
            result.suspended = bool(event.get("suspended", False))
            # Each run ends with one top-level complete covering all its agents;
            # a turn that hands off to subagents spans several runs.
            if depth == 0:
                run_usage = {
                    "totalSteps": event.get("totalSteps", 0) or 0,
                    "costUsd": sum(
                        a.get("costUSD", a.get("costUsd", 0)) or 0
                        for a in (event.get("usageByAgent") or {}).values()
                        if isinstance(a, dict)
                    ),
                }
                result.usage = result.usage or {}
                _add_usage(result.usage, run_usage)
                if verbose and not json_mode:
                    plain(f"[muted]  run done — {_format_cost(run_usage)}[/muted]")

        elif event_type == "error":
            display.clear()
            error_code = event.get("errorCode", "")
            msg = event.get("message", "Unknown error")
            friendly = _ERROR_MESSAGES.get(error_code, f"Wren error: {msg}")
            result.error = {"code": error_code, "message": msg}
            # run_in_progress is handled by the caller's wait-and-retry loop.
            if not json_mode and error_code != "run_in_progress":
                error(friendly)
            if error_code == "unauthorized" and first_turn:
                result.fatal = True

        elif event_type == "aborted":
            display.clear()
            reason = event.get("reason", "unknown")
            result.error = {"code": "aborted", "message": reason}
            if not json_mode:
                warning(_ABORT_REASONS.get(reason, f"Run aborted ({reason})."))

        elif event_type == "user_input_required":
            display.clear()
            if event.get("auto"):
                # Informational: auto mode answers it itself in the same
                # tick and the run continues — show it, don't gate.
                if not json_mode:
                    if event.get("inputKind") == "plan":
                        content = event.get("content", "")
                        if content:
                            title = event.get("title") or "Plan"
                            _print_markdown_panel(f"Plan: {title}", content)
                    else:
                        for q in event.get("questions", []) or []:
                            question_text = q.get("question", "")
                            if question_text:
                                plain(f"[muted]  ? {question_text}[/muted]")
            else:
                result.pending_input = event

        elif event_type == "user_input_answered":
            if not json_mode:
                display.clear()
                selected = [
                    str(s)
                    for answer in (event.get("value", {}) or {}).get("answers", [])
                    for s in answer.get("selected", [])
                ]
                if selected:
                    prefix = "auto-answered: " if event.get("auto") else ""
                    plain(f"[muted]  → {prefix}{', '.join(selected)}[/muted]")
                elif event.get("auto") and (event.get("value") or {}).get("approved"):
                    plain("[muted]  → auto-approved plan[/muted]")

        elif event_type == "content_filter":
            display.clear()
            source = event.get("source", "unknown")
            categories = event.get("categories", [])
            cat_str = ", ".join(str(c) for c in categories) if categories else "unknown"
            if not json_mode:
                warning(f"Content filter triggered on {source} ({cat_str}).")

        elif event_type == "usage_update":
            if verbose and not json_mode:
                input_tokens = event.get("inputTokens", 0)
                output_tokens = event.get("outputTokens", 0)
                cost = event.get("costUsd", 0)
                display.clear()
                plain(f"[muted]  usage: {input_tokens}in/{output_tokens}out ${cost:.4f}[/muted]")

        elif event_type == "usage_limit_reached":
            display.clear()
            cost = event.get("costUsd", 0)
            limit = event.get("limitUsd", 0)
            period = event.get("period", "period")
            result.error = {"code": "usage_limit_reached", "message": str(event)}
            if not json_mode:
                error(f"Usage limit reached (${cost:.2f} of ${limit:.2f} this {period}).")

        elif event_type == "smart_analyst_reasoning":
            text = event.get("text", "")
            if text and not json_mode:
                display.clear()
                plain(f"[muted]  {text}[/muted]")

        elif event_type == "smart_analyst_sampling_start":
            call_id = event.get("callId", "")
            total = event.get("totalBatches", 0)
            sampling_state[call_id] = {"done": 0, "total": total}
            display.spin(f"Analysing data (0/{total} batches)…")

        elif event_type == "smart_analyst_sampling_progress":
            call_id = event.get("callId", "")
            if call_id in sampling_state:
                sampling_state[call_id]["done"] += 1
                done = sampling_state[call_id]["done"]
                total = sampling_state[call_id]["total"]
                display.spin(f"Analysing data ({done}/{total} batches)…")

        elif event_type == "smart_analyst_sampling_complete":
            call_id = event.get("callId", "")
            sampling_state.pop(call_id, None)
            display.spin("Thinking…")

        elif event_type == "compaction_start":
            display.spin("Compacting conversation…")

        elif event_type == "compaction_end":
            display.spin("Thinking…")

        elif event_type in ("thinking_heartbeat", "token_refresh_required", "resume"):
            pass

        else:
            logger.debug("Unhandled event type: %s", event_type)


def _stream_turn(
    project: AgentStudioProject,
    prompt: str,
    session_id: str | None,
    verbose: bool = False,
    json_mode: bool = False,
    first_turn: bool = True,
    no_pull: bool = False,
    mode: str | None = None,
    agent_name: str | None = None,
    input_response: tuple[str, dict[str, Any]] | None = None,
) -> TurnResult:
    """Stream a single wren turn, rendering events to the console.

    Args:
        project: The loaded project.
        prompt: User prompt to send (ignored when input_response is set).
        session_id: Session ID to continue, or None for new session.
        verbose: Whether to show verbose output.
        json_mode: Suppress console output and accumulate for JSON.
        first_turn: Whether this is the first turn of the session.
        no_pull: If True, skip automatic pulling on apply.
        mode: Gate handling mode for the request context.
        agent_name: Optional top-level agent override.
        input_response: (requestId, answer) answering a pending gate instead of
            sending a new prompt. Resumes the paused run in session_id on a fresh
            stream.

    Returns:
        TurnResult with session state and what happened.
    """
    from poly.output.console import error

    result = TurnResult(session_id=session_id)
    display = _TurnDisplay(enabled=not json_mode)

    def _pull_on_apply() -> None:
        if not no_pull and not json_mode:
            _pull_local(project)

    def _open_stream() -> Iterable[dict[str, Any]]:
        if input_response is not None:
            request_id, answer = input_response
            return project.wren.answer(session_id or "", request_id, answer)
        return project.wren.turn(prompt, session_id=session_id, mode=mode, agent_name=agent_name)

    try:
        _render_events(
            _open_stream(),
            result,
            display,
            verbose=verbose,
            json_mode=json_mode,
            first_turn=first_turn,
            on_branch_change=lambda branch_id, action: _follow_branch(
                project, branch_id, action, json_mode
            ),
            on_changes_applied=_pull_on_apply,
        )
    except requests.HTTPError as e:
        display.clear()
        status_code = e.response.status_code if e.response is not None else 0
        if status_code == 409:
            # A previous run (e.g. a suspended subagent) is still going;
            # the caller's wait-and-retry loop handles this silently.
            result.error = {"code": "run_in_progress", "message": str(e)}
        else:
            # 400 bodies carry the server's validation detail, e.g.
            # "Invalid request: context.projectId: Required".
            result.error = {"code": f"http_{status_code}", "message": str(e)}
            if not json_mode:
                if status_code == 400 and input_response is not None:
                    error(f"That request is no longer pending — send a new message. ({e})")
                else:
                    error(f"Request failed: {e}")
            if status_code in (401, 403):
                result.fatal = True
    except requests.ConnectionError:
        display.clear()
        result.error = {"code": "connection_error", "message": "Connection failed"}
        if not json_mode:
            error("Could not connect to Wren. Check your network and region.")
        result.fatal = True
    finally:
        display.clear()

    return result


def _pull_local(project: AgentStudioProject, json_mode: bool = False) -> dict[str, Any]:
    """Pull the project to sync remote changes after apply.

    Returns:
        A dict with pull result info for JSON output.
    """
    from poly.output.console import console, warning

    pull_info: dict[str, Any] = {"performed": True, "conflicts": []}

    if not json_mode:
        console.print("[muted]  Pulling changes to local workspace…[/muted]", end=" ")
    try:
        conflicts, _ = project.pull_project(force=True)
        if conflicts:
            pull_info["conflicts"] = conflicts
            if not json_mode:
                console.print()
                warning(f"Pull completed with {len(conflicts)} conflict(s): {conflicts}")
        else:
            if not json_mode:
                console.print("[muted]done.[/muted]")
    except Exception as e:
        pull_info["error"] = str(e)
        if not json_mode:
            console.print()
            warning(f"Pull failed: {e}")
    return pull_info


_BUSY_RETRY_DELAY_S = 3
_BUSY_RETRY_LIMIT = 200  # ~10 minutes; plan/build chains can run for several


def _turn_with_retry(
    project: AgentStudioProject,
    prompt: str,
    session_id: str | None,
    verbose: bool = False,
    json_mode: bool = False,
    first_turn: bool = True,
    no_pull: bool = False,
    mode: str | None = None,
    agent_name: str | None = None,
    input_response: tuple[str, dict[str, Any]] | None = None,
) -> TurnResult:
    """Run a turn, waiting and retrying while a previous run is still in progress.

    Suspended runs (subagent dispatch) keep working server-side after the SSE
    stream closes; a new prompt gets a 409 until they finish. Only
    run_in_progress is retried — a stale gate answer must not loop.
    """
    import time

    from poly.output.console import plain, warning

    attempts = 0
    while True:
        result = _stream_turn(
            project,
            prompt,
            session_id,
            verbose=verbose,
            json_mode=json_mode,
            first_turn=first_turn,
            no_pull=no_pull,
            mode=mode,
            agent_name=agent_name,
            input_response=input_response,
        )
        busy = bool(result.error) and result.error.get("code") == "run_in_progress"
        if not busy:
            return result
        attempts += 1
        if attempts > _BUSY_RETRY_LIMIT:
            if not json_mode:
                warning("Wren is still busy — try again shortly.")
            return result
        if attempts == 1 and not json_mode:
            plain("[muted]  Wren is busy — waiting for the current run to finish…[/muted]")
        time.sleep(_BUSY_RETRY_DELAY_S)


def _make_prompt_session() -> Any:
    """Build a prompt_toolkit session: Enter sends, Ctrl+J / Alt+Enter add a newline.

    Multiline pastes are preserved via bracketed paste. prompt_toolkit is
    already available as a questionary dependency.
    """
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings

    bindings = KeyBindings()

    @bindings.add("enter")
    def _submit(event: Any) -> None:
        event.current_buffer.validate_and_handle()

    @bindings.add("c-j")
    def _newline(event: Any) -> None:
        event.current_buffer.insert_text("\n")

    @bindings.add("escape", "enter")
    def _newline_alt(event: Any) -> None:
        event.current_buffer.insert_text("\n")

    return PromptSession(
        multiline=True,
        key_bindings=bindings,
        prompt_continuation="     ",
    )


class WrenCommand(BaseCommand):
    """Work on the project with Wren, Agent Studio's AI builder."""

    command = "wren"
    group = BUILDER_API_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``wren`` subcommand tree."""
        wren_parser = subparsers.add_parser(
            "wren",
            parents=[parents.verbose, parents.debug],
            help="Work on the project with Wren, Agent Studio's AI builder.",
            description=(
                "Work on the project with Wren, Agent Studio's AI builder.\n\n"
                "Examples:\n"
                "  poly wren chat\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        wren_subparsers = wren_parser.add_subparsers(dest="wren_subcommand", required=True)

        chat_parser = wren_subparsers.add_parser(
            "chat",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="Chat with Wren about the project.",
            description=(
                "Chat with Wren about the project.\n\n"
                "Wren works remotely on a branch. The local project follows that\n"
                "branch and pulls Wren's changes as it applies them.\n\n"
                "Examples:\n"
                "  poly wren chat\n"
                "  poly wren chat -m 'Add a transfer flow for billing'\n"
                "  poly wren chat --json -m 'Add an FAQ topic'\n"
                "  poly wren chat --session-id <id>\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        chat_parser.add_argument(
            "--message",
            "-m",
            type=str,
            default=None,
            help="Send one message instead of starting an interactive session.",
        )
        chat_parser.add_argument(
            "--session-id",
            type=str,
            default=None,
            help="Continue an existing Wren session.",
        )
        chat_parser.add_argument(
            "--no-pull",
            action="store_true",
            default=False,
            help="Don't pull Wren's changes into the local project.",
        )
        chat_parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Start even if there are local changes. Wren's changes overwrite them.",
        )
        # Dev tool: run a different top-level agent (server default: "orchestrator").
        chat_parser.add_argument("--agent", type=str, default=None, help=SUPPRESS)
        # Dev tool: render a downloaded conversation JSON through the real
        # renderer, no project or API access needed.
        chat_parser.add_argument("--replay", type=str, default=None, help=SUPPRESS)
        chat_parser.add_argument("--replay-delay", type=int, default=0, help=SUPPRESS)

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the matching wren sub-handler."""
        if args.wren_subcommand == "chat":
            cls.chat(args)

    @classmethod
    def chat(cls, args: Namespace) -> None:
        """Run a Wren chat: one message, a JSON round trip, or an interactive session."""
        from poly.output.console import error

        verbose = args.verbose
        if args.replay:
            cls._run_replay(args.replay, args.replay_delay, verbose)
            return

        json_mode = args.json
        if json_mode and not args.message:
            json_print({"success": False, "error": "--json requires --message (-m)"})
            sys.exit(1)

        project = load_project(args.path, output_json=json_mode)

        try:
            # Fails early with login instructions rather than mid-stream.
            retrieve_api_key(project.region)
            if not args.force:
                project.wren.ensure_no_local_changes()
        except ValueError as e:
            if json_mode:
                json_print({"success": False, "error": str(e)})
            else:
                error(str(e))
            sys.exit(1)

        if json_mode:
            cls._run_json(project, args.message, args.session_id, args.no_pull, args.agent)
        elif args.message:
            cls._run_single(
                project, args.message, args.session_id, args.no_pull, verbose, args.agent
            )
        else:
            cls._run_interactive(project, args.session_id, args.no_pull, verbose, args.agent)

    @classmethod
    def _run_replay(cls, path: str, delay_ms: int, verbose: bool) -> None:
        """Render a downloaded conversation JSON through the live renderer."""
        from rich.markup import escape

        from poly.cli_commands.wren_replay import (
            load_conversation,
            replay_segments,
            segment_events,
        )
        from poly.output.console import console, error, info, plain

        try:
            conv = load_conversation(path)
        except (OSError, ValueError) as e:
            error(f"Could not load conversation: {e}")
            sys.exit(1)

        def replay_branch_change(branch_id: str, action: str) -> dict[str, str]:
            info(f"⏇ Branch {action}: [bold]{branch_id}[/bold]")
            plain("[muted]  Local project now tracks this branch.[/muted]")
            return {"id": branch_id, "action": action}

        _print_header(
            conv.get("accountId", "?"),
            conv.get("projectId", "?"),
            conv.get("branchId"),
            hints=False,
        )

        delay_s = max(delay_ms, 0) / 1000
        first_turn = True
        usage: dict[str, Any] = {}
        for prompt, segment in replay_segments(conv):
            if prompt is not None:
                console.print(f"\n[bold]You:[/bold] {escape(prompt)}")
            result = TurnResult()
            display = _TurnDisplay(enabled=True)
            try:
                _render_events(
                    segment_events(segment, delay_s),
                    result,
                    display,
                    verbose=verbose,
                    first_turn=first_turn,
                    on_branch_change=replay_branch_change,
                    on_changes_applied=lambda: plain(
                        "[muted]  Pulling changes to local workspace… done. (replay)[/muted]"
                    ),
                )
            finally:
                display.clear()
            _add_usage(usage, result.usage)
            first_turn = False

        _print_exit_summary(conv.get("sessionId"), usage)

    @classmethod
    def _run_json(
        cls,
        project: AgentStudioProject,
        message: str,
        session_id: str | None,
        no_pull: bool,
        agent_name: str | None = None,
    ) -> None:
        """Single-shot JSON mode — emit one JSON object and exit."""
        result = _turn_with_retry(
            project,
            message,
            session_id,
            verbose=False,
            json_mode=True,
            first_turn=True,
            no_pull=no_pull,
            # Auto: Wren answers its own questions, so a scripted run finishes with
            # Wren's best guess. "headless" would refuse every question instead.
            mode="auto",
            agent_name=agent_name,
        )
        output: dict[str, Any] = {
            "success": result.error is None,
            "sessionId": result.session_id,
            "branch": result.branch_info,
            "messages": result.messages,
            "toolCalls": result.tool_calls,
            "changesApplied": result.changes_applied,
            "changes": result.changes,
            "suspended": result.suspended,
            "report": result.report,
            "pull": None,
            "usage": result.usage,
            "pendingInput": (
                {
                    "inputKind": result.pending_input.get("inputKind"),
                    "requestId": result.pending_input.get("requestId"),
                }
                if result.pending_input
                else None
            ),
            "error": result.error,
        }

        if result.changes_applied and not no_pull:
            output["pull"] = _pull_local(project, json_mode=True)

        json_print(output)
        if result.error:
            sys.exit(1)

    @classmethod
    def _run_single(
        cls,
        project: AgentStudioProject,
        message: str,
        session_id: str | None,
        no_pull: bool,
        verbose: bool,
        agent_name: str | None = None,
    ) -> None:
        """Single-shot interactive mode — one prompt, then pull."""
        from poly.output.console import plain

        result = _turn_with_retry(
            project,
            message,
            session_id,
            verbose=verbose,
            json_mode=False,
            first_turn=True,
            no_pull=no_pull,
            # See _run_json: a single message can't answer Wren's questions.
            mode="auto",
            agent_name=agent_name,
        )
        if result.pending_input:
            plain(
                "[muted]  Wren needs an answer to continue. Run "
                "poly wren chat without -m to answer it in an interactive session.[/muted]"
            )
        if result.suspended:
            plain(
                "[muted]  Wren is continuing to work remotely — "
                "run 'poly pull' later or resume with --session-id to see the result.[/muted]"
            )
        _print_exit_summary(result.session_id, result.usage)

    @classmethod
    def _run_interactive(
        cls,
        project: AgentStudioProject,
        session_id: str | None,
        no_pull: bool,
        verbose: bool,
        agent_name: str | None = None,
    ) -> None:
        """Interactive REPL mode."""
        from poly.output.console import plain, warning

        _print_header(
            project.account_id,
            project.project_id,
            project.get_current_branch(),
            session_id=session_id,
        )

        prompt_session = _make_prompt_session()
        first_turn = True
        pending_pull = False
        usage: dict[str, Any] = {}
        # A typed answer to one of Wren's questions, sent instead of a new prompt.
        pending_response: tuple[str, dict[str, Any]] | None = None

        try:
            while True:
                if pending_response is not None:
                    user_input = ""
                else:
                    try:
                        user_input = prompt_session.prompt("\nYou: ").strip()
                    except (KeyboardInterrupt, EOFError):
                        plain("")
                        break

                    if not user_input:
                        continue
                    if user_input.lower() == "/exit":
                        break
                    if user_input.lower() == "/usage":
                        plain(
                            f"[muted]  cost so far: {_format_cost(usage)}[/muted]"
                            if usage
                            else "[muted]  Nothing spent yet this session.[/muted]"
                        )
                        continue

                turn = _turn_with_retry(
                    project,
                    user_input,
                    session_id,
                    verbose=verbose,
                    json_mode=False,
                    first_turn=first_turn,
                    no_pull=no_pull,
                    # Interactive: real gates, answered over input_response.
                    mode="interactive",
                    agent_name=agent_name,
                    input_response=pending_response,
                )
                pending_response = None
                session_id = turn.session_id or session_id
                first_turn = False
                _add_usage(usage, turn.usage)

                if turn.changes_applied:
                    pending_pull = False

                if turn.suspended:
                    # The run keeps working server-side after the stream closes;
                    # the next message waits on it via the 409 retry loop.
                    plain(
                        "[muted]  Wren is continuing to work remotely — "
                        "your next message will wait for it to finish.[/muted]"
                    )
                    pending_pull = not no_pull

                if turn.pending_input:
                    request_id = turn.pending_input.get("requestId")
                    answer = _collect_user_input(turn.pending_input)
                    if answer and request_id and session_id:
                        pending_response = (str(request_id), answer)
                        continue
                    if answer:
                        warning("Wren's question can't be answered: it has no request ID.")

                if turn.fatal:
                    break
        except KeyboardInterrupt:
            plain("")

        if pending_pull and not no_pull:
            _pull_local(project)
        _print_exit_summary(session_id, usage)
