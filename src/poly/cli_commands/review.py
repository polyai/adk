"""Review command family: create, list, and delete GitHub Gist reviews.

Copyright PolyAI Limited
"""

import os
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Optional

from poly.cli_commands.base import PROJECT_SYNC_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import compute_diff, format_gist_choice
from poly.handlers.github_api_handler import GitHubAPIHandler
from poly.output.json_output import json_print


class ReviewCommand(BaseCommand):
    """Create a GitHub Gist of Agent Studio project changes to share for review."""

    command = "review"

    group = PROJECT_SYNC_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``review`` subcommand tree."""
        review_parser = subparsers.add_parser(
            "review",
            parents=[parents.verbose, parents.json],
            help="Create a GitHub Gist of Agent Studio project changes to share changes.",
            description=(
                "Make a review page against project configuration in Agent Studio.\n\n"
                "If you do not specify --before/--after, it compares your local project "
                "to the remote version (local vs remote).\n"
                "If you provide --before and --after, it compares those versions or "
                "branches directly.\n\n"
                "Examples:\n"
                "  poly review create\n"
                "  poly review create --path /path/to/project\n"
                "  poly review create version-hash-1\n"
                "  poly review create --before main --after feature-branch\n"
                "  poly review create --before sandbox --after live\n"
                "  poly review create --before version-hash-1 --after version-hash-2\n"
                "  poly review list\n"
                "  poly review list --json\n"
                "  poly review delete\n"
                "  poly review delete --id GIST_ID\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        review_parser.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="Base path to the project. Defaults to current working directory.",
        )

        review_subparsers = review_parser.add_subparsers(dest="review_subcommand", required=True)

        review_create_parser = review_subparsers.add_parser(
            "create",
            parents=[parents.verbose, parents.json],
            help="Create a review gist for the current changes.",
        )
        review_create_parser.add_argument(
            "hash",
            nargs="?",
            default=None,
            type=str,
            help="Hash of the version to compare against. If not specified, it will be inferred from the --before and --after arguments.",
        )
        review_create_parser.add_argument(
            "--before",
            type=str,
            help="Name of the original branch or version to compare with.",
        )
        review_create_parser.add_argument(
            "--after",
            type=str,
            help="Name of the branch or version to compare with.",
        )
        review_create_parser.add_argument(
            "--files",
            nargs="*",
            help="List of files to show changes for. If not specified, shows all changes.",
        )
        review_create_parser.set_defaults(review_subcommand="create")

        review_list_parser = review_subparsers.add_parser(
            "list",
            parents=[parents.json],
            help="Interactively select a review gist to open in the browser.",
        )
        review_list_parser.set_defaults(review_subcommand="list")

        review_delete_parser = review_subparsers.add_parser(
            "delete",
            parents=[parents.json],
            help="Interactively select and delete review gists.",
        )
        review_delete_parser.add_argument(
            "--id",
            type=str,
            default=None,
            metavar="GIST_ID",
            help="Gist ID (or first 7 characters) to delete directly, skipping the interactive prompt.",
        )
        review_delete_parser.set_defaults(review_subcommand="delete")

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the matching review sub-handler."""
        if args.review_subcommand == "delete":
            cls.delete_gists(gist_id=args.id, output_json=args.json)
        elif args.review_subcommand == "list":
            cls.list_gists(output_json=args.json)
        elif args.review_subcommand == "create":
            cls.review(
                base_path=args.path,
                files=args.files,
                version_hash=args.hash,
                before=args.before,
                after=args.after,
                output_json=args.json,
            )

    @classmethod
    def review(
        cls,
        base_path: str,
        files: list[str] = None,
        version_hash: str = None,
        before: str = None,
        after: str = None,
        output_json: bool = False,
    ) -> None:
        """Create a GitHub gist for reviewing changes, similar to a pull request."""
        import requests

        from poly.output.console import error, plain, success

        project_name = "/".join(os.path.abspath(base_path).split(os.sep)[-2:])
        if version_hash and (before or after):
            error("Cannot specify both hash and before/after versions.")
            return

        if version_hash:
            after = version_hash
            description = f"Poly ADK: {project_name}: {version_hash}"
        elif not (before or after):
            description = f"Poly ADK: {project_name}: local → remote"
        elif before and after:
            description = f"Poly ADK: {project_name}: {before} → {after}"
        elif after:
            description = f"Poly ADK: {project_name}: {after}"
        else:
            description = f"Poly ADK: {project_name}: {before} → local"

        diffs = compute_diff(
            base_path, files=files, before=before, after=after, output_json=output_json
        )

        if not diffs:
            if output_json and diffs is not None:
                json_print({"success": False, "message": "No changes to review."})
            elif output_json:
                json_print({"success": False, "message": "Failed to compute diffs."})
            else:
                plain("[muted]No changes detected.[/muted]")
            return

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
                success(f"Gist created: {url}")
        except requests.HTTPError as e:
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
    def list_gists(cls, output_json: bool = False) -> None:
        """Interactively select a review gist and open it in the browser."""
        import webbrowser

        import questionary
        import requests

        from poly.output.console import error, plain

        try:
            gists = GitHubAPIHandler.list_diff_gists()
        except requests.HTTPError as e:
            if output_json:
                json_print({"success": False, "message": f"GitHub API error: {e}"})
            else:
                error(f"GitHub API error: {e}")
            return
        except OSError as e:
            if output_json:
                json_print({"success": False, "message": str(e)})
            else:
                error(str(e))
            return

        if output_json:
            json_print(gists)
            return

        if not gists:
            plain("[muted]No review gists found.[/muted]")
            return

        url_by_choice = {format_gist_choice(g): g["html_url"] for g in gists}
        selected = questionary.select("Select a gist to open", choices=list(url_by_choice)).ask()
        if not selected:
            return

        webbrowser.open(url_by_choice[selected])

    @classmethod
    def delete_gists(cls, gist_id: Optional[str] = None, output_json: bool = False) -> None:
        """Interactively select and delete review gists."""
        import questionary
        import requests

        from poly.output.console import error, plain, success, warning

        try:
            gists = GitHubAPIHandler.list_diff_gists()
        except requests.HTTPError as e:
            if output_json:
                json_print({"success": False, "message": f"GitHub API error: {e}"})
            else:
                error(f"GitHub API error: {e}")
            return
        except OSError as e:
            if output_json:
                json_print({"success": False, "message": str(e)})
            else:
                error(str(e))
            return

        if gist_id:
            matched = next(
                (g for g in gists if g["id"].startswith(gist_id)),
                None,
            )
            if not matched:
                if output_json:
                    json_print(
                        {"success": False, "message": f"No review gist found matching '{gist_id}'."}
                    )
                else:
                    error(f"No review gist found matching '{gist_id}'.")
                return
            try:
                GitHubAPIHandler.delete_gist(matched["id"])
            except requests.HTTPError as e:
                if output_json:
                    json_print({"success": False, "message": f"GitHub API error: {e}"})
                else:
                    error(f"GitHub API error: {e}")
                return
            except OSError as e:
                if output_json:
                    json_print({"success": False, "message": str(e)})
                else:
                    error(str(e))
                return
            if output_json:
                json_print({"success": True})
            else:
                success(f"Deleted gist: {matched['id']}")
            return

        if not gists:
            plain("[muted]No review gists found.[/muted]")
            return

        choices = [format_gist_choice(g) for g in gists]
        description_to_id = {format_gist_choice(g): g["id"] for g in gists}

        if output_json:
            json_print(
                {
                    "success": False,
                    "error": "Please provide a gist ID to delete when using JSON output.",
                }
            )
            return

        selected = questionary.checkbox("Select gists to delete", choices=choices).ask()
        if not selected:
            warning("No gists selected. Exiting.")
            return

        try:
            for description in selected:
                gist_id = description_to_id[description]
                GitHubAPIHandler.delete_gist(gist_id)
                if not output_json:
                    plain(f"  [muted]Deleted gist:[/muted] {description}")
            if output_json:
                json_print({"success": True})
            else:
                success(f"Deleted {len(selected)} gist(s).")
        except requests.HTTPError as e:
            if output_json:
                json_print({"success": False, "message": f"GitHub API error: {e}"})
            else:
                error(f"GitHub API error: {e}")
        except OSError as e:
            if output_json:
                json_print({"success": False, "message": str(e)})
            else:
                error(str(e))
