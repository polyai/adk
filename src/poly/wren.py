"""Wren operations scoped to one Agent Studio project, reached as ``project.wren``.

Copyright PolyAI Limited
"""

from typing import TYPE_CHECKING, Any, Generator, Optional

from poly.handlers.wren_api import stream_wren_input_response, stream_wren_turn

if TYPE_CHECKING:
    from poly.project import AgentStudioProject


class ProjectWren:
    """Talk to Wren about a project and keep the local project on Wren's branch.

    Like project methods, these never print or prompt: they return data or raise.
    """

    def __init__(self, project: "AgentStudioProject") -> None:
        """Wrap a loaded project."""
        self._project = project

    def context(self, mode: Optional[str] = None) -> dict[str, str]:
        """Build the context Wren needs to act on this project.

        The branch is read from the project on every call: Wren moves the session
        between branches, and a context without a branch puts Wren back on main.

        Args:
            mode: How Wren handles its questions: "interactive" (it waits for an
                answer) or "auto" (it answers them itself). Omitted on a resumed run,
                which keeps the mode it started with.

        Returns:
            dict[str, str]: The context to send with a message.
        """
        context = {
            "accountId": self._project.account_id,
            "projectId": self._project.project_id,
        }
        if self._project.branch_id:
            context["branchId"] = self._project.branch_id
        if mode:
            context["mode"] = mode
        return context

    def ensure_no_local_changes(self) -> None:
        """Refuse to start while local edits would be overwritten by Wren's changes.

        Raises:
            ValueError: If the project has local changes that haven't been pushed.
        """
        if self._project.get_diffs():
            raise ValueError(
                "You have local changes that Wren's changes would overwrite. "
                "Push or revert them first, or re-run with --force to discard them."
            )

    def turn(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        mode: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Send a prompt to Wren and yield the run's events.

        Args:
            prompt: What to ask Wren.
            session_id: Session to continue, or None to start a new one.
            mode: "interactive" or "auto"; see ``context``.
            agent_name: Top-level agent to run. The server defaults to "orchestrator".

        Yields:
            dict[str, Any]: Each event, up to the one that ends the run.
        """
        return stream_wren_turn(
            region=self._project.region,
            prompt=prompt,
            context=self.context(mode=mode),
            session_id=session_id,
            agent_name=agent_name,
        )

    def answer(
        self, session_id: str, request_id: str, answer: dict[str, Any]
    ) -> Generator[dict[str, Any], None, None]:
        """Answer a question Wren is waiting on, and yield the resumed run's events.

        Args:
            session_id: Session of the paused run.
            request_id: The ``requestId`` from the ``user_input_required`` event.
            answer: Typed answer: ``{"inputKind": ..., "value": ...}``.

        Yields:
            dict[str, Any]: Each event, up to the one that ends the run.

        Raises:
            ValueError: If the session or request ID is missing.
        """
        if not session_id or not request_id:
            raise ValueError("Answering Wren needs both the session ID and the request ID.")
        return stream_wren_input_response(
            region=self._project.region,
            request_id=request_id,
            answer=answer,
            context=self.context(),
            session_id=session_id,
        )

    def follow_branch(self, branch_id: str) -> Optional[str]:
        """Move the local project onto a branch Wren created or switched to.

        Override this to change what happens when Wren changes branch, for example to
        refuse when the local branch is pinned by something else.

        Args:
            branch_id: The branch Wren is now working on.

        Returns:
            Optional[str]: The branch's name, or None if it isn't listed yet.
        """
        self._project.track_branch(branch_id)
        _, branches = self._project.get_branches()
        return next(
            (name for name, meta in branches.items() if meta.get("branchId") == branch_id),
            None,
        )
