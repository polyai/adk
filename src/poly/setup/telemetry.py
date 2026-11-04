"""The three ``poly setup`` analytics events: started, one per step, completed.

A :class:`SetupRun` is created once per command invocation. Steps are timed
with :meth:`SetupRun.step`, which records the outcome whatever happens inside
the block and re-raises. Nothing here raises to the caller and nothing here
collects key values, file paths or command arguments.

Copyright PolyAI Limited
"""

import logging
import platform
import sys
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from poly.cli_commands.shared import get_package_version
from poly.handlers.posthog import alias_identity, capture_event
from poly.setup.agents import (
    NO_AGENT,
    detect_entry,
    detect_installed_agents,
    detect_invoking_agent,
    has_node,
)

logger = logging.getLogger(__name__)

EVENT_STARTED = "setup_started"
EVENT_STEP = "setup_step"
EVENT_COMPLETED = "setup_completed"

OUTCOME_DONE = "done"
OUTCOME_SKIPPED = "skipped"
OUTCOME_DECLINED = "declined"
OUTCOME_FAILED = "failed"
OUTCOMES = frozenset({OUTCOME_DONE, OUTCOME_SKIPPED, OUTCOME_DECLINED, OUTCOME_FAILED})

MODE_HUMAN = "human"
MODE_AGENT = "agent"


class StepResult:
    """Mutable record a step block fills in: its outcome and an optional detail.

    ``detail`` carries one short, non-sensitive label the completion event
    reports (for example the project step's ``created`` / ``connected``).
    """

    def __init__(self) -> None:
        self.outcome = OUTCOME_DONE
        self.error_class: str | None = None
        self.detail: str | None = None

    def skipped(self, detail: str | None = None) -> None:
        """Mark the step as already done or not applicable."""
        self.outcome, self.detail = OUTCOME_SKIPPED, detail

    def declined(self, detail: str | None = None) -> None:
        """Mark the step as offered and turned down by the user."""
        self.outcome, self.detail = OUTCOME_DECLINED, detail

    def failed(self, error_class: str, detail: str | None = None) -> None:
        """Mark the step as failed without an exception reaching the block's end."""
        self.outcome, self.error_class, self.detail = OUTCOME_FAILED, error_class, detail

    def done(self, detail: str | None = None) -> None:
        """Mark the step as done (the default), optionally with a detail label."""
        self.outcome, self.detail = OUTCOME_DONE, detail


class SetupRun:
    """Telemetry for one ``poly setup`` invocation.

    Args:
        region: The region the run targets, if known at the start; it picks the
            PostHog project. Updated via :meth:`identify` or :attr:`region`.
        mode: ``"human"`` or ``"agent"``; see :func:`detect_mode`.
    """

    def __init__(self, region: str | None = None, mode: str = MODE_HUMAN) -> None:
        self.region = region
        self.mode = mode
        self.anonymous_id = f"anon:{uuid.uuid4()}"
        self.distinct_id = self.anonymous_id
        self.started_at = time.monotonic()
        self.steps: dict[str, str] = {}
        self.details: dict[str, str] = {}
        # One failed send disables the rest of the run so a bad network costs one
        # timeout, not one per event.
        self._enabled = True

    def _send(self, event: str, properties: dict) -> None:
        if not self._enabled:
            return
        if not capture_event(self.region, event, properties, self.distinct_id):
            self._enabled = False

    def started(self, *, had_credentials: bool) -> None:
        """Emit ``setup_started`` with the machine and caller facts."""
        self._send(
            EVENT_STARTED,
            {
                "entry": detect_entry(),
                "os": platform.system().lower() or "unknown",
                "adk_version": get_package_version(),
                "invoking_agent": detect_invoking_agent(),
                "agents_detected": detect_installed_agents(),
                "had_credentials": had_credentials,
                "has_node": has_node(),
                "mode": self.mode,
            },
        )

    def identify(self, account_id: str) -> None:
        """Switch the run's identity to the account id, aliasing the anonymous id to it."""
        if not account_id or self.distinct_id == account_id:
            return
        if self._enabled and not alias_identity(self.region, self.anonymous_id, account_id):
            self._enabled = False
        self.distinct_id = account_id

    @contextmanager
    def step(self, name: str) -> Iterator[StepResult]:
        """Time a step and emit ``setup_step`` when the block ends, however it ends.

        An exception (including ``SystemExit``) records the step as failed with
        the exception's class name and is re-raised.
        """
        result = StepResult()
        start = time.monotonic()
        try:
            yield result
        except BaseException as exc:
            result.failed(type(exc).__name__)
            raise
        finally:
            self._record(name, result, time.monotonic() - start)

    def _record(self, name: str, result: StepResult, elapsed: float) -> None:
        self.steps[name] = result.outcome
        if result.detail:
            self.details[name] = result.detail
        properties = {
            "step": name,
            "outcome": result.outcome,
            "duration_ms": int(elapsed * 1000),
        }
        if result.error_class:
            properties["error_class"] = result.error_class
        self._send(EVENT_STEP, properties)

    def completed(self) -> None:
        """Emit ``setup_completed`` with the run's totals."""
        properties = {
            "duration_ms": int((time.monotonic() - self.started_at) * 1000),
            "steps_done": [name for name, outcome in self.steps.items() if outcome == OUTCOME_DONE],
        }
        if "project" in self.details:
            properties["project"] = self.details["project"]
        self._send(EVENT_COMPLETED, properties)


def detect_mode() -> str:
    """``"agent"`` when a coding agent spawned us or stdin is not a terminal, else ``"human"``."""
    if detect_invoking_agent() != NO_AGENT:
        return MODE_AGENT
    try:
        if not sys.stdin.isatty():
            return MODE_AGENT
    except (AttributeError, ValueError):
        return MODE_AGENT
    return MODE_HUMAN
