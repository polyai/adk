"""Multi-leg chat supervision for agentic dial and warm transfer flows.

Copyright PolyAI Limited
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

import requests

from poly.project import PROJECT_CONFIG_FILE, AgentStudioProject

PARENT_CONVERSATION_HEADER = "X-PolyAI-AgenticDial-Parent-Conversation-ID"
DIAL_ID_HEADER = "X-PolyAI-AgenticDial-Dial-ID"

LegStatus = Literal["active", "holding", "bridged", "ended", "failed"]
ReplyProcessor = Callable[[dict], dict]


@dataclass
class ChatLeg:
    """One independently addressable conversation in a multi-leg call."""

    key: str
    project: AgentStudioProject
    conversation_id: str
    environment: str
    role: Literal["parent", "child"]
    status: LegStatus = "active"
    dial_id: Optional[str] = None
    destination: Optional[str] = None
    parent_key: Optional[str] = None
    turns: list[dict] = field(default_factory=list)
    terminal_status_reported: bool = False


class MultiLegChatSupervisor:
    """Keep agentic-dial chat legs alive and route their control events."""

    def __init__(
        self,
        *,
        project: AgentStudioProject,
        environment: str,
        channel: str,
        variant: Optional[str] = None,
        input_lang: Optional[str] = None,
        output_lang: Optional[str] = None,
        show_functions: bool = False,
        show_flow: bool = False,
        show_state: bool = False,
        output_json: bool = False,
        conversation_id: Optional[str] = None,
        reply_processor: Optional[ReplyProcessor] = None,
    ) -> None:
        """Initialize a supervisor around a parent Agent Studio project."""
        self.parent_project = project
        self.environment = environment
        self.channel = channel
        self.variant = variant
        self.input_lang = input_lang
        self.output_lang = output_lang
        self.show_functions = show_functions
        self.show_flow = show_flow
        self.show_state = show_state
        self.output_json = output_json
        self.parent_conversation_id = conversation_id
        self.reply_processor = reply_processor or self._default_reply_processor

        self.legs: dict[str, ChatLeg] = {}
        self.active_key = "parent"
        self.events: list[dict] = []
        self.bridged_dial_id: Optional[str] = None
        self.bridged_parent_key: Optional[str] = None
        self.bridge_started_at: Optional[float] = None
        self.started_at = time.monotonic()
        self.finished = False
        self._cleanup_requested = False

    def run(self, input_messages: Optional[list[str]] = None) -> tuple[bool, dict]:
        """Start the parent leg and run the interactive or scripted control loop."""
        from poly.output.console import error, info, plain

        restart = False
        try:
            self._start_parent()
        except (requests.HTTPError, ValueError) as exc:
            if not self.output_json:
                error(f"Failed to create multi-leg chat session: {exc}")
            return False, {"success": False, "error": str(exc)}

        if not self.output_json:
            plain(
                "[muted]Multi-leg mode: input follows the active leg. "
                "Use /legs, /parent, /leg <dial-or-destination>, /fail, /hangup, "
                "/restart, or /exit.[/muted]"
            )

        scripted = input_messages
        try:
            while not self.finished:
                if scripted is not None:
                    if not scripted:
                        break
                    user_input = scripted.pop(0).strip()
                    if not self.output_json:
                        plain(f"\n[muted]You:[/muted] {user_input}")
                else:
                    try:
                        user_input = input(self._prompt()).strip()
                    except (KeyboardInterrupt, EOFError):
                        if not self.output_json:
                            plain("")
                        self._cleanup_requested = True
                        break

                if not user_input:
                    continue
                if user_input.startswith("/"):
                    restart = self._handle_command(user_input)
                    if restart or self._cleanup_requested:
                        break
                    continue

                if self.bridged_dial_id:
                    if not self.output_json:
                        plain(
                            "[muted]The call is bridged; agent chat turns are paused. "
                            "Use /hangup when the simulated bridged call ends.[/muted]"
                        )
                    continue

                leg = self.legs.get(self.active_key)
                if leg is None or leg.status in {"ended", "failed"}:
                    if not self.output_json:
                        plain(
                            "[muted]That leg is no longer active. Use /legs to select one.[/muted]"
                        )
                    continue
                self._send_turn(leg, user_input)
        finally:
            if self._cleanup_requested:
                self._close_all_legs()
                if not self.output_json:
                    info("Multi-leg chat session ended.")

        return restart, self.to_dict()

    def to_dict(self) -> dict:
        """Return a machine-readable snapshot of the supervised call."""
        return {
            "success": True,
            "bridged_dial_id": self.bridged_dial_id,
            "bridged_parent_leg": self.bridged_parent_key,
            "active_leg": self.active_key,
            "events": self.events,
            "legs": [
                {
                    "key": leg.key,
                    "role": leg.role,
                    "dial_id": leg.dial_id,
                    "destination": leg.destination,
                    "conversation_id": leg.conversation_id,
                    "account_id": leg.project.account_id,
                    "project_id": leg.project.project_id,
                    "environment": leg.environment,
                    "status": leg.status,
                    "url": leg.project.get_conversation_url(leg.conversation_id),
                    "turns": leg.turns,
                }
                for leg in self.legs.values()
            ],
        }

    def _start_parent(self) -> None:
        """Create or resume the root conversation."""
        from poly.output.console import info, plain, success

        response = None
        if self.parent_conversation_id:
            conversation_id = self.parent_conversation_id
            if not self.output_json:
                info(f"Resuming parent chat session (conversation: {conversation_id})...")
        else:
            if self.environment == "draft" and not self.output_json:
                info("Preparing parent branch deployment...")
            response = self.parent_project.create_chat_session(
                self.environment,
                self.channel,
                self.variant,
                self.input_lang,
                self.output_lang,
            )
            conversation_id = response.get("conversation_id")
            if not conversation_id:
                raise ValueError(f"No conversation_id in response: {response}")

        self.parent_conversation_id = conversation_id
        parent = ChatLeg(
            key="parent",
            project=self.parent_project,
            conversation_id=conversation_id,
            environment=self.environment,
            role="parent",
        )
        self.legs[parent.key] = parent
        self.events.append(
            {
                "type": "leg_started",
                "leg": parent.key,
                "conversation_id": conversation_id,
            }
        )
        if not self.output_json:
            url = parent.project.get_conversation_url(conversation_id)
            success(f"Parent leg started (conversation: [link={url}]{conversation_id}[/link])")
        if response is not None:
            self._process_reply(parent, response, user_input=None)
            if not self.output_json and not response.get("response"):
                plain("[muted]Parent agent started without a greeting.[/muted]")

    def _send_turn(
        self,
        leg: ChatLeg,
        text: str,
        *,
        external_events: Optional[list[dict]] = None,
    ) -> Optional[dict]:
        """Send one user or control turn to a leg and process its reply."""
        from poly.output.console import error

        try:
            reply = leg.project.send_message(
                leg.conversation_id,
                text,
                leg.environment,
                self.input_lang,
                self.output_lang,
                external_events=external_events,
            )
        except requests.HTTPError as exc:
            self.events.append({"type": "turn_failed", "leg": leg.key, "error": str(exc)})
            if not self.output_json:
                error(f"Failed to send a turn to {self._leg_label(leg)}: {exc}")
            return None

        self._process_reply(leg, reply, user_input=text if external_events is None else None)
        return reply

    def _process_reply(
        self,
        leg: ChatLeg,
        reply: dict,
        *,
        user_input: Optional[str],
    ) -> None:
        """Record a reply, apply dial instructions, and route function messages."""
        processed = self.reply_processor(reply)
        leg.turns.append({"input": user_input, **processed})
        self._render_reply(leg, reply)

        metadata = reply.get("metadata") or {}
        for dial in metadata.get("agentic_dials") or []:
            self._start_child_leg(leg, dial)

        self._route_function_messages(leg, metadata.get("function_events") or [])

        if bridge := metadata.get("bridge"):
            self._activate_bridge(leg, bridge.get("dial_id"))

        if reply.get("conversation_ended"):
            self._handle_leg_ended(leg)

    def _start_child_leg(self, parent: ChatLeg, dial: dict) -> None:
        """Start a child conversation for one sanitized agentic-dial instruction."""
        from poly.output.console import error, info, success

        dial_id = dial.get("dial_id")
        destination = dial.get("destination") or dial_id or "unknown"
        if not dial_id or dial_id in self.legs:
            return

        target = dial.get("target")
        if not target:
            reason = dial.get("resolution_error") or "dial target could not be resolved"
            self.events.append(
                {
                    "type": "dial_failed",
                    "parent_leg": parent.key,
                    "dial_id": dial_id,
                    "destination": destination,
                    "reason": reason,
                }
            )
            if not self.output_json:
                error(f"Could not start child leg {destination}: {reason}")
            self._send_dial_status(parent, dial_id, "failed", reason=reason)
            return

        child_project, local_project = self._resolve_project(parent.project, target)
        child_environment = self._child_environment(
            parent.environment,
            child_project,
            target.get("client_env"),
            local_project=local_project,
        )
        headers = dict(dial.get("custom_sip_headers") or {})
        headers[PARENT_CONVERSATION_HEADER] = parent.conversation_id
        headers[DIAL_ID_HEADER] = dial_id

        if not self.output_json:
            location = "local branch" if child_environment == "draft" else child_environment
            info(f"Starting child leg {destination} on {child_project.project_id} ({location})...")
        try:
            response = child_project.create_chat_session(
                child_environment,
                self.channel,
                target.get("variant_id"),
                self.input_lang,
                self.output_lang,
                integration_attributes=dial.get("integration_attributes") or {},
                custom_sip_headers=headers,
            )
        except (requests.HTTPError, ValueError) as exc:
            self.events.append(
                {
                    "type": "dial_failed",
                    "parent_leg": parent.key,
                    "dial_id": dial_id,
                    "destination": destination,
                    "reason": str(exc),
                }
            )
            if not self.output_json:
                error(f"Failed to start child leg {destination}: {exc}")
            self._send_dial_status(parent, dial_id, "failed", reason=str(exc))
            return

        conversation_id = response.get("conversation_id")
        if not conversation_id:
            reason = f"No conversation_id in child response: {response}"
            if not self.output_json:
                error(reason)
            self._send_dial_status(parent, dial_id, "failed", reason=reason)
            return

        parent.status = "holding"
        child = ChatLeg(
            key=dial_id,
            project=child_project,
            conversation_id=conversation_id,
            environment=child_environment,
            role="child",
            dial_id=dial_id,
            destination=destination,
            parent_key=parent.key,
        )
        self.legs[child.key] = child
        self.active_key = child.key
        self.events.append(
            {
                "type": "leg_started",
                "leg": child.key,
                "parent_leg": parent.key,
                "dial_id": dial_id,
                "destination": destination,
                "conversation_id": conversation_id,
                "project_id": child.project.project_id,
                "environment": child.environment,
            }
        )
        if not self.output_json:
            url = child.project.get_conversation_url(conversation_id)
            success(
                f"Child leg {destination} answered "
                f"(conversation: [link={url}]{conversation_id}[/link])"
            )

        self._send_dial_status(parent, dial_id, "answered")
        self._process_reply(child, response, user_input=None)

    def _route_function_messages(self, leg: ChatLeg, function_events: list[dict]) -> None:
        """Route child-to-parent and parent-to-child agentic-dial messages."""
        for function_event in function_events:
            control = function_event.get("agentic_dial") or {}
            for message in control.get("messages_to_parent") or []:
                if leg.parent_key and leg.dial_id:
                    parent = self.legs.get(leg.parent_key)
                    if parent:
                        self._send_external_message(
                            parent,
                            leg.dial_id,
                            message.get("content", ""),
                            source_leg=leg,
                        )

            for message in control.get("messages_to_children") or []:
                destination = message.get("destination")
                child = self._find_child(leg.key, destination)
                if child and child.dial_id:
                    self._send_external_message(
                        child,
                        f"{child.dial_id}:child-inbox",
                        message.get("content", ""),
                        source_leg=leg,
                    )

            for destination in control.get("unsubscribed_destinations") or []:
                child = self._find_child(leg.key, destination)
                if child and child.status not in {"bridged", "ended", "failed"}:
                    child.status = "ended"
                    self.events.append(
                        {
                            "type": "dial_unsubscribed",
                            "leg": child.key,
                            "destination": destination,
                        }
                    )

    def _send_external_message(
        self,
        target: ChatLeg,
        event_id: str,
        content: str,
        *,
        source_leg: ChatLeg,
    ) -> None:
        """Deliver an agentic-dial message as a structured external event."""
        self.events.append(
            {
                "type": "message_routed",
                "from_leg": source_leg.key,
                "to_leg": target.key,
                "event_id": event_id,
                "content": content,
            }
        )
        self._send_turn(
            target,
            "",
            external_events=[self._external_event(event_id, "message", content=content)],
        )

    def _send_dial_status(
        self,
        parent: ChatLeg,
        dial_id: str,
        status: str,
        *,
        reason: Optional[str] = None,
    ) -> None:
        """Deliver one child dial status to its parent conversation."""
        payload = {"event_type": "dial_status", "status": status}
        if reason:
            payload["reason"] = reason
        self.events.append(
            {
                "type": "dial_status",
                "leg": parent.key,
                "dial_id": dial_id,
                "status": status,
                "reason": reason,
            }
        )
        self._send_turn(
            parent,
            "",
            external_events=[
                {
                    "ext_event_id": dial_id,
                    "data": json.dumps(payload, separators=(",", ":")),
                    "content_type": "application/json",
                }
            ],
        )

    def _activate_bridge(self, source: ChatLeg, dial_id: Optional[str]) -> None:
        """Mark a parent and child as physically bridged without ending the session."""
        from poly.output.console import success, warning

        if not dial_id:
            if not self.output_json:
                warning("Agent returned a bridge instruction without a dial ID.")
            return
        child = self.legs.get(dial_id)
        parent = self.legs.get(child.parent_key) if child and child.parent_key else source
        if child is None:
            if not self.output_json:
                warning(f"Agent returned a bridge for unknown dial {dial_id}.")
            return

        self.bridged_dial_id = dial_id
        self.bridged_parent_key = parent.key
        self.bridge_started_at = time.monotonic()
        child.status = "bridged"
        parent.status = "bridged"
        self.active_key = child.key
        self.events.append(
            {
                "type": "bridge_started",
                "parent_leg": parent.key,
                "child_leg": child.key,
                "dial_id": dial_id,
            }
        )
        if not self.output_json:
            success(
                f"Bridge active: {self._leg_label(parent)} ↔ {self._leg_label(child)}. "
                "The supervisor will keep the call open until /hangup."
            )

    def _handle_leg_ended(self, leg: ChatLeg) -> None:
        """End only the affected leg, preserving every other live leg."""
        from poly.output.console import plain

        if leg.status == "bridged":
            return
        leg.status = "ended"
        self.events.append({"type": "leg_ended", "leg": leg.key})
        if not self.output_json:
            plain(f"[muted]{self._leg_label(leg)} ended; other legs remain supervised.[/muted]")

        if leg.role == "child" and leg.parent_key and leg.dial_id:
            parent = self.legs.get(leg.parent_key)
            if parent and not leg.terminal_status_reported:
                leg.terminal_status_reported = True
                self.active_key = parent.key
                self._refresh_parent_status(parent)
                self._send_dial_status(parent, leg.dial_id, "hangup")

        live_legs = [
            other for other in self.legs.values() if other.status not in {"ended", "failed"}
        ]
        if not live_legs and not self.bridged_dial_id:
            self.finished = True

    def _handle_command(self, command_line: str) -> bool:
        """Apply a multi-leg slash command and return whether restart was requested."""
        from poly.output.console import plain, warning

        command, _, argument = command_line.partition(" ")
        command = command.lower()
        argument = argument.strip()
        if command == "/legs":
            self._show_legs()
        elif command == "/parent":
            self.active_key = "parent"
            if not self.output_json:
                plain("[muted]Input now targets the parent leg.[/muted]")
        elif command == "/leg":
            leg = self._select_leg(argument)
            if leg:
                self.active_key = leg.key
                if not self.output_json:
                    plain(f"[muted]Input now targets {self._leg_label(leg)}.[/muted]")
            elif not self.output_json:
                warning(f"No leg matches '{argument}'. Use /legs to list them.")
        elif command == "/fail":
            self._fail_active_child(argument or "failed")
        elif command in {"/hangup", "/bridge-end"}:
            self._cleanup_requested = True
        elif command == "/exit":
            self._cleanup_requested = True
        elif command == "/restart":
            self._cleanup_requested = True
            return True
        elif not self.output_json:
            warning(f"Unknown command: {command}")
        return False

    def _fail_active_child(self, reason: str) -> None:
        """Simulate a terminal status on the currently selected child leg."""
        from poly.output.console import warning

        child = self.legs.get(self.active_key)
        if child is None or child.role != "child" or not child.parent_key or not child.dial_id:
            if not self.output_json:
                warning("Select a child leg before using /fail.")
            return
        if child.status in {"ended", "failed", "bridged"}:
            if not self.output_json:
                warning(f"{self._leg_label(child)} is already {child.status}.")
            return

        try:
            child.project.end_chat(child.conversation_id, child.environment)
        except requests.HTTPError:
            pass
        child.status = "failed"
        child.terminal_status_reported = True
        parent = self.legs[child.parent_key]
        self.active_key = parent.key
        self._refresh_parent_status(parent)
        status = reason.lower() if reason.lower() in {"busy", "noanswer", "no-answer"} else "failed"
        status_reason = None if status != "failed" else reason
        self._send_dial_status(parent, child.dial_id, status, reason=status_reason)

    def _close_all_legs(self) -> None:
        """End the simulated call and every server-side conversation context."""
        if self.bridged_dial_id:
            parent = self.legs.get(self.bridged_parent_key or "parent")
            if parent:
                bridge_duration = int(
                    time.monotonic() - (self.bridge_started_at or time.monotonic())
                )
                call_duration = int(time.monotonic() - self.started_at)
                try:
                    parent.project.bridge_ended(
                        parent.conversation_id,
                        bridge_duration_seconds=bridge_duration,
                        call_duration_seconds=call_duration,
                    )
                    self.events.append(
                        {
                            "type": "bridge_ended",
                            "dial_id": self.bridged_dial_id,
                            "bridge_duration_seconds": bridge_duration,
                            "call_duration_seconds": call_duration,
                        }
                    )
                except requests.HTTPError as exc:
                    self.events.append({"type": "bridge_end_failed", "error": str(exc)})

        for leg in reversed(list(self.legs.values())):
            if leg.status in {"ended", "failed"}:
                continue
            try:
                leg.project.end_chat(leg.conversation_id, leg.environment)
            except requests.HTTPError as exc:
                self.events.append({"type": "leg_end_failed", "leg": leg.key, "error": str(exc)})
            leg.status = "ended"
        self.finished = True

    def _refresh_parent_status(self, parent: ChatLeg) -> None:
        """Reflect whether a parent still has another live child on hold."""
        if parent.status in {"bridged", "ended", "failed"}:
            return
        has_live_child = any(
            leg.role == "child"
            and leg.parent_key == parent.key
            and leg.status not in {"ended", "failed"}
            for leg in self.legs.values()
        )
        parent.status = "holding" if has_live_child else "active"

    def _resolve_project(
        self,
        source_project: AgentStudioProject,
        target: dict,
    ) -> tuple[AgentStudioProject, bool]:
        """Use a matching sibling checkout when present, otherwise build a remote proxy."""
        target_account = target.get("account_id") or source_project.account_id
        target_project = target["project_id"]
        if (
            source_project.account_id == target_account
            and source_project.project_id == target_project
        ):
            return source_project, True

        source_root = Path(source_project.root_path)
        candidate_roots = [source_root.parent / target_project]
        try:
            candidate_roots.extend(
                child
                for child in source_root.parent.iterdir()
                if child.is_dir() and child != source_root and child not in candidate_roots
            )
        except OSError:
            pass

        for candidate in candidate_roots:
            if not (candidate / PROJECT_CONFIG_FILE).is_file():
                continue
            try:
                project = AgentStudioProject.from_file_path(str(candidate))
            except (FileNotFoundError, ValueError, OSError):
                continue
            if project.account_id == target_account and project.project_id == target_project:
                return project, True

        return (
            AgentStudioProject(
                region=source_project.region,
                account_id=target_account,
                project_id=target_project,
                root_path=str(source_root.parent / target_project),
                resources={},
                last_updated=datetime.now(),
                branch_id="main",
            ),
            False,
        )

    @staticmethod
    def _child_environment(
        parent_environment: str,
        project: AgentStudioProject,
        target_environment: Optional[str],
        *,
        local_project: bool,
    ) -> str:
        """Prefer the child's own branch when a parent branch is being tested."""
        if (
            parent_environment == "draft"
            and local_project
            and project.branch_id
            and project.branch_id != "main"
        ):
            return "draft"
        aliases = {"prod": "live", "prelive": "pre-release", "pre_live": "pre-release"}
        environment = aliases.get(target_environment or "", target_environment)
        return environment or "sandbox"

    def _find_child(self, parent_key: str, destination: Optional[str]) -> Optional[ChatLeg]:
        """Find the newest live child for a destination under one parent."""
        for leg in reversed(list(self.legs.values())):
            if (
                leg.role == "child"
                and leg.parent_key == parent_key
                and (leg.destination == destination or leg.dial_id == destination)
                and leg.status not in {"ended", "failed"}
            ):
                return leg
        return None

    def _select_leg(self, selector: str) -> Optional[ChatLeg]:
        """Select a leg by key, dial ID, destination, or unambiguous prefix."""
        if not selector:
            return None
        if selector in self.legs:
            return self.legs[selector]
        matches = [
            leg
            for leg in self.legs.values()
            if leg.destination == selector
            or (leg.dial_id or "").startswith(selector)
            or leg.key.startswith(selector)
        ]
        return matches[0] if len(matches) == 1 else None

    def _show_legs(self) -> None:
        """Render a compact list of all supervised legs."""
        if self.output_json:
            return
        from poly.output.console import plain

        for leg in self.legs.values():
            marker = "*" if leg.key == self.active_key else " "
            plain(
                f"{marker} [bold]{self._leg_label(leg)}[/bold] "
                f"status={leg.status} conversation={leg.conversation_id}"
            )

    def _render_reply(self, leg: ChatLeg, reply: dict) -> None:
        """Render one reply with an explicit leg label."""
        if self.output_json:
            return
        from poly.output.console import plain, print_turn_metadata

        print_turn_metadata(reply, self.show_functions, self.show_flow, self.show_state)
        if agent_text := reply.get("response"):
            plain(f"\n[bold]{self._leg_label(leg)}:[/bold] {agent_text}")

    def _prompt(self) -> str:
        """Return an input prompt naming the currently selected leg."""
        leg = self.legs.get(self.active_key)
        return f"\nYou → {self._leg_label(leg) if leg else self.active_key}: "

    @staticmethod
    def _leg_label(leg: ChatLeg) -> str:
        """Return a stable human-readable leg label."""
        if leg.role == "parent":
            return "Parent agent"
        return f"Child agent ({leg.destination or leg.dial_id})"

    @staticmethod
    def _external_event(event_id: str, event_type: str, **payload: str) -> dict:
        """Build an external event accepted by the debug-chat API."""
        return {
            "ext_event_id": event_id,
            "data": json.dumps(
                {"event_type": event_type, **payload},
                separators=(",", ":"),
            ),
            "content_type": "application/json",
        }

    @staticmethod
    def _default_reply_processor(reply: dict) -> dict:
        """Keep JSON output useful without copying the full conversation state."""
        metadata = reply.get("metadata") or {}
        processed = {
            "response": reply.get("response"),
            "conversation_ended": reply.get("conversation_ended", False),
        }
        control = {
            key: metadata[key]
            for key in ("agentic_dials", "bridge")
            if metadata.get(key) is not None
        }
        if control:
            processed["control"] = control
        return processed
