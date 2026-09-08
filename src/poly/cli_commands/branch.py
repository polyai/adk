"""Branch command family: list, create, switch, current, delete, merge.

Copyright PolyAI Limited
"""

import json
import os
import subprocess
import sys
from argparse import SUPPRESS, ArgumentParser, Namespace, _SubParsersAction
from collections import Counter
from contextlib import nullcontext
from typing import Any, Optional

from poly.cli_commands.base import (
    PROJECT_SYNC_GROUP,
    BaseCommand,
    GroupedRawTextHelpFormatter,
    Parents,
    add_grouped_subparsers,
    group_subcommands,
)
from poly.cli_commands.shared import load_project, parse_from_projection_json, read_project_config
from poly.output.json_output import json_print
from poly.project import DeploymentMode
from poly.resources.resource_utils import contains_merge_conflict
from poly.utils import merge_strings

# Single-line values longer than this are treated like multiline (no terminal dump; editor for edit).
_BRANCH_MERGE_LONG_LINE_THRESHOLD = 800

# Section headers for `poly branch --help`: commands that move a branch through
# its lifecycle, then the read-only ones that report on it.
BRANCH_LIFECYCLE_GROUP = "Branch lifecycle"
BRANCH_INSPECT_GROUP = "Inspect"

BRANCH_SUBCOMMAND_GROUP_ORDER = [BRANCH_LIFECYCLE_GROUP, BRANCH_INSPECT_GROUP]

BRANCH_SUBCOMMAND_GROUPS = {
    "list": BRANCH_LIFECYCLE_GROUP,
    "create": BRANCH_LIFECYCLE_GROUP,
    "switch": BRANCH_LIFECYCLE_GROUP,
    "current": BRANCH_LIFECYCLE_GROUP,
    "rename": BRANCH_LIFECYCLE_GROUP,
    "delete": BRANCH_LIFECYCLE_GROUP,
    "restore": BRANCH_LIFECYCLE_GROUP,
    "merge": BRANCH_LIFECYCLE_GROUP,
    "sync": BRANCH_LIFECYCLE_GROUP,
    "tag": BRANCH_LIFECYCLE_GROUP,
    "untag": BRANCH_LIFECYCLE_GROUP,
    "diff": BRANCH_INSPECT_GROUP,
    "review": BRANCH_INSPECT_GROUP,
    "status": BRANCH_INSPECT_GROUP,
    "history": BRANCH_INSPECT_GROUP,
}


def _is_sequence_mismatch(errors: list[dict[str, Any]]) -> bool:
    messages = (str(err.get("message", "")).lower() for err in errors)
    return any("sequence mismatch" in m or "sequence_mismatch" in m for m in messages)


def _branch_merge_conflict_file_key(path: list[str]) -> str:
    """Group field-level API conflicts by parent path (resource-ish key)."""
    if not path:
        return ""
    if len(path) <= 1:
        return os.sep.join(path)
    return os.sep.join(path[:-1])


def enrich_branch_merge_conflicts(conflicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add visual_path, merged_value, can_auto_merge, file_key, conflicts_in_resource for branch merge UI."""
    user = [
        c for c in conflicts if c.get("path") and c["path"][-1] not in {"updatedAt", "createdAt"}
    ]
    counts: Counter[str] = Counter(_branch_merge_conflict_file_key(c["path"]) for c in user)
    out: list[dict[str, Any]] = []
    for c in conflicts:
        row = dict(c)
        path = row.get("path")
        if not path or path[-1] in {"updatedAt", "createdAt"}:
            out.append(row)
            continue
        base_value = row.get("baseValue") or ""
        theirs_value = row.get("theirsValue") or ""
        ours_value = row.get("oursValue") or ""
        fk = _branch_merge_conflict_file_key(path)
        row["visual_path"] = os.sep.join(path)
        row["file_key"] = fk
        row["conflicts_in_resource"] = counts[fk]
        if all(isinstance(v, str) for v in [base_value, theirs_value, ours_value]):
            merged = merge_strings(base_value, theirs_value, ours_value)
            row["merged_value"] = merged
            row["can_auto_merge"] = not contains_merge_conflict(merged)
        else:
            row["merged_value"] = None
            row["can_auto_merge"] = False
        out.append(row)
    return out


def _auto_merge_resolution(path: list[str], merged_value: str) -> dict[str, Any]:
    """API payload shape for accepting the locally computed clean merge."""
    return {"path": path, "value": merged_value, "strategy": "theirs"}


def _build_branch_name_lookup(project: Any, archived: list[dict[str, Any]]) -> dict[str, str]:
    """Map branch ids to branch names, for displaying archived branches' parents.

    Archived entries reference their parent by id only, which means nothing to a
    user. A parent is normally archived alongside its children, so the archive
    resolves most ids on its own; the active branches are fetched only when an id
    is still unresolved (a child archived while its parent stayed live).
    """
    names = {
        branch["branchId"]: branch.get("name") or branch["branchId"]
        for branch in archived
        if branch.get("branchId")
    }

    unresolved = {
        branch.get("parentBranchId")
        for branch in archived
        if branch.get("parentBranchId") and branch.get("parentBranchId") != "main"
    } - names.keys()
    if not unresolved:
        return names

    try:
        _, active = project.get_branches()
    except ValueError:
        # The parent column is cosmetic — degrade to showing raw ids rather than
        # failing the whole listing.
        return names

    for name, meta in active.items():
        branch_id = meta.get("branchId")
        if branch_id and branch_id not in names:
            names[branch_id] = name
    return names


class BranchCommand(BaseCommand):
    """Manage branches in the Agent Studio project."""

    command = "branch"

    group = PROJECT_SYNC_GROUP

    @classmethod
    def _branch_name_completer(
        cls,
        prefix: str,
        action: Any = None,
        parser: Any = None,
        parsed_args: Any = None,
        **kwargs: Any,
    ) -> list[str]:
        """Return deletable branch names for argcomplete tab-completion."""
        try:
            base_path = getattr(parsed_args, "path", None) or os.getcwd()
            project = read_project_config(base_path)
            if project is None:
                return []
            _, branches = project.get_branches()
            return [name for name in branches if name != "main" and name.startswith(prefix)]
        except Exception:
            return []

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``branch`` subcommand tree."""
        branches_parser = subparsers.add_parser(
            "branch",
            parents=[],
            help="Manage branches in the Agent Studio project.",
            description=(
                "Manage branches in the Agent Studio project.\n\n"
                "Examples:\n"
                "  poly branch list\n"
                "  poly branch list --archived\n"
                "  poly branch create new-branch\n"
                "  poly branch create new-branch --from other-branch\n"
                "  poly branch switch existing-branch\n"
                "  poly branch rename new-name\n"
                "  poly branch merge 'Merge branch'\n"
                "  poly branch sync\n"
                "  poly branch history\n"
                "  poly branch current\n"
                "  poly branch delete\n"
                "  poly branch restore archived-branch\n"
                "  poly branch tag\n"
                "  poly branch untag\n"
            ),
            formatter_class=GroupedRawTextHelpFormatter,
        )
        branch_subparsers = add_grouped_subparsers(
            branches_parser, dest="branch_subcommand", metavar="<subcommand>"
        )

        # -- list --
        branch_list_parser = branch_subparsers.add_parser(
            "list",
            parents=[parents.path, parents.verbose, parents.json, parents.debug],
            help="List all branches in the project.",
        )
        branch_list_parser.add_argument(
            "--archived",
            action="store_true",
            help="Show soft-deleted (archived) branches instead of active ones.",
        )
        branch_list_parser.set_defaults(branch_subcommand="list")

        # -- create --
        branch_create_parser = branch_subparsers.add_parser(
            "create",
            parents=[parents.path, parents.verbose, parents.json, parents.debug],
            help="Create a new branch.",
        )
        branch_create_parser.add_argument(
            "branch_name", nargs="?", help="Name of the branch to create."
        )
        branch_create_parser.add_argument(
            "--env",
            "--environment",
            type=str,
            choices=["sandbox", "pre-release", "live"],
            default=None,
            dest="environment",
            help="Initiate the new branch from this environment instead of sandbox (main).",
        )
        branch_create_parser.add_argument(
            "--from",
            type=str,
            default=None,
            dest="source_branch",
            metavar="BRANCH",
            help="Create the new branch from this branch instead of the current branch.",
        ).completer = cls._branch_name_completer
        branch_create_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Force switch to a different branch/create new branch and discard changes.",
        )
        branch_create_parser.set_defaults(branch_subcommand="create")

        # -- switch --
        branch_switch_parser = branch_subparsers.add_parser(
            "switch",
            parents=[parents.path, parents.verbose, parents.json, parents.debug],
            help="Switch to a different branch.",
        )
        branch_switch_parser.add_argument(
            "branch_name", nargs="?", help="Name of the branch to switch to."
        ).completer = cls._branch_name_completer
        branch_switch_parser.add_argument(
            "--format",
            action="store_true",
            help="Format the project after switching branches.",
        )
        branch_switch_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Force switch to a different branch and discard changes.",
        )
        branch_switch_parser.add_argument(
            "--from-projection",
            type=str,
            metavar="JSON|-",
            help=SUPPRESS,
            default=None,
        )
        branch_switch_parser.add_argument(
            "--output-json-projection",
            action="store_true",
            help="Output the projection in json format",
            default=False,
        )
        branch_switch_parser.set_defaults(branch_subcommand="switch")

        # -- current --
        branch_current_parser = branch_subparsers.add_parser(
            "current",
            parents=[parents.path, parents.verbose, parents.json, parents.debug],
            help="Show the current branch.",
        )
        branch_current_parser.set_defaults(branch_subcommand="current")

        # -- rename --
        branch_rename_parser = branch_subparsers.add_parser(
            "rename",
            parents=[parents.path, parents.verbose, parents.json, parents.debug],
            help="Rename the current branch.",
        )
        branch_rename_parser.add_argument(
            "new_branch_name",
            type=str,
            nargs="?",
            default=None,
            help="New name for the current branch.",
        )
        branch_rename_parser.set_defaults(branch_subcommand="rename")

        # -- delete --
        branch_delete_parser = branch_subparsers.add_parser(
            "delete",
            parents=[parents.path, parents.verbose, parents.json, parents.debug],
            help="Interactively select and delete a branch.",
        )
        branch_delete_parser.add_argument(
            "branch_name",
            nargs="?",
            default=None,
            help="Name of the branch to delete directly, skipping the interactive prompt.",
        ).completer = cls._branch_name_completer
        branch_delete_parser.set_defaults(branch_subcommand="delete")

        # -- restore --
        branch_restore_parser = branch_subparsers.add_parser(
            "restore",
            parents=[parents.path, parents.verbose, parents.json, parents.debug],
            help="Restore a soft-deleted branch from the archive.",
        )
        branch_restore_parser.add_argument(
            "branch_id",
            type=str,
            metavar="BRANCH",
            nargs="?",
            default=None,
            help=(
                "Branch id of the archived branch to restore. Archived names are not "
                "unique, so ids are required — find them with 'poly branch list --archived'."
            ),
        )
        branch_restore_parser.set_defaults(branch_subcommand="restore")

        # -- merge --
        branch_merge_parser = branch_subparsers.add_parser(
            "merge",
            parents=[parents.path, parents.verbose, parents.json, parents.debug],
            help="Merge branch into its parent branch",
        )
        branch_merge_parser.add_argument(
            "message",
            nargs="?",
            default=None,
            help="Message for the merge. Required when merging into main.",
        )
        branch_merge_parser.add_argument(
            "--interactive",
            "-i",
            action="store_true",
            help="Enable interactive mode for resolving any merge conflicts. Set $EDITOR or $VISUAL to your preferred editor for editing merge conflict values if needed.",
        )
        branch_merge_parser.add_argument(
            "--resolutions",
            type=str,
            default=None,
            help=(
                "Conflict resolutions as a JSON file path, inline JSON string, or '-' for stdin. "
                "JSON should be an array of objects, each representing a conflict resolution:\n"
                '- path: List of strings representing the path to the conflicted field (e.g., ["users", "1", "name"])\n'
                '- strategy: Resolution strategy - "ours", "theirs", or "base"\n'
                '- value: Optional custom value (use "theirs" strategy)'
            ),
        )
        branch_merge_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Skip the confirmation prompt when merging into main deploys to a live environment.",
        )
        branch_merge_parser.set_defaults(branch_subcommand="merge")

        # -- sync --
        branch_sync_parser = branch_subparsers.add_parser(
            "sync",
            parents=[parents.path, parents.verbose, parents.json, parents.debug],
            help="Sync branch with parent",
        )
        branch_sync_parser.add_argument(
            "--interactive",
            "-i",
            action="store_true",
            help="Enable interactive mode for resolving any merge conflicts. Set $EDITOR or $VISUAL to your preferred editor for editing merge conflict values if needed.",
        )
        branch_sync_parser.add_argument(
            "--resolutions",
            type=str,
            default=None,
            help=(
                "Conflict resolutions as a JSON file path, inline JSON string, or '-' for stdin. "
                "JSON should be an array of objects, each representing a conflict resolution:\n"
                '- path: List of strings representing the path to the conflicted field (e.g., ["users", "1", "name"])\n'
                '- strategy: Resolution strategy - "ours", "theirs", or "base"\n'
                '- value: Optional custom value (use "theirs" strategy)'
            ),
        )
        branch_sync_parser.set_defaults(branch_subcommand="sync")

        # -- tag --
        branch_tag_parser = branch_subparsers.add_parser(
            "tag",
            parents=[parents.path, parents.verbose, parents.json, parents.debug],
            help="Tag the current branch and deploy to staging environment. Tagging 'main' branch is not supported.",
        )
        branch_tag_parser.set_defaults(branch_subcommand="tag")

        # -- untag --
        branch_untag_parser = branch_subparsers.add_parser(
            "untag",
            parents=[parents.path, parents.verbose, parents.json, parents.debug],
            help="Remove a tag from the current branch. Untagging 'main' branch is not supported.",
        )
        branch_untag_parser.set_defaults(branch_subcommand="untag")

        # -- diff --
        branch_diff_parser = branch_subparsers.add_parser(
            "diff",
            parents=[parents.path, parents.verbose, parents.json, parents.debug],
            help="Show changes made on a branch since it was created.",
        )
        branch_diff_parser.add_argument(
            "branch_name",
            nargs="?",
            default=None,
            help="Branch to diff. Defaults to the current branch.",
        ).completer = cls._branch_name_completer
        branch_diff_parser.add_argument(
            "--files",
            nargs="*",
            help="Only show changes for these files.",
        )
        branch_diff_parser.set_defaults(branch_subcommand="diff")

        # -- review --
        branch_review_parser = branch_subparsers.add_parser(
            "review",
            parents=[parents.path, parents.verbose, parents.json, parents.debug],
            help="Create a GitHub Gist of branch changes since it was created.",
        )
        branch_review_parser.add_argument(
            "branch_name",
            nargs="?",
            default=None,
            help="Branch to review. Defaults to the current branch.",
        ).completer = cls._branch_name_completer
        branch_review_parser.add_argument(
            "--files",
            nargs="*",
            help="Only include changes for these files.",
        )
        branch_review_parser.set_defaults(branch_subcommand="review")

        # -- status --
        branch_status_parser = branch_subparsers.add_parser(
            "status",
            parents=[parents.path, parents.verbose, parents.json, parents.debug],
            help="Show branch status including local changes and fork-point info.",
        )
        branch_status_parser.add_argument(
            "branch_name",
            nargs="?",
            default=None,
            help="Branch to check status for. Defaults to the current branch.",
        ).completer = cls._branch_name_completer
        branch_status_parser.set_defaults(branch_subcommand="status")

        # -- history --
        branch_history_parser = branch_subparsers.add_parser(
            "history",
            parents=[parents.path, parents.verbose, parents.json, parents.debug],
            help="Show the history of a branch.",
        )
        branch_history_parser.add_argument(
            "--branch-name",
            "-b",
            type=str,
            default=None,
            help="Name of the branch to show history for. Defaults to the current branch.",
        )
        branch_history_parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of history entries to show. Shows all by default.",
        )
        branch_history_parser.set_defaults(branch_subcommand="history")

        group_subcommands(
            branch_subparsers, BRANCH_SUBCOMMAND_GROUPS, BRANCH_SUBCOMMAND_GROUP_ORDER
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the matching branch sub-handler."""
        if args.branch_subcommand == "list":
            cls.branch_list(args.path, args.json, getattr(args, "archived", False))

        elif args.branch_subcommand == "create":
            cls.branch_create(
                args.path,
                args.branch_name,
                args.json,
                getattr(args, "environment", None),
                getattr(args, "force", False),
                getattr(args, "source_branch", None),
            )

        elif args.branch_subcommand == "switch":
            cls.branch_switch(
                args.path,
                args.branch_name,
                getattr(args, "force", False),
                getattr(args, "format", False),
                args.json,
                output_json_projection=args.output_json_projection,
                from_projection=args.from_projection,
            )

        elif args.branch_subcommand == "current":
            cls.get_current_branch(args.path, args.json)

        elif args.branch_subcommand == "delete":
            cls.branch_delete(args.path, args.branch_name, args.json)

        elif args.branch_subcommand == "merge":
            cls.branch_merge(
                args.path, args.message, args.json, args.interactive, args.resolutions, args.force
            )

        elif args.branch_subcommand == "sync":
            cls.branch_sync(args.path, args.json, args.interactive, args.resolutions)

        elif args.branch_subcommand == "history":
            cls.branch_history(args.path, args.branch_name, args.json, args.limit)

        elif args.branch_subcommand == "rename":
            cls.branch_rename(args.path, args.new_branch_name, args.json)

        elif args.branch_subcommand == "restore":
            cls.branch_restore(args.path, args.branch_id, args.json)

        elif args.branch_subcommand == "tag":
            cls.branch_tag(args.path, args.json)

        elif args.branch_subcommand == "untag":
            cls.branch_untag(args.path, args.json)

        elif args.branch_subcommand == "diff":
            cls.branch_diff(args.path, args.branch_name, getattr(args, "files", None), args.json)

        elif args.branch_subcommand == "review":
            cls.branch_review(args.path, args.branch_name, getattr(args, "files", None), args.json)

        elif args.branch_subcommand == "status":
            cls.branch_status(args.path, args.branch_name, args.json)

    @classmethod
    def branch_list(cls, base_path: str, output_json: bool = False, archived: bool = False) -> None:
        """List branches in the Agent Studio project."""
        from poly.output.console import (
            plain,
            print_archived_branches,
            print_branches,
            print_releases_branches,
            warning,
        )

        project = load_project(base_path, output_json=output_json)

        if archived:
            branches = project.list_archived_branches()
            if output_json:
                json_print({"archived_branches": branches})
                return
            if not branches:
                plain("[muted]No archived branches found.[/muted]")
                return
            print_archived_branches(branches, _build_branch_name_lookup(project, branches))
            return

        current_branch, branches = project.get_branches()

        if output_json:
            json_output = {
                "current_branch": current_branch,
                "branches": branches,
            }
            json_print(json_output)
            return

        if not branches:
            plain("[muted]No branches found.[/muted]")
            return

        if project.deployment_mode == DeploymentMode.RELEASES_BRANCHES:
            print_releases_branches(branches, current_branch)
        else:
            print_branches(branches, current_branch)

        if current_branch is None:
            warning(
                "Current local branch does not exist in Agent Studio. "
                "It may have been deleted or merged."
            )

    @classmethod
    def branch_create(
        cls,
        base_path: str,
        branch_name: str = None,
        output_json: bool = False,
        env: str = None,
        force: bool = False,
        source_branch: str = None,
    ) -> None:
        """Create a new branch in the Agent Studio project."""
        from poly.output.console import error, success, warning

        project = load_project(base_path, output_json=output_json)

        if env in ["pre-release", "live"]:
            # Checks for any local changes on main before creating env branch.
            if diffs := project.get_diffs():
                if not force:
                    raise ValueError(f"Uncommitted changes on main, diffs: {list(diffs.keys())}")

        if not branch_name:
            if output_json:
                json_print(
                    {
                        "success": False,
                        "error": "branch create with --json requires a branch name argument.",
                    }
                )
                sys.exit(1)
            branch_name = input("Enter the name of the new branch: ").strip()
            if not branch_name:
                warning("No branch name provided. Exiting.")
                return

        if source_branch:
            base_branch_name = source_branch
            _, branches = project.get_branches()
            base_branch_id = branches.get(source_branch, {}).get("branchId")
        else:
            base_branch_id = project.branch_id
            base_branch_name = project.get_current_branch()
        try:
            new_branch_id = project.create_branch(branch_name, source_branch_name=source_branch)
        except ValueError as e:
            if output_json:
                json_print({"success": False, "error": str(e)})
            else:
                error(str(e))
            sys.exit(1)
        if output_json:
            json_print(
                {
                    "success": bool(new_branch_id),
                    "base_branch_id": base_branch_id,
                    "base_branch_name": base_branch_name,
                    "new_branch_id": new_branch_id,
                    "branch_name": branch_name,
                }
            )
            if not new_branch_id:
                sys.exit(1)
            return

        if new_branch_id:
            success(
                f"Created new branch '{branch_name}' (ID: {new_branch_id}) from '{base_branch_name}'"
            )
        else:
            error("Failed to create the branch.")
            sys.exit(1)

        # Pushes existing state of env to provide clean slate for hotfixes.
        if env in ["pre-release", "live"]:
            project.pull_project_from_env(env=env, format=False)
            success(f"Pulled {project.account_id}/{project.project_id}")
            project.push_project(
                force=True,
                skip_validation=True,
                dry_run=False,
                format=False,
            )

    @classmethod
    def branch_switch(
        cls,
        base_path: str,
        branch_name: str = None,
        force: bool = False,
        format: bool = False,
        output_json: bool = False,
        output_json_projection: bool = False,
        from_projection: str = None,
    ) -> None:
        """Switch to a different branch in the Agent Studio project."""
        import questionary

        from poly.output.console import console, error, flatten_branch_tree, plain, success, warning

        project = load_project(base_path, output_json=output_json)

        if not branch_name:
            if output_json:
                json_print(
                    {
                        "success": False,
                        "error": "branch switch with --json requires a branch name argument.",
                    }
                )
                sys.exit(1)
            # Drop down menu to select branch
            current_branch, branches = project.get_branches()
            if not branches:
                plain("[muted]No branches found.[/muted]")
                return

            if project.deployment_mode == DeploymentMode.RELEASES_BRANCHES:
                # Show branch-from-branch lineage via indentation/connectors.
                choices = [
                    questionary.Choice(title=title, value=value)
                    for title, value in flatten_branch_tree(branches, current_branch)
                ]
            else:
                choices = [
                    questionary.Choice(
                        title=f"{name} (current)" if name == current_branch else name,
                        value=name,
                    )
                    for name in branches.keys()
                ]

            branch_name = questionary.select(
                "Select Branch", choices=choices, use_search_filter=True, use_jk_keys=False
            ).ask()
            if not branch_name:
                warning("No branch selected. Exiting.")
                return

        projection_json = parse_from_projection_json(
            from_projection,
            json_errors=output_json or output_json_projection,
        )

        ctx = (
            console.status("[info]Saving resources...[/info]") if not output_json else nullcontext()
        )
        on_save = None

        with ctx as status:
            if status:

                def on_save(current: int, total: int) -> None:
                    status.update(f"[info]Saving resources ({current}/{total})...[/info]")

            switch_ok, projection = project.switch_branch(
                branch_name,
                force=force,
                format=format,
                projection_json=projection_json,
                on_save=on_save,
            )

        if output_json or output_json_projection:
            json_output = {
                "success": switch_ok,
                "branch_name": branch_name,
            }
            if output_json_projection:
                json_output["projection"] = projection
            json_print(json_output)
            if not switch_ok:
                sys.exit(1)
            return

        if switch_ok:
            success(f"Switched to branch '{branch_name}'.")
        else:
            error(f"Failed to switch to branch '{branch_name}'.")
            sys.exit(1)

    @classmethod
    def get_current_branch(cls, base_path: str, output_json: bool = False) -> None:
        """Get the current branch of the Agent Studio project, and its parent if it has one."""
        from poly.output.console import plain, warning

        project = load_project(base_path, output_json=output_json)

        current_branch, branches = project.get_branches()

        if current_branch is None:
            if output_json:
                json_print({"current_branch": None, "parent_branch": None})
            else:
                warning(
                    "Current local branch does not exist in Agent Studio. "
                    "It may have been deleted or merged."
                )
            return

        parent_branch_id = branches.get(current_branch, {}).get("parentBranchId")
        parent_branch = (
            next(
                (
                    name
                    for name, meta in branches.items()
                    if meta.get("branchId") == parent_branch_id
                ),
                parent_branch_id,
            )
            if parent_branch_id
            else None
        )

        if output_json:
            json_print({"current_branch": current_branch, "parent_branch": parent_branch})
            return

        plain(f"Current branch: [bold]{current_branch}[/bold]")
        if parent_branch and parent_branch != "main":
            plain(f"Parent branch: [bold]{parent_branch}[/bold]")

    @classmethod
    def branch_delete(
        cls,
        base_path: str,
        branch_name: Optional[str] = None,
        output_json: bool = False,
    ) -> None:
        """Interactively select and delete a branch from the Agent Studio project.

        If branch_name is provided, delete that specific branch without an interactive prompt.
        """
        import questionary

        from poly.output.console import error, flatten_branch_tree, info, plain, success, warning

        project = load_project(base_path, output_json=output_json)
        current_branch, branches = project.get_branches()

        # Filter out 'main' — it cannot be deleted
        deletable = {name: meta for name, meta in branches.items() if name != "main"}

        if branch_name:
            if branch_name not in deletable:
                msg = f"Branch '{branch_name}' does not exist or cannot be deleted."
                if output_json:
                    json_print({"success": False, "message": msg})
                else:
                    error(msg)
                return
            if not output_json:
                confirmed = questionary.confirm(
                    f"Delete branch '{branch_name}'?", default=False
                ).ask()
                if not confirmed:
                    warning("Aborted.")
                    return
            try:
                deleted = project.delete_branch(branch_name)
            except ValueError as e:
                if output_json:
                    json_print({"success": False, "message": str(e)})
                else:
                    error(str(e))
                sys.exit(1)
            if output_json:
                result = {"success": deleted}
                if deleted and branch_name == current_branch:
                    result["switched_to"] = "main"
                json_print(result)
            else:
                if deleted:
                    success(f"Deleted branch: {branch_name}")
                    if branch_name == current_branch:
                        info("Switched to branch 'main'.")
                else:
                    error(f"Failed to delete branch '{branch_name}'.")
            return

        if not deletable:
            plain("[muted]No deletable branches found.[/muted]")
            return

        if project.deployment_mode == DeploymentMode.RELEASES_BRANCHES:
            # Show 'main' as disabled tree context so lineage is visible, but not selectable.
            choices = [
                questionary.Choice(
                    title=title,
                    value=value,
                    disabled="cannot delete main" if value == "main" else None,
                )
                for title, value in flatten_branch_tree(branches, current_branch)
            ]
        else:
            choices = [
                questionary.Choice(
                    title=f"{name} (current)" if name == current_branch else name,
                    value=name,
                )
                for name in deletable
            ]

        selected = questionary.checkbox("Select branches to delete", choices=choices).ask()
        if not selected:
            warning("No branches selected. Exiting.")
            return

        branch_names = selected
        confirm_msg = f"Delete {len(branch_names)} branch(es): {', '.join(branch_names)}?"
        confirmed = questionary.confirm(confirm_msg, default=False).ask()
        if not confirmed:
            warning("Aborted.")
            return

        deleted_count = 0
        current_branch_deleted = False
        for name in selected:
            try:
                deleted = project.delete_branch(name)
                if deleted:
                    deleted_count += 1
                    if name == current_branch:
                        current_branch_deleted = True
                    if not output_json:
                        plain(f"  [muted]Deleted branch:[/muted] {name}")
                        if name == current_branch:
                            info("Switched to branch 'main'.")
                else:
                    if not output_json:
                        error(f"Failed to delete branch '{name}'.")
            except ValueError as e:
                if not output_json:
                    error(str(e))

        if output_json:
            result = {"success": deleted_count > 0, "deleted": deleted_count}
            if current_branch_deleted:
                result["switched_to"] = "main"
            json_print(result)
        else:
            if deleted_count:
                success(f"Deleted {deleted_count} branch(es).")

    @staticmethod
    def _merge_interactively(
        conflicts: list[dict[str, Any]],
        existing_resolutions: dict[str, dict[str, Any]],
        branch_display_name: str = "",
    ) -> list[dict[str, Any]]:
        """Resolve merge conflicts with questionary; expects API conflicts optionally enriched."""
        import questionary

        from poly.output.console import (
            edit_in_editor,
            print_merge_conflict_interactive_header,
            prompt_typed_edit,
            warning,
        )

        resolutions: list[dict[str, Any]] = []
        index_in_resource: dict[str, int] = {}
        branch_label = branch_display_name or "current branch"

        def _is_heavy_content(c: dict[str, Any]) -> bool:
            for key in ("baseValue", "theirsValue", "oursValue"):
                v = c.get(key, "")
                s = v if isinstance(v, str) else str(v)
                if "\n" in s:
                    return True
                if len(s) > _BRANCH_MERGE_LONG_LINE_THRESHOLD:
                    return True
            return False

        for conflict in conflicts:
            if conflict["path"][-1] in {"updatedAt", "createdAt"}:
                resolutions.append({"path": conflict["path"], "strategy": "theirs"})
                continue

            path = conflict["path"]
            clean_path = conflict.get("visual_path") or os.sep.join(path)
            merged_version = conflict.get("merged_value")
            existing_resolution = existing_resolutions.get(clean_path)
            auto_merged = conflict.get("can_auto_merge")
            fk = conflict.get("file_key")
            index_in_resource[fk] = index_in_resource.get(fk, 0) + 1
            idx = index_in_resource[fk]
            total = int(conflict.get("conflicts_in_resource") or 1)
            heavy = _is_heavy_content(conflict)
            print_merge_conflict_interactive_header(
                field_path=clean_path,
                resource_key=fk,
                conflict_index=idx,
                conflict_total=total,
                auto_mergeable=auto_merged,
                heavy=heavy,
                base_value=str(conflict.get("baseValue", "")),
                branch_label=branch_label,
                branch_value=str(conflict.get("theirsValue", "")),
                main_value=str(conflict.get("oursValue", "")),
                existing_resolution=existing_resolution,
            )

            choices: list[dict[str, str]] = []
            if existing_resolution:
                er_strategy = existing_resolution.get("strategy", "")
                er_value = existing_resolution.get("value")
                if er_value is not None:
                    er_label = (
                        er_value if isinstance(er_value, str) and "\n" not in er_value else "value"
                    )
                else:
                    er_label = er_strategy
                choices.append({"name": f"Use resolution: {er_label}", "value": "existing"})
            if auto_merged:
                choices.append({"name": "Accept auto-merge", "value": "merged"})
            choices.extend(
                [
                    {"name": "Use main", "value": "ours"},
                    {"name": f"Use branch — {branch_label}", "value": "theirs"},
                    {"name": "Use original (base)", "value": "base"},
                ]
            )
            original = conflict.get("theirsValue", conflict.get("oursValue"))
            if not isinstance(original, dict):
                choices.append({"name": "Edit manually", "value": "edit"})

            extension = ".py" if path[-1] == "code" else ".txt"

            while True:
                answer = questionary.select("Select resolution", choices=choices).ask()
                if answer is None:
                    return []
                if answer == "existing":
                    resolutions.append(existing_resolution)
                    break
                if answer == "merged":
                    resolutions.append(_auto_merge_resolution(path, merged_version))
                    break
                if answer == "edit":
                    if isinstance(original, (bool, int, float, list)):
                        edited_val = prompt_typed_edit(original)
                        if edited_val is None:
                            return []
                        resolutions.append(
                            {"path": path, "value": edited_val, "strategy": "theirs"}
                        )
                        break

                    try:
                        if heavy and merged_version is not None:
                            edited = edit_in_editor(
                                merged_version, extension=extension, filename=fk
                            )
                        else:
                            edited_q = questionary.text(
                                "Custom resolution",
                                default=str(conflict.get("theirsValue", "")),
                                multiline=True,
                            ).ask()
                            if edited_q is None:
                                return []
                            edited = edited_q
                    except FileNotFoundError:
                        warning(
                            "Could not open the configured editor. Check your $EDITOR or "
                            "$VISUAL setting, then try Edit again."
                        )
                        continue
                    except subprocess.CalledProcessError:
                        warning(
                            "The editor exited with an error. Fix the issue and try Edit "
                            "again, or choose another resolution."
                        )
                        continue
                    except ValueError:
                        warning(
                            "Editor closed without saving; choose another option or try Edit again."
                        )
                        continue

                    if contains_merge_conflict(edited):
                        warning(
                            "Edited version still contains merge conflict markers. "
                            "Resolve them before continuing."
                        )
                        continue

                    resolutions.append({"path": path, "value": edited, "strategy": "theirs"})
                    break

                resolutions.append({"path": path, "strategy": answer})
                break

        return resolutions

    @classmethod
    def branch_merge(
        cls,
        base_path: str,
        message: str = None,
        output_json: bool = False,
        interactive: bool = False,
        resolutions_file: str = None,
        force: bool = False,
    ):
        """Merge the current branch into main, with optional conflict resolutions."""
        import questionary

        from poly.output.console import (
            console,
            error,
            info,
            output_merge_conflict_table,
            plain,
            success,
            warning,
        )

        if interactive and output_json:
            json_print(
                {
                    "success": False,
                    "error": "--interactive and --json cannot be used together.",
                }
            )
            sys.exit(1)

        file_resolutions: list[dict[str, Any]] | None = None
        if resolutions_file:
            try:
                if resolutions_file == "-":
                    file_resolutions = json.load(sys.stdin)
                elif resolutions_file.lstrip().startswith("["):
                    file_resolutions = json.loads(resolutions_file)
                else:
                    with open(resolutions_file, encoding="utf-8") as f:
                        file_resolutions = json.load(f)
                if not isinstance(file_resolutions, list):
                    raise ValueError("Resolutions must be a JSON array.")
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                if output_json:
                    json_print({"success": False, "error": f"Failed to parse resolutions: {exc}"})
                else:
                    error(f"Failed to parse resolutions: {exc}")
                sys.exit(1)

        project = load_project(base_path, output_json=output_json)

        current_branch_name, branches = project.get_branches()
        current_branch_meta = branches.get(current_branch_name, {})
        parent_branch_id = current_branch_meta.get("parentBranchId") or None
        parent_branch_name = next(
            (name for name, meta in branches.items() if meta.get("branchId") == parent_branch_id),
            "main",
        )

        if parent_branch_name == "main" and (
            message is None or (isinstance(message, str) and not message.strip())
        ):
            if output_json:
                json_print(
                    {"success": False, "error": "Merge message is required when merging into main."}
                )
            else:
                error("Merge message is required when merging into main.")
            sys.exit(1)

        is_live_deploy = parent_branch_name == "main" and project.using_simplified_deployments

        def _report_merge_success() -> None:
            if is_live_deploy:
                success(
                    f"Branch '{current_branch_name}' merged into main — your changes are now live."
                )
            else:
                success(f"Branch '{current_branch_name}' merged successfully.")
            info(f"Switched to '{parent_branch_name}' branch after merge.")

        if is_live_deploy:
            if not output_json and not force:
                warning("Merging into 'main' will deploy changes into live environment")
                if not questionary.confirm(
                    "Confirm Deployment?", default=False, auto_enter=False
                ).ask():
                    warning("Aborted.")
                    sys.exit(0)

        ctx = (
            console.status(
                f"[info]Merging branch '{current_branch_name}' into '{parent_branch_name}'...[/info]"
            )
            if not output_json
            else nullcontext()
        )
        with ctx:
            merge_success, conflicts, errors = project.merge_branch(
                message=message, conflict_resolutions=file_resolutions
            )

        if output_json:
            output = {"success": merge_success}
            if conflicts or errors:
                output["conflicts"] = conflicts
                output["errors"] = errors
            json_print(output)
            if not merge_success:
                sys.exit(1)
            return

        if merge_success:
            _report_merge_success()
            return

        # Failed branch merge
        error(f"Failed to merge branch '{current_branch_name}'.")
        if errors:
            plain("\n[red]Errors:[/red]")
            for err in errors:
                error(f"- {err['path']}: {err['message']}")
            if _is_sequence_mismatch(errors):
                warning(
                    "The branch changed while merging (e.g. a draft deployment finished). "
                    "Re-run the merge."
                )

        enriched = enrich_branch_merge_conflicts(conflicts) if conflicts else []
        display_conflict = [
            c for c in enriched if c.get("path") and c["path"][-1] not in {"updatedAt", "createdAt"}
        ]
        if display_conflict:
            output_merge_conflict_table(
                display_conflict, show_type=True, resolutions=file_resolutions
            )

        if errors:
            sys.exit(1)

        if not interactive:
            plain(
                "Merge conflicts detected. To resolve:\n"
                "- Use 'poly branch merge -i <message>' to resolve conflicts interactively\n"
                "- Use 'poly branch merge --resolutions <file.json> <message>' to provide pre-defined resolutions\n"
                "- Merge manually on Agent Studio"
            )
            sys.exit(1)

        existing_resolutions = {
            os.sep.join(r["path"]): r for r in (file_resolutions or []) if "path" in r
        }
        while True:
            resolutions = cls._merge_interactively(
                enriched, existing_resolutions, current_branch_name
            )
            if not resolutions:
                warning("No resolutions provided. Exiting.")
                sys.exit(1)
            ctx2 = (
                console.status("[info]Merging branch...[/info]")
                if not output_json
                else nullcontext()
            )
            with ctx2:
                merge_success, conflicts, errors = project.merge_branch(
                    message=message, conflict_resolutions=resolutions
                )
            if merge_success:
                _report_merge_success()
                break
            if errors:
                error(f"Failed to merge branch '{current_branch_name}' after conflict resolution.")
                plain("\n[red]Errors:[/red]")
                for err in errors:
                    error(f"- {err['path']}: {err['message']}")
                sys.exit(1)
            if not conflicts:
                error(
                    f"Failed to merge branch '{current_branch_name}' after conflict resolution "
                    "(no conflicts or errors returned)."
                )
                sys.exit(1)
            warning("Merge still blocked; resolve the remaining conflicts below.")
            enriched = enrich_branch_merge_conflicts(conflicts)
            display_conflict = [
                c
                for c in enriched
                if c.get("path") and c["path"][-1] not in {"updatedAt", "createdAt"}
            ]
            if display_conflict:
                output_merge_conflict_table(
                    display_conflict,
                    show_type=True,
                    panel_title="Remaining merge conflicts",
                )

    @classmethod
    def branch_diff(
        cls,
        base_path: str,
        branch_name: str = None,
        files: list[str] = None,
        output_json: bool = False,
    ) -> None:
        """Show changes made on a branch since it was created."""
        from poly.output.console import console, error, plain, print_diff

        project = load_project(base_path, output_json=output_json)

        try:
            diffs = project.diff_branch(branch_name=branch_name, file_paths=files)
        except ValueError as e:
            if output_json:
                json_print({"success": False, "error": str(e)})
            else:
                error(str(e))
            sys.exit(1)

        if not diffs:
            if output_json:
                json_print({"success": True, "diffs": {}})
            else:
                plain("[muted]No changes detected on this branch.[/muted]")
            return

        if output_json:
            json_print({"success": True, "diffs": diffs})
            return

        for file_path, diff_text in diffs.items():
            console.rule(f"[bold]{file_path}[/bold]")
            print_diff(diff_text)

    @classmethod
    def branch_review(
        cls,
        base_path: str,
        branch_name: str = None,
        files: list[str] = None,
        output_json: bool = False,
    ) -> None:
        """Create a GitHub Gist of branch changes since it was created."""
        import requests as req

        from poly.handlers.github_api_handler import GitHubAPIHandler
        from poly.output.console import error, plain, success

        project = load_project(base_path, output_json=output_json)

        try:
            diffs = project.diff_branch(branch_name=branch_name, file_paths=files)
        except ValueError as e:
            if output_json:
                json_print({"success": False, "error": str(e)})
            else:
                error(str(e))
            sys.exit(1)

        if not diffs:
            if output_json:
                json_print({"success": False, "message": "No changes to review."})
            else:
                plain("[muted]No changes detected on this branch.[/muted]")
            return

        project_name = "/".join(os.path.abspath(base_path).split(os.sep)[-2:])
        display_name = branch_name or project.get_current_branch() or project.branch_id
        description = f"Poly ADK: {project_name}: branch '{display_name}' review"

        body = {}
        for file_path, diff in diffs.items():
            if not diff:
                continue
            safe_name = file_path.replace(os.sep, "_")
            body[f"{safe_name}.diff"] = {"content": diff}

        try:
            url = GitHubAPIHandler.create_gist(
                files=body,
                description=description,
                public=False,
            )
            if output_json:
                json_print({"success": True, "link": url})
            else:
                success(f"Review gist created: {url}")
        except req.HTTPError as e:
            if output_json:
                json_print({"success": False, "message": f"GitHub API error: {e}"})
            else:
                error(f"GitHub API error: {e}")
        except OSError as e:
            if output_json:
                json_print({"success": False, "message": str(e)})
            else:
                error(str(e))

    @classmethod
    def branch_status(
        cls,
        base_path: str,
        branch_name: str = None,
        output_json: bool = False,
    ) -> None:
        """Show what changed on a branch relative to its fork point."""
        from poly.cli_commands.shared import resolve_account_name
        from poly.output.console import error, plain, print_file_list, print_status

        project = load_project(base_path, output_json=output_json)
        resolve_account_name(project)

        current_branch_name, branches = project.get_branches()
        target_name = branch_name or current_branch_name
        branch_meta = branches.get(target_name, {}) if target_name else {}

        parent_branch_id = branch_meta.get("parentBranchId")
        parent_name = next(
            (name for name, meta in branches.items() if meta.get("branchId") == parent_branch_id),
            parent_branch_id,
        )
        created_by = branch_meta.get("createdBy")
        is_diverged = branch_meta.get("isDiverged")

        try:
            new_files, modified_files, deleted_files = project.branch_status(
                branch_name=branch_name
            )
        except ValueError as e:
            if output_json:
                json_print({"success": False, "error": str(e)})
            else:
                error(str(e))
            sys.exit(1)

        if output_json:
            json_print(
                {
                    "branch": target_name,
                    "parent_branch": parent_name,
                    "created_by": created_by,
                    "is_diverged": is_diverged,
                    "new_files": new_files,
                    "modified_files": modified_files,
                    "deleted_files": deleted_files,
                }
            )
            return

        print_status(
            region=project.region,
            account_id=project.account_id,
            project_id=project.project_id,
            last_updated=project.last_updated.isoformat(),
            branch=target_name,
            account_name=project.account_name,
            project_name=project.project_name,
            parent_branch=parent_name,
            created_by=created_by,
            is_diverged=is_diverged,
            title="Branch Status",
        )

        print_file_list("New files", new_files, "filename.new")
        print_file_list("Deleted files", deleted_files, "filename.deleted")
        print_file_list("Modified files", modified_files, "filename.modified")

        if not new_files and not modified_files and not deleted_files:
            plain("\n[muted]No changes on this branch.[/muted]")

    @classmethod
    def branch_sync(
        cls,
        base_path: str,
        output_json: bool = False,
        interactive: bool = False,
        resolutions_file: str = None,
    ):
        """Sync the current branch with it's parent, with optional conflict resolutions."""
        from poly.cli_commands.shared import require_deployment_simplification
        from poly.output.console import (
            console,
            error,
            output_merge_conflict_table,
            plain,
            success,
            warning,
        )

        if interactive and output_json:
            json_print(
                {
                    "success": False,
                    "error": "--interactive and --json cannot be used together.",
                }
            )
            sys.exit(1)

        file_resolutions: list[dict[str, Any]] | None = None
        if resolutions_file:
            try:
                if resolutions_file == "-":
                    file_resolutions = json.load(sys.stdin)
                elif resolutions_file.lstrip().startswith("["):
                    file_resolutions = json.loads(resolutions_file)
                else:
                    with open(resolutions_file, encoding="utf-8") as f:
                        file_resolutions = json.load(f)
                if not isinstance(file_resolutions, list):
                    raise ValueError("Resolutions must be a JSON array.")
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                if output_json:
                    json_print({"success": False, "error": f"Failed to parse resolutions: {exc}"})
                else:
                    error(f"Failed to parse resolutions: {exc}")
                sys.exit(1)

        project = load_project(base_path, output_json=output_json)

        require_deployment_simplification(project, output_json=output_json)

        branch_name = project.get_current_branch()
        ctx = console.status("[info]Syncing branch...[/info]") if not output_json else nullcontext()
        with ctx:
            merge_success, conflicts, errors = project.sync_branch(
                conflict_resolutions=file_resolutions
            )

        if output_json:
            output = {"success": merge_success}
            if conflicts or errors:
                output["conflicts"] = conflicts
                output["errors"] = errors
            json_print(output)
            if not merge_success:
                sys.exit(1)
            return

        if merge_success:
            success(f"Branch '{branch_name}' synced successfully.")
            return

        # Failed branch sync
        error(f"Failed to sync branch '{branch_name}'.")
        if errors:
            plain("\n[red]Errors:[/red]")
            for err in errors:
                error(f"- {err['path']}: {err['message']}")
            if _is_sequence_mismatch(errors):
                warning(
                    "The branch changed while syncing (e.g. a draft deployment finished). "
                    "Re-run the sync."
                )

        enriched = enrich_branch_merge_conflicts(conflicts) if conflicts else []
        display_conflict = [
            c for c in enriched if c.get("path") and c["path"][-1] not in {"updatedAt", "createdAt"}
        ]
        if display_conflict:
            output_merge_conflict_table(
                display_conflict, show_type=True, resolutions=file_resolutions
            )

        if errors:
            sys.exit(1)

        if not interactive:
            plain(
                "Merge conflicts detected. To resolve:\n"
                "- Use 'poly branch sync -i' to resolve conflicts interactively\n"
                "- Use 'poly branch sync --resolutions <file.json>' to provide pre-defined resolutions\n"
                "- Merge manually on Agent Studio"
            )
            sys.exit(1)

        existing_resolutions = {
            os.sep.join(r["path"]): r for r in (file_resolutions or []) if "path" in r
        }
        while True:
            resolutions = cls._merge_interactively(enriched, existing_resolutions, branch_name)
            if not resolutions:
                warning("No resolutions provided. Exiting.")
                sys.exit(1)
            ctx2 = (
                console.status("[info]Sync branch...[/info]") if not output_json else nullcontext()
            )
            with ctx2:
                merge_success, conflicts, errors = project.sync_branch(
                    conflict_resolutions=resolutions
                )
            if merge_success:
                success(f"Branch '{branch_name}' synced successfully.")
                break
            if errors:
                error(f"Failed to sync branch '{branch_name}' after conflict resolution.")
                plain("\n[red]Errors:[/red]")
                for err in errors:
                    error(f"- {err['path']}: {err['message']}")
                sys.exit(1)
            if not conflicts:
                error(
                    f"Failed to sync branch '{branch_name}' after conflict resolution "
                    "(no conflicts or errors returned)."
                )
                sys.exit(1)
            warning("Sync still blocked; resolve the remaining conflicts below.")
            enriched = enrich_branch_merge_conflicts(conflicts)
            display_conflict = [
                c
                for c in enriched
                if c.get("path") and c["path"][-1] not in {"updatedAt", "createdAt"}
            ]
            if display_conflict:
                output_merge_conflict_table(
                    display_conflict,
                    show_type=True,
                    panel_title="Remaining merge conflicts",
                )

    @classmethod
    def branch_history(
        cls,
        base_path: str,
        branch_name: Optional[str] = None,
        output_json: bool = False,
        limit: Optional[int] = None,
    ) -> None:
        """Show the history of a branch in the Agent Studio project."""
        from poly.output.console import paged_output, plain, print_branch_history, warning

        project = load_project(base_path, output_json=output_json)

        current_branch, branches = project.get_branches()
        if not branch_name:
            branch_name = current_branch

        if not branch_name:
            if output_json:
                json_print(
                    {
                        "success": False,
                        "error": "No current branch found. Please specify a branch name.",
                    }
                )
            else:
                warning("No current branch found. Please specify a branch name.")
            return

        branch_id = branches.get(branch_name, {}).get("branchId")
        if not branch_id:
            if output_json:
                json_print({"success": False, "error": f"Branch '{branch_name}' does not exist."})
            else:
                warning(f"Branch '{branch_name}' does not exist.")
            return

        history = project.get_branch_history(branch_id)
        if limit is not None:
            history = history[:limit]

        if output_json:
            json_print({"branch_name": branch_name, "branch_id": branch_id, "history": history})
            return

        if not history:
            plain(f"[muted]No history found for branch '{branch_name}'.[/muted]")
            return

        with paged_output():
            plain(f"History for branch '{branch_name}':")
            print_branch_history(history)

    @classmethod
    def branch_rename(
        cls, base_path: str, new_branch_name: Optional[str] = None, output_json: bool = False
    ) -> None:
        """Rename the current branch in the Agent Studio project."""
        from poly.output.console import error, success, warning

        project = load_project(base_path, output_json=output_json)

        current_branch = project.get_current_branch()
        if not current_branch:
            if output_json:
                json_print(
                    {
                        "success": False,
                        "error": "Current branch doesn't exist. Create a new branch before renaming.",
                    }
                )
            else:
                warning("Current branch doesn't exist. Create a new branch before renaming.")
            return

        if current_branch == "main":
            if output_json:
                json_print({"success": False, "error": "Cannot rename the main branch."})
            else:
                error("Cannot rename the main branch.")
            return

        if not new_branch_name:
            if output_json:
                json_print({"success": False, "error": "No new branch name provided."})
            else:
                new_branch_name = input("Enter the new name for the current branch: ").strip()
                if not new_branch_name:
                    warning("No new branch name provided. Exiting.")
                    return

        try:
            renamed = project.rename_branch(new_branch_name)
        except ValueError as e:
            if output_json:
                json_print({"success": False, "error": str(e)})
            else:
                error(str(e))
            sys.exit(1)

        if output_json:
            json_print(
                {
                    "success": renamed,
                    "old_branch_name": current_branch,
                    "new_branch_name": new_branch_name,
                }
            )
        else:
            if renamed:
                success(f"Renamed branch '{current_branch}' to '{new_branch_name}'.")
            else:
                error(f"Failed to rename branch '{current_branch}' to '{new_branch_name}'.")

    @classmethod
    def branch_restore(
        cls,
        base_path: str,
        branch_id: Optional[str] = None,
        output_json: bool = False,
    ) -> None:
        """Restore a soft-deleted branch from the archive, by branch id or name."""
        import questionary

        from poly.output.console import (
            error,
            plain,
            resolve_parent_branch_label,
            success,
            warning,
        )

        project = load_project(base_path, output_json=output_json)

        if not branch_id:
            if output_json:
                json_print(
                    {
                        "success": False,
                        "error": "branch restore with --json requires a branch id argument.",
                    }
                )
                sys.exit(1)

            archived = project.list_archived_branches()
            if not archived:
                plain("[muted]No archived branches to restore.[/muted]")
                return

            name_by_branch_id = _build_branch_name_lookup(project, archived)
            archived_branch_ids = {b["branchId"] for b in archived if b.get("branchId")}
            choices = []
            branch_by_label: dict[str, dict[str, Any]] = {}
            for b in archived:
                name = b.get("name", "—")
                archived_branch_id = b.get("branchId", "")
                parent = resolve_parent_branch_label(b, name_by_branch_id, archived_branch_ids)
                # Names repeat across the archive, so the id and parent are what
                # actually let the user tell two same-named entries apart.
                label = f"{name} ({archived_branch_id}) — parent: {parent}"
                choices.append(label)
                branch_by_label[label] = b

            selected = questionary.select(
                "Select branch to restore",
                choices=choices,
                use_search_filter=True,
                use_jk_keys=False,
            ).ask()
            if not selected:
                warning("No branch selected. Exiting.")
                return

            selected_branch = branch_by_label[selected]
            try:
                restored = project.restore_branch(selected_branch["branchId"])
            except ValueError as e:
                error(str(e))
                sys.exit(1)
            if restored:
                success(f"Branch '{selected_branch.get('name', '—')}' restored.")
            else:
                error("Failed to restore selected branch.")
            return

        try:
            restored = project.restore_branch(branch_id)
        except ValueError as e:
            if output_json:
                json_print({"success": False, "error": str(e)})
            else:
                error(str(e))
            sys.exit(1)

        if output_json:
            json_print({"success": restored, "branch_id": branch_id})
        else:
            if restored:
                success(f"Branch '{branch_id}' restored.")
            else:
                error(f"Failed to restore branch '{branch_id}'.")

    @classmethod
    def branch_tag(
        cls,
        base_path: str,
        output_json: bool = False,
    ) -> None:
        """Tag the current branch with a new tag."""
        from poly.cli_commands.shared import require_deployment_simplification
        from poly.output.console import error, success

        project = load_project(base_path, output_json=output_json)
        require_deployment_simplification(project, output_json=output_json)

        tagged = project.tag_branch()

        if output_json:
            json_print({"success": tagged})
        else:
            if tagged:
                success(
                    f"Current branch '{project.get_current_branch()}' tagged and deployed to staging."
                )
            else:
                error("Failed to tag the current branch.")

    @classmethod
    def branch_untag(
        cls,
        base_path: str,
        output_json: bool = False,
    ) -> None:
        """Remove a tag from the current branch."""
        from poly.cli_commands.shared import require_deployment_simplification
        from poly.output.console import error, success

        project = load_project(base_path, output_json=output_json)
        require_deployment_simplification(project, output_json=output_json)

        untagged = project.untag_branch()

        if output_json:
            json_print({"success": untagged})
        else:
            if untagged:
                success(
                    f"Staging tag removed from current branch '{project.get_current_branch()}'."
                )
            else:
                error("Failed to remove tag from the current branch.")
