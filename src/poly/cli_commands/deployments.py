"""Deployments command family: manage deployments and A/B tests.

Copyright PolyAI Limited
"""

import logging
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Any, Optional

from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.output.json_output import json_print
from poly.project import AgentStudioProject

logger = logging.getLogger(__name__)


class DeploymentsCommand(BaseCommand):
    """Manage deployments and A/B tests for the project."""

    command = "deployments"

    group = BUILDER_API_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``deployments`` subcommand tree."""
        deployments_parser = subparsers.add_parser(
            "deployments",
            parents=[parents.verbose],
            help="Manage deployments for the project.",
            description=(
                "Manage deployments for the project.\n\nExamples:\n  poly deployments list\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )

        deployments_subparsers = deployments_parser.add_subparsers(
            dest="deployments_subcommand", required=True
        )

        deployment_list_parser = deployments_subparsers.add_parser(
            "list",
            parents=[parents.path, parents.json, parents.verbose],
            help="List deployments for the project.",
            description=(
                "List deployments for the project.\n\n"
                "Examples:\n"
                "  poly deployments list\n"
                "  poly deployments list --env live\n"
                "  poly deployments list --details\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        deployment_list_parser.add_argument(
            "--env",
            "-e",
            type=str,
            default=None,
            choices=["sandbox", "pre-release", "live"],
            help=(
                "Environment to list deployments for. Defaults to live for projects using"
                " simplified deployments, otherwise sandbox."
            ),
        )
        deployment_list_parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of versions to show. Shows all by default.",
        )
        deployment_list_parser.add_argument(
            "--offset",
            type=int,
            default=0,
            help="Number of versions to skip. Defaults to 0.",
        )
        deployment_list_parser.add_argument(
            "--hash",
            type=str,
            help="Hash of the version to start from.",
        )
        deployment_list_parser.add_argument(
            "--details",
            action="store_true",
            help="Output each deployment with detailed information.",
        )

        deployment_show_parser = deployments_subparsers.add_parser(
            "show",
            parents=[parents.path, parents.json],
            help="Show details for a specific deployment.",
            description=(
                "Show detailed metadata and included deployments for a specific"
                " version.\n\n"
                "Examples:\n"
                "  poly deployments show abc123def\n"
                "  poly deployments show abc123def --env live\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        deployment_show_parser.add_argument(
            "hash",
            type=str,
            help="Version hash (or prefix) of the deployment to show.",
        )
        deployment_show_parser.add_argument(
            "--env",
            "-e",
            type=str,
            default=None,
            choices=["sandbox", "pre-release", "live"],
            help=(
                "Environment to query. Defaults to live for projects using simplified"
                " deployments, otherwise sandbox."
            ),
        )

        deployment_promote_parser = deployments_subparsers.add_parser(
            "promote",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="Promote a deployment to the next environment.",
            description=(
                "Promote a deployment to the next environment.\n\nExamples:\n  poly deployments promote --from <deployment_id> --to <target_env>\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        deployment_promote_parser.add_argument(
            "--from",
            dest="from_deployment",
            type=str,
            required=True,
            help="ID/env of the deployment to promote.",
        )
        deployment_promote_parser.add_argument(
            "--to",
            dest="to_env",
            type=str,
            required=True,
            choices=["pre-release", "live"],
            help="Target environment to promote to.",
        )
        deployment_promote_parser.add_argument(
            "--message",
            "-m",
            type=str,
            required=False,
            help="Optional message to include with the promotion (e.g. release notes or changelog). If not specified, current deployment message will be used instead",
        )
        deployment_promote_parser.add_argument(
            "--force",
            action="store_true",
            help="Force the promotion without confirmation. When used, the existing deployment message is kept unless --message is provided. This is default in non-interactive mode (e.g. when --json is used)",
        )
        deployment_promote_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be promoted without actually promoting. Displays the deployment hash, target environment, and changes included.",
        )

        deployment_rollback_parser = deployments_subparsers.add_parser(
            "rollback",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="Rollback main to a previous version.",
            description=(
                "Rollback a deployment to a previous version.\n\n"
                "Targets live for projects using simplified deployments, otherwise"
                " sandbox.\n\nExamples:\n  poly deployments rollback --to <deployment_id>\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        deployment_rollback_parser.add_argument(
            "--to",
            dest="to_deployment",
            type=str,
            required=True,
            help="ID/env of the deployment to rollback to.",
        )
        deployment_rollback_parser.add_argument(
            "--message",
            "-m",
            type=str,
            required=False,
            help="Optional message to include with the rollback (e.g. release notes or changelog). If not specified, current deployment message will be used instead",
        )
        deployment_rollback_parser.add_argument(
            "--force",
            action="store_true",
            help="Force the rollback without confirmation. When used, the existing deployment message is kept unless --message is provided. This is default in non-interactive mode (e.g. when --json is used)",
        )
        deployment_rollback_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be rolled back without actually rolling back. Displays the target deployment and reverted deployments.",
        )

        # A/B TESTS
        ab_test_parser = deployments_subparsers.add_parser(
            "ab-test",
            parents=[parents.verbose],
            help="Manage A/B tests for live deployments.",
            description=(
                "Manage A/B tests for live deployments.\n\n"
                "Examples:\n"
                "  poly deployments ab-test start --name 'v2 test'"
                " --variant-version <hash> --traffic 50\n"
                "  poly deployments ab-test list\n"
                "  poly deployments ab-test active\n"
                "  poly deployments ab-test update --traffic 30\n"
                "  poly deployments ab-test end\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        ab_test_subparsers = ab_test_parser.add_subparsers(dest="ab_test_subcommand", required=True)

        ab_test_start_parser = ab_test_subparsers.add_parser(
            "start",
            parents=[parents.path, parents.json, parents.verbose],
            help="Start a new A/B test.",
            description=(
                "Start a new A/B test against the current live deployment.\n\n"
                "The variant must be a pre-release deployment. Traffic percentage\n"
                "controls what fraction of calls route to the variant (0-100).\n\n"
                "Examples:\n"
                "  poly deployments ab-test start"
                " --name 'v2 test' --variant-version <hash> --traffic 50\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        ab_test_start_parser.add_argument(
            "--name",
            "-n",
            type=str,
            default=None,
            help="Name/label for the A/B test. If omitted, prompts interactively.",
        )
        ab_test_start_parser.add_argument(
            "--variant-version",
            type=str,
            default=None,
            help="Version hash of the pre-release variant. If omitted, prompts interactively.",
        )
        ab_test_start_parser.add_argument(
            "--traffic",
            type=int,
            default=None,
            help="Percentage of traffic to route to the variant (0-100). Defaults to 50 interactively.",
        )

        ab_test_list_parser = ab_test_subparsers.add_parser(
            "list",
            parents=[parents.path, parents.json, parents.verbose],
            help="List A/B tests for the project.",
            description=(
                "List A/B tests for the project.\n\n"
                "Examples:\n"
                "  poly deployments ab-test list\n"
                "  poly deployments ab-test list --limit 20\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        ab_test_list_parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Number of A/B tests to show. Defaults to 10.",
        )

        ab_test_subparsers.add_parser(
            "active",
            parents=[parents.path, parents.json, parents.verbose],
            help="Show the currently active A/B test.",
            description="Show the currently active A/B test, if any.",
            formatter_class=RawTextHelpFormatter,
        )

        ab_test_update_parser = ab_test_subparsers.add_parser(
            "update",
            parents=[parents.path, parents.json, parents.verbose],
            help="Update traffic percentage for an active A/B test.",
            description=(
                "Update the traffic split for the active A/B test.\n\n"
                "Examples:\n"
                "  poly deployments ab-test update --traffic 30\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        ab_test_update_parser.add_argument(
            "--traffic",
            type=int,
            default=None,
            help="New percentage of traffic to route to the variant (0-100). Prompts if omitted.",
        )

        ab_test_end_parser = ab_test_subparsers.add_parser(
            "end",
            parents=[parents.path, parents.json, parents.verbose],
            help="End an active A/B test and choose a winner.",
            description=(
                "End the active A/B test and choose which deployment wins.\n\n"
                "If --chosen-version is omitted, an interactive prompt\n"
                "shows the control and variant deployments for selection.\n\n"
                "Examples:\n"
                "  poly deployments ab-test end"
                " --chosen-version <hash>\n"
                "  poly deployments ab-test end   # interactive\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        ab_test_end_parser.add_argument(
            "--chosen-version",
            type=str,
            default=None,
            help="Version hash of the deployment to keep as winner. If omitted, prompts interactively.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the matching deployments sub-handler."""
        if args.deployments_subcommand == "list":
            cls.deployments_list(
                args.path,
                args.env,
                args.limit,
                args.offset,
                args.hash,
                args.json,
                args.details,
            )
        elif args.deployments_subcommand == "show":
            cls.deployments_show(
                args.path,
                args.hash,
                args.env,
                args.json,
            )
        elif args.deployments_subcommand == "promote":
            cls.deployments_promote(
                args.path,
                args.from_deployment,
                args.to_env,
                args.message,
                force=args.force,
                output_json=args.json,
                dry_run=args.dry_run,
            )
        elif args.deployments_subcommand == "rollback":
            cls.deployments_rollback(
                args.path,
                args.to_deployment,
                args.message,
                force=args.force,
                output_json=args.json,
                dry_run=args.dry_run,
            )
        elif args.deployments_subcommand == "ab-test":
            if args.ab_test_subcommand == "start":
                cls.ab_test_start(
                    args.path,
                    args.name,
                    args.variant_version,
                    args.traffic,
                    output_json=args.json,
                )
            elif args.ab_test_subcommand == "list":
                cls.ab_test_list(
                    args.path,
                    args.limit,
                    output_json=args.json,
                )
            elif args.ab_test_subcommand == "active":
                cls.ab_test_active(args.path, output_json=args.json)
            elif args.ab_test_subcommand == "update":
                cls.ab_test_update(
                    args.path,
                    args.traffic,
                    output_json=args.json,
                )
            elif args.ab_test_subcommand == "end":
                cls.ab_test_end(
                    args.path,
                    chosen_version=args.chosen_version,
                    output_json=args.json,
                )

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _resolve_included_deployments(
        sandbox_versions: list[dict[str, Any]],
        target_hash: str,
        predecessor_hash: str | None,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Slice sandbox history to find deployments between two versions.

        For promotions (target is newer), returns deployments from target
        to predecessor (target inclusive, predecessor exclusive).
        For rollbacks (target is older), returns deployments from predecessor
        to target (predecessor inclusive, target exclusive) — the versions
        being reverted.

        Args:
            sandbox_versions: Full sandbox deployment list (newest first).
            target_hash: Version hash of the target deployment.
            predecessor_hash: Version hash of the deployment being replaced
                in the target env, or None if this is the first deployment.

        Returns:
            Tuple of (included deployments, is_rollback).
        """
        target_idx = next(
            (i for i, v in enumerate(sandbox_versions) if v.get("version_hash") == target_hash),
            None,
        )
        if target_idx is None:
            return [], False

        if not predecessor_hash:
            return sandbox_versions[target_idx:], False

        pred_idx = next(
            (
                i
                for i, v in enumerate(sandbox_versions)
                if v.get("version_hash") == predecessor_hash
            ),
            None,
        )
        if pred_idx is None:
            return sandbox_versions[target_idx:], False

        if pred_idx < target_idx:
            return sandbox_versions[pred_idx:target_idx], True

        return sandbox_versions[target_idx:pred_idx], False

    @staticmethod
    def _default_ab_test_name() -> str:
        """Generate a default A/B test name matching the Agent Studio UI format."""
        from datetime import datetime

        now = datetime.now()
        day = now.day
        if 11 <= day <= 13:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix} {now.strftime('%B %Y')} Test {now.strftime('%H:%M')}"

    @staticmethod
    def _fetch_deployment_map(project: AgentStudioProject) -> dict[str, dict]:
        """Build a deployment ID → deployment dict map for display enrichment."""
        dep_map: dict[str, dict] = {}
        try:
            for env in ("live", "pre-release"):
                deps, _ = project.get_deployments(client_env=env)
                for dep in deps:
                    if dep.get("id"):
                        dep_map[dep["id"]] = dep
        except Exception as e:
            logger.debug("Failed to fetch deployments for A/B test display: %s", e)
        return dep_map

    @staticmethod
    def _resolve_version_to_deployment_id(
        version_hash: str,
        deployments: list[dict],
    ) -> str | None:
        """Resolve a version hash (or prefix) to a deployment ID.

        Args:
            version_hash: Full or 9-char prefix of a version hash.
            deployments: List of deployment dicts with 'id' and 'version_hash' keys.

        Returns:
            The deployment ID if exactly one match is found, else None.
        """
        prefix = version_hash[:9]
        matches = [dep for dep in deployments if (dep.get("version_hash") or "")[:9] == prefix]
        if len(matches) == 1:
            return matches[0].get("id")
        return None

    # ── deployment handlers ─────────────────────────────────────────

    @classmethod
    def deployments_list(
        cls,
        base_path: str,
        environment: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        version_hash: str = None,
        output_json: bool = False,
        details: bool = False,
    ) -> None:
        """List deployment history for the project.

        By default shows all deployments for live on projects using simplified
        deployments, and for sandbox otherwise. Pass version_hash to start the listing
        from a specific version. Use details for full per-deployment metadata.

        Args:
            base_path: Base path for the project.
            environment: Environment to query — sandbox, pre-release, or live. Defaults
                to the environment holding the project's deployments.
            limit: Maximum number of versions to show. Shows all by default.
            offset: Number of versions to skip before showing results.
            version_hash: Start listing from this version hash (overrides offset).
            output_json: If True, print result as JSON instead of rich text.
            details: If True, print full metadata for each deployment.
        """
        from poly.output.console import error, paged_output, print_deployments

        project = load_project(base_path, output_json=output_json)
        if environment is None:
            environment = "live" if project.using_simplified_deployments else "sandbox"
        versions, active_deployment_hashes = project.get_deployments(client_env=environment)

        if not versions:
            error("No versions found.")
            return

        if version_hash:
            version_hash = version_hash[:9]
            version_idx = next(
                (
                    i
                    for i, v in enumerate(versions)
                    if (v.get("version_hash") or "")[:9] == version_hash
                ),
                None,
            )
            if version_idx is None:
                error(f"Version hash '{version_hash}' not found.")
                return
            offset = version_idx

        end = offset + limit if limit is not None else None
        versions = versions[offset:end]
        if output_json:
            json_output = {
                "versions": versions,
                "active_deployment_hashes": active_deployment_hashes,
            }
            json_print(json_output)
        else:
            with paged_output():
                print_deployments(versions, active_deployment_hashes, details=details)

    @classmethod
    def deployments_show(
        cls,
        base_path: str,
        version_hash: str,
        environment: Optional[str] = None,
        output_json: bool = False,
    ) -> None:
        """Show detailed metadata and included deployments for a single deployment.

        Displays the deployment record and the sandbox deployments included since the
        previous version in the given environment. Sandbox remains the source of truth
        for the linear version history — pre-release/live promotions carry the same
        version hashes forward. Deployments made under simplified deployments never
        reached sandbox, so nothing is bundled into them and the included list is empty;
        a project's older pre-migration promotions still resolve normally.

        Args:
            base_path: Base path for the project.
            version_hash: Full or prefix hash of the target deployment.
            environment: Environment to query (sandbox, pre-release, live). Defaults to
                the environment holding the project's deployments.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import error, print_deployment_show

        project = load_project(base_path, output_json=output_json)
        if environment is None:
            environment = "live" if project.using_simplified_deployments else "sandbox"
        env_versions, active_deployment_hashes = project.get_deployments(client_env=environment)

        if not env_versions:
            error("No versions found.")
            return

        version_hash = version_hash[:9]
        version_idx = next(
            (
                i
                for i, v in enumerate(env_versions)
                if (v.get("version_hash") or "")[:9] == version_hash
            ),
            None,
        )
        if version_idx is None:
            error(f"Version hash '{version_hash}' not found.")
            return

        deployment = env_versions[version_idx]
        target_full_hash = deployment.get("version_hash", "")

        # Find predecessor in the same environment (next entry in the env list)
        predecessor_full_hash = None
        if version_idx < len(env_versions) - 1:
            predecessor_full_hash = env_versions[version_idx + 1].get("version_hash", "")

        # Resolve included deployments from the environment holding the linear history
        if environment == "sandbox":
            history_versions = env_versions
        else:
            history_versions, _ = project.get_deployments(client_env="sandbox")

        included, is_rollback = cls._resolve_included_deployments(
            history_versions, target_full_hash, predecessor_full_hash
        )

        if output_json:
            json_print(
                {
                    "success": True,
                    "deployment": deployment,
                    "active_deployment_hashes": active_deployment_hashes,
                    "included_deployments": included,
                    "is_rollback": is_rollback,
                }
            )
            return

        print_deployment_show(deployment, active_deployment_hashes, included, is_rollback)

    @classmethod
    def deployments_promote(
        cls,
        base_path: str,
        from_deployment: str,
        to_env: str,
        message: Optional[str] = None,
        force: bool = False,
        output_json: bool = False,
        dry_run: bool = False,
    ) -> None:
        """Promote a deployment to a different environment.

        Args:
            base_path: Base path for the project.
            from_deployment: Version hash of the deployment to promote.
            to_env: Target environment to promote to — pre-release or live.
            force: If True, bypass confirmation prompt.
            message: Optional deployment message to include with the promotion (defaults to original deployment message).
            output_json: If True, print result as JSON instead of rich text.
            dry_run: If True, show what would be promoted without actually promoting.
        """
        import questionary

        from poly.output.console import error, plain, print_deployments, success, warning

        project = load_project(base_path, output_json=output_json)

        result: dict = {"success": False, "to_env": to_env}
        deployment_hash = None

        # Under simplified deployments the sandbox -> pre-release -> live ladder no
        # longer exists: merging to main deploys straight to live, and sandbox is
        # frozen at its pre-migration state. The platform does not reject promotions,
        # so without this guard promoting would republish stale content to production.
        if project.using_simplified_deployments:
            msg = (
                "'poly deployments promote' is not available for projects using simplified"
                " deployments. Merging to main deploys directly to live."
            )
            if output_json:
                json_print({**result, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        if to_env not in ["pre-release", "live"]:
            msg = f"Invalid target environment '{to_env}'. Must be 'pre-release' or 'live'."
            if output_json:
                json_print({**result, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        if to_env == "live":
            search_env = "pre-release"
        else:
            search_env = "sandbox"
        versions, active_deployment_hashes = project.get_deployments(search_env)

        # Resolve from_deployment to full version hash
        if from_deployment in active_deployment_hashes:
            deployment_hash = active_deployment_hashes[from_deployment]
        else:
            deployment_hash = from_deployment

        deployment_version = next(
            (v for v in versions if (v.get("version_hash") or "")[:9] == deployment_hash[:9]),
            None,
        )

        if not deployment_version:
            msg = f"Deployment '{from_deployment}' not found in {search_env}."
            if output_json:
                json_print({**result, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        deployment_metadata = deployment_version.get("deployment_metadata", {})
        deployment_message = deployment_metadata.get("deployment_message")

        result["from_hash"] = deployment_version.get("version_hash", "")
        result["message"] = message or deployment_message or ""

        # Resolve included deployments using sandbox as the linear history
        target_full_hash = deployment_version.get("version_hash", "")
        predecessor_hash = active_deployment_hashes.get(to_env)

        if search_env == "sandbox":
            sandbox_versions = versions
        else:
            sandbox_versions, _ = project.get_deployments("sandbox")

        included, is_rollback = cls._resolve_included_deployments(
            sandbox_versions, target_full_hash, predecessor_hash
        )
        result["included_deployments"] = included

        if not output_json:
            plain(f"Promoting hash [bold]{result['from_hash'][:9]}[/bold] to [info]{to_env}[/info]")
            if is_rollback:
                plain(f"Rolling back to an earlier version: {deployment_message or '-'}")
            elif not predecessor_hash:
                plain(f"First deployment to {to_env}.")
            if included:
                label = "Reverting deployments" if is_rollback else "Included deployments"
                plain(f"{label} ({len(included)}):")
                print_deployments(included, {})

        if dry_run:
            if output_json:
                json_print({**result, "dry_run": True})
            else:
                plain("[dim]Dry run — no changes were made.[/dim]")
            return

        if not output_json and not force:
            if not questionary.confirm(
                "Confirm Deployment?", default=False, auto_enter=False
            ).ask():
                warning("Aborted.")
                sys.exit(0)

            if not message:
                message = questionary.text("Deployment message (default: merge message):").ask()
                result["message"] = message or deployment_message or ""

        try:
            project.promote_deployment(
                deployment_version.get("id"), to_env, message=result["message"]
            )
            if output_json:
                json_print({**result, "success": True})
            else:
                success(f"Deployment {from_deployment} promoted to {to_env}.")
        except Exception as e:
            if output_json:
                json_print({**result, "error": str(e)})
            else:
                error(f"Failed to promote deployment: {e}")
            sys.exit(1)

    @classmethod
    def deployments_rollback(
        cls,
        base_path: str,
        deployment: str,
        message: Optional[str] = None,
        force: bool = False,
        output_json: bool = False,
        dry_run: bool = False,
    ) -> None:
        """Rollback main to a previous deployment.

        Targets live for projects using simplified deployments — where main tracks live
        and the platform only accepts live rollback targets — and sandbox otherwise.
        """
        import questionary

        from poly.output.console import error, plain, print_deployments, success, warning

        project = load_project(base_path, output_json=output_json)

        environment = "live" if project.using_simplified_deployments else "sandbox"
        versions, active_deployment_hashes = project.get_deployments(environment)

        # Resolve deployment to full version hash
        if deployment in active_deployment_hashes:
            deployment_hash = active_deployment_hashes[deployment]
        else:
            deployment_hash = deployment

        deployment_version = next(
            (v for v in versions if v.get("version_hash", "")[:9] == deployment_hash[:9]),
            None,
        )

        if not deployment_version:
            msg = f"Deployment '{deployment}' not found in {environment}."
            if output_json:
                json_print({"success": False, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        deployment_metadata = deployment_version.get("deployment_metadata", {})
        deployment_message = deployment_metadata.get("deployment_message")

        # Resolve reverted deployments (current deployment -> target)
        target_full_hash = deployment_version.get("version_hash", "")
        current_hash = active_deployment_hashes.get(environment)
        reverted, _ = cls._resolve_included_deployments(versions, current_hash, target_full_hash)

        result = {
            "success": False,
            "target_hash": target_full_hash,
            "message": message or deployment_message or "",
            "reverted_deployments": reverted,
        }

        if not output_json:
            plain(
                f"Rolling back {environment} to deployment "
                f"'[bold]{target_full_hash[:9]}[/bold]: {deployment_message or '-'}'"
            )
            if reverted:
                plain(f"Reverting deployments ({len(reverted)}):")
                print_deployments(reverted, {})

        if dry_run:
            if output_json:
                json_print({**result, "dry_run": True})
            else:
                plain("[dim]Dry run — no changes were made.[/dim]")
            return

        if not output_json and not force:
            if not questionary.confirm("Confirm Rollback?", default=False, auto_enter=False).ask():
                warning("Aborted.")
                sys.exit(0)

        try:
            project.rollback_deployment(
                deployment_version.get("id"), message=message or deployment_message or ""
            )
            if output_json:
                json_print({**result, "success": True})
            else:
                success(f"{environment.capitalize()} rolled back to deployment {deployment}.")
        except Exception as e:
            if output_json:
                json_print({**result, "error": str(e)})
            else:
                error(f"Failed to rollback deployment: {e}")
            sys.exit(1)

    # ── A/B tests ────────────────────────────────────────────────────

    @classmethod
    def ab_test_start(
        cls,
        base_path: str,
        name: str | None,
        variant_version: str | None,
        traffic_percentage: int | None,
        output_json: bool = False,
    ) -> None:
        """Start a new A/B test."""
        import questionary

        from poly.output.console import error, print_ab_test_detail, success, warning

        project = load_project(base_path, output_json=output_json)

        # -- name --
        if name is None:
            if output_json:
                msg = "--name is required when using --json."
                json_print({"success": False, "error": msg})
                sys.exit(1)
            default_name = cls._default_ab_test_name()
            name = questionary.text("A/B test name:", default=default_name).ask()
            if name is None:
                warning("Aborted.")
                sys.exit(0)

        if not name.strip():
            msg = "A/B test name is required and cannot be empty."
            if output_json:
                json_print({"success": False, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        # -- variant --
        try:
            pr_deployments, active_hashes = project.get_deployments(client_env="pre-release")
        except Exception as e:
            msg = f"Failed to fetch pre-release deployments: {e}"
            if output_json:
                json_print({"success": False, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        live_version = active_hashes.get("live")

        if variant_version is None:
            if output_json:
                msg = "--variant-version is required when using --json."
                json_print({"success": False, "error": msg})
                sys.exit(1)
            eligible = [dep for dep in pr_deployments if dep.get("version_hash") != live_version]
            if not eligible:
                error(
                    "No eligible pre-release deployments found."
                    " All pre-release versions match the current live version."
                )
                sys.exit(1)
            dep_choices = []
            for dep in eligible:
                dep_id = dep.get("id", "")
                dep_hash = (dep.get("version_hash") or "")[:9]
                dep_msg = (dep.get("deployment_metadata") or {}).get("deployment_message", "") or ""
                label = f"{dep_hash}  {dep_msg}" if dep_msg else dep_hash
                dep_choices.append(questionary.Choice(title=label, value=dep_id))
            variant_deployment_id = questionary.select(
                "Select pre-release deployment (variant):", choices=dep_choices
            ).ask()
            if not variant_deployment_id:
                warning("Aborted.")
                sys.exit(0)
        else:
            variant_deployment_id = cls._resolve_version_to_deployment_id(
                variant_version, pr_deployments
            )
            if not variant_deployment_id:
                msg = f"No pre-release deployment found matching version '{variant_version}'."
                if output_json:
                    json_print({"success": False, "error": msg})
                else:
                    error(msg)
                sys.exit(1)
            matched_dep = next(
                (d for d in pr_deployments if d.get("id") == variant_deployment_id), None
            )
            matched_version = matched_dep.get("version_hash") if matched_dep else None
            if live_version and matched_version and matched_version == live_version:
                msg = (
                    "Variant deployment has the same version as the current live deployment."
                    " An A/B test requires different versions."
                )
                if output_json:
                    json_print({"success": False, "error": msg})
                else:
                    error(msg)
                sys.exit(1)

        # -- traffic --
        if traffic_percentage is None:
            if output_json:
                msg = "--traffic is required when using --json."
                json_print({"success": False, "error": msg})
                sys.exit(1)
            traffic_input = questionary.text(
                "Traffic percentage for variant (0-100):", default="50"
            ).ask()
            if traffic_input is None:
                warning("Aborted.")
                sys.exit(0)
            try:
                traffic_percentage = int(traffic_input)
            except ValueError:
                error("Traffic percentage must be an integer.")
                sys.exit(1)

        if not 0 <= traffic_percentage <= 100:
            msg = "Traffic percentage must be an integer between 0 and 100."
            if output_json:
                json_print({"success": False, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        result = project.create_ab_test(name.strip(), variant_deployment_id, traffic_percentage)
        if output_json:
            json_print({"success": True, "ab_test": result})
        else:
            success("A/B test started.")
            dep_map = cls._fetch_deployment_map(project)
            print_ab_test_detail(result, deployments=dep_map)

    @classmethod
    def ab_test_list(
        cls,
        base_path: str,
        limit: int = 10,
        output_json: bool = False,
    ) -> None:
        """List A/B tests for the project."""
        from poly.output.console import paged_output, print_ab_tests

        project = load_project(base_path, output_json=output_json)
        ab_tests = project.list_ab_tests(limit=limit)
        if output_json:
            json_print({"success": True, "ab_tests": ab_tests})
        else:
            dep_map = cls._fetch_deployment_map(project) if ab_tests else {}
            with paged_output():
                print_ab_tests(ab_tests, deployments=dep_map)

    @classmethod
    def ab_test_active(
        cls,
        base_path: str,
        output_json: bool = False,
    ) -> None:
        """Show the currently active A/B test."""
        from poly.output.console import print_ab_test_detail

        project = load_project(base_path, output_json=output_json)
        ab_test = project.get_active_ab_test()
        if output_json:
            json_print({"success": True, "ab_test": ab_test})
        else:
            dep_map = cls._fetch_deployment_map(project) if ab_test else {}
            print_ab_test_detail(ab_test, deployments=dep_map)

    @classmethod
    def ab_test_update(
        cls,
        base_path: str,
        traffic_percentage: int | None,
        output_json: bool = False,
    ) -> None:
        """Update traffic percentage for the active A/B test."""
        import questionary

        from poly.output.console import error, info, print_ab_test_detail, success, warning

        project = load_project(base_path, output_json=output_json)

        ab_test = project.get_active_ab_test()
        if not ab_test:
            msg = "No active A/B test found for this project."
            if output_json:
                json_print({"success": False, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        if traffic_percentage is None:
            if output_json:
                msg = "--traffic is required when using --json."
                json_print({"success": False, "error": msg})
                sys.exit(1)
            current = str(ab_test.get("traffic_percentage", 50))
            traffic_input = questionary.text(
                "Traffic percentage for variant (0-100):", default=current
            ).ask()
            if traffic_input is None:
                warning("Aborted.")
                sys.exit(0)
            try:
                traffic_percentage = int(traffic_input)
            except ValueError:
                error("Traffic percentage must be an integer.")
                sys.exit(1)

        if not 0 <= traffic_percentage <= 100:
            msg = "Traffic percentage must be an integer between 0 and 100."
            if output_json:
                json_print({"success": False, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        ab_test_id = ab_test["id"]
        if traffic_percentage == ab_test.get("traffic_percentage"):
            if output_json:
                json_print({"success": True, "ab_test": ab_test, "unchanged": True})
            else:
                info(f"Traffic is already at {traffic_percentage}%. No update needed.")
            return

        result = project.update_ab_test(ab_test_id, traffic_percentage)
        if output_json:
            json_print({"success": True, "ab_test": result})
        else:
            success(f"Traffic updated to {traffic_percentage}%.")
            dep_map = cls._fetch_deployment_map(project)
            print_ab_test_detail(result, deployments=dep_map)

    @classmethod
    def ab_test_end(
        cls,
        base_path: str,
        chosen_version: str | None = None,
        output_json: bool = False,
    ) -> None:
        """End the active A/B test and choose the winning deployment."""
        import questionary

        from poly.output.console import error, info, success, warning

        project = load_project(base_path, output_json=output_json)

        ab_test = project.get_active_ab_test()
        if not ab_test:
            msg = "No active A/B test found for this project."
            if output_json:
                json_print({"success": False, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        ab_test_id = ab_test["id"]
        ab_test_name = ab_test.get("name") or ab_test_id
        control_id = ab_test.get("control_deployment_id", "unknown")
        variant_id = ab_test.get("variant_deployment_id", "unknown")

        dep_map = cls._fetch_deployment_map(project)

        def _label(did: str) -> str:
            dep = dep_map.get(did)
            if not dep:
                return did
            h = (dep.get("version_hash") or "")[:9]
            m = (dep.get("deployment_metadata") or {}).get("deployment_message", "") or ""
            return f"{h}  {m}".strip() if h else did

        control_label = _label(control_id)
        variant_label = _label(variant_id)

        if not output_json:
            info(f"Active A/B test: [bold]{ab_test_name}[/bold]")

        if not chosen_version:
            if output_json:
                json_print(
                    {
                        "success": False,
                        "error": "--chosen-version is required when using --json.",
                    }
                )
                sys.exit(1)

            choices = [
                questionary.Choice(title=f"Control — {control_label}", value=control_id),
                questionary.Choice(title=f"Variant — {variant_label}", value=variant_id),
            ]
            chosen_deployment_id = questionary.select(
                "Choose the winning deployment (this version will receive all live traffic):",
                choices=choices,
            ).ask()
            if not chosen_deployment_id:
                warning("Aborted.")
                sys.exit(0)
        else:
            all_deps = list(dep_map.values())
            chosen_deployment_id = cls._resolve_version_to_deployment_id(chosen_version, all_deps)
            if not chosen_deployment_id:
                msg = f"No deployment found matching version '{chosen_version}'."
                if output_json:
                    json_print({"success": False, "error": msg})
                else:
                    error(msg)
                sys.exit(1)

        winner_label = _label(chosen_deployment_id)
        promote_variant = chosen_deployment_id == variant_id

        result = project.end_ab_test(ab_test_id, chosen_deployment_id)

        if not output_json:
            success(f"A/B test '{ab_test_name}' ended. Winner: {winner_label}")

        promoted = False
        if promote_variant:
            if not output_json:
                info("Promoting variant to live...")
            try:
                variant_dep = dep_map.get(variant_id, {})
                variant_msg = (variant_dep.get("deployment_metadata") or {}).get(
                    "deployment_message", ""
                ) or ""
                project.promote_deployment(variant_id, "live", message=variant_msg)
                promoted = True
                if not output_json:
                    success("Variant promoted to live.")
            except Exception as e:
                if output_json:
                    json_print(
                        {
                            "success": True,
                            "ab_test": result,
                            "promoted": False,
                            "promote_error": str(e),
                        }
                    )
                else:
                    warning(f"A/B test ended but failed to promote variant to live: {e}")
                return

        if output_json:
            json_print(
                {
                    "success": True,
                    "ab_test": result,
                    "promoted": promoted,
                }
            )
