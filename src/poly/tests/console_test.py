"""Tests for poly/output/console.py display helpers.

Copyright PolyAI Limited
"""

import os
import unittest
from unittest.mock import MagicMock, PropertyMock, patch

from rich.console import Console, ConsoleDimensions

from poly.library import TTSVoice
from poly.output.console import (
    _less_command,
    _merge_leaf_diffs,
    _OverflowPager,
    console,
    flatten_branch_tree,
    mask_api_key,
    mask_secret,
    paged_output,
    print_aggregate,
    print_archived_branches,
    print_asr_models,
    print_available_metrics,
    print_branch_history,
    print_conversation_search,
    print_experiment_detail,
    print_experiments,
    print_llm_models,
    print_merge_conflict_interactive_header,
    print_releases_branches,
    print_transcript,
    print_transcript_matches,
    print_tts_voice,
    print_tts_voices,
    resolve_parent_branch_label,
)


class MaskSecretTest(unittest.TestCase):
    """Tests for mask_secret and mask_api_key's markup-free/coloured split."""

    def test_mask_secret_has_no_markup(self):
        """mask_secret is plain text, safe for JSON output or an exception message."""
        self.assertEqual(mask_secret("sk-abcdefgh1234"), "sk-a****1234")

    def test_short_secret_is_fully_masked(self):
        """A secret too short to safely reveal 4+4 characters of is masked entirely."""
        self.assertEqual(mask_secret("short"), "****")

    def test_mask_api_key_wraps_mask_secret_in_colour_markup(self):
        """mask_api_key adds console colour markup around the same masked value."""
        self.assertEqual(mask_api_key("sk-abcdefgh1234"), "[yellow]sk-a****1234[/yellow]")


def _branch(
    branch_id: str, parent_branch_id: str | None = None, tag: str | None = None
) -> dict[str, str | None]:
    """Build the branch metadata shape returned by the platform for one branch."""
    return {"branchId": branch_id, "parentBranchId": parent_branch_id, "tag": tag}


class FlattenBranchTreeTest(unittest.TestCase):
    """Tests for flatten_branch_tree, which renders a branch forest for flat pickers."""

    def test_single_root_branch_has_no_prefix(self):
        """A lone root branch is rendered as its plain name with no connector."""
        branches = {"main": _branch("id-main")}

        self.assertEqual(flatten_branch_tree(branches, current_branch=None), [("main", "main")])

    def test_multi_level_tree_uses_connectors_and_indentation(self):
        """Children are prefixed with connectors and indented once per level of depth."""
        branches = {
            "main": _branch("id-main"),
            "feature-a": _branch("id-a", "id-main"),
            "feature-b": _branch("id-b", "id-main"),
            "sub-a": _branch("id-sub-a", "id-a"),
            "sub-b": _branch("id-sub-b", "id-a"),
        }

        self.assertEqual(
            flatten_branch_tree(branches, current_branch=None),
            [
                ("main", "main"),
                ("├─ feature-a", "feature-a"),
                ("│  ├─ sub-a", "sub-a"),
                ("│  └─ sub-b", "sub-b"),
                ("└─ feature-b", "feature-b"),
            ],
        )

    def test_last_sibling_subtree_indents_with_blank_continuation(self):
        """Descendants of a last sibling indent with spaces, not a vertical guide."""
        branches = {
            "main": _branch("id-main"),
            "feature-a": _branch("id-a", "id-main"),
            "feature-b": _branch("id-b", "id-main"),
            "grandchild": _branch("id-grandchild", "id-b"),
        }

        self.assertEqual(
            flatten_branch_tree(branches, current_branch=None),
            [
                ("main", "main"),
                ("├─ feature-a", "feature-a"),
                ("└─ feature-b", "feature-b"),
                ("   └─ grandchild", "grandchild"),
            ],
        )

    def test_siblings_are_sorted_alphabetically_at_every_level(self):
        """Roots and children are both emitted in alphabetical order, not insertion order."""
        branches = {
            "zebra": _branch("id-zebra"),
            "apple": _branch("id-apple"),
            "z-child": _branch("id-z-child", "id-apple"),
            "a-child": _branch("id-a-child", "id-apple"),
        }

        titles = [title for title, _ in flatten_branch_tree(branches, current_branch=None)]

        self.assertEqual(titles, ["apple", "├─ a-child", "└─ z-child", "zebra"])

    def test_current_branch_title_is_suffixed_but_value_is_not(self):
        """The current branch shows '(current)' in its title while its value stays plain."""
        branches = {
            "main": _branch("id-main"),
            "feature-a": _branch("id-a", "id-main"),
        }

        result = flatten_branch_tree(branches, current_branch="feature-a")

        self.assertEqual(result, [("main", "main"), ("└─ feature-a (current)", "feature-a")])

    def test_current_root_branch_title_is_suffixed(self):
        """A root branch that is current is also suffixed, with no connector added."""
        branches = {"main": _branch("id-main")}

        self.assertEqual(
            flatten_branch_tree(branches, current_branch="main"), [("main (current)", "main")]
        )

    def test_branch_with_unknown_parent_is_treated_as_root(self):
        """A branch whose parent is missing from the dict is rendered as a root branch."""
        branches = {
            "main": _branch("id-main"),
            "orphan": _branch("id-orphan", "id-deleted-parent"),
        }

        self.assertEqual(
            flatten_branch_tree(branches, current_branch=None),
            [("main", "main"), ("orphan", "orphan")],
        )

    def test_no_branches_returns_empty_list(self):
        """An empty branches dict produces no rows."""
        self.assertEqual(flatten_branch_tree({}, current_branch=None), [])

    def test_values_are_always_raw_branch_names(self):
        """Every value is the raw branch name, so callers can use it without stripping."""
        branches = {
            "main": _branch("id-main"),
            "feature-a": _branch("id-a", "id-main"),
            "sub-a": _branch("id-sub-a", "id-a"),
        }

        values = [value for _, value in flatten_branch_tree(branches, current_branch="sub-a")]

        self.assertEqual(sorted(values), ["feature-a", "main", "sub-a"])


class PrintReleasesBranchesTest(unittest.TestCase):
    """Tests for print_releases_branches, the tree renderer used by `branch list`."""

    def _render(self, branches: dict, current_branch: str | None = None) -> str:
        with console.capture() as capture:
            print_releases_branches(branches, current_branch)
        return capture.get()

    def test_tagged_branch_shows_tag_alongside_name(self):
        """A branch with a tag renders '(tag)' after its name."""
        branches = {
            "main": _branch("id-main"),
            "Release 1": _branch("id-release-1", "id-main", tag="staging"),
        }

        output = self._render(branches)

        self.assertIn("Release 1 (staging)", output)

    def test_untagged_branch_shows_no_tag_suffix(self):
        """A branch with no tag renders its name with no trailing parenthetical."""
        branches = {
            "main": _branch("id-main"),
            "Release 1": _branch("id-release-1", "id-main"),
        }

        output = self._render(branches)

        self.assertIn("Release 1\n", output)
        self.assertNotIn("(", output)

    def test_current_and_tagged_branch_shows_both_markers(self):
        """A branch that is both current and tagged shows the tag and '(current)'."""
        branches = {
            "main": _branch("id-main"),
            "Release 1": _branch("id-release-1", "id-main", tag="staging"),
        }

        output = self._render(branches, current_branch="Release 1")

        self.assertIn("Release 1 (staging) (current)", output)


class PrintArchivedBranchesTest(unittest.TestCase):
    """Tests for print_archived_branches, the table used by `branch list --archived`."""

    def _render(self, branches: list[dict]) -> str:
        with console.capture() as capture:
            print_archived_branches(branches)
        return capture.get()

    def test_renders_a_row_per_archived_branch(self):
        """Each archived branch contributes its name and id to the table."""
        output = self._render(
            [
                {"name": "old-a", "branchId": "b-a", "archivedAt": "", "daysLeft": 30},
                {"name": "old-b", "branchId": "b-b", "archivedAt": "", "daysLeft": 2},
            ]
        )

        for expected in ("old-a", "b-a", "old-b", "b-b"):
            self.assertIn(expected, output)

    def test_shows_remaining_days_before_permanent_deletion(self):
        """daysLeft is rendered so users know how long they have to restore."""
        output = self._render([{"name": "old", "branchId": "b-1", "daysLeft": 7}])

        self.assertIn("7 days left", output)

    def test_missing_expiry_renders_a_placeholder(self):
        """A branch with no daysLeft shows a dash rather than 'None'."""
        output = self._render([{"name": "old", "branchId": "b-1"}])

        self.assertNotIn("None", output)
        self.assertIn("—", output)

    def test_zero_days_left_is_rendered_not_treated_as_missing(self):
        """daysLeft of 0 is a real value — the last day — and must still show."""
        output = self._render([{"name": "old", "branchId": "b-1", "daysLeft": 0}])

        self.assertIn("0 days left", output)

    def test_missing_fields_render_placeholders(self):
        """A row missing name and id degrades to dashes instead of raising."""
        output = self._render([{}])

        self.assertIn("—", output)

    def test_empty_list_renders_headers_only(self):
        """With nothing archived the table still renders its headers."""
        output = self._render([])

        self.assertIn("Branch", output)
        self.assertIn("Expires", output)


class PrintBranchHistoryTest(unittest.TestCase):
    """Tests for print_branch_history, the table used by `branch history`."""

    def _render(self, commits: list[dict]) -> str:
        with console.capture() as capture:
            print_branch_history(commits)
        return capture.get()

    def test_renders_a_row_per_merge(self):
        """Each merge contributes its source branch and author to the table."""
        output = self._render(
            [
                {"mergedAt": "", "branchName": "feature-a", "mergedBy": "ada@example.com"},
                {"mergedAt": "", "branchName": "feature-b", "mergedBy": "grace@example.com"},
            ]
        )

        for expected in ("feature-a", "ada@example.com", "feature-b", "grace@example.com"):
            self.assertIn(expected, output)

    def test_empty_history_reports_no_commits(self):
        """An empty history is explained rather than rendered as a blank table."""
        output = self._render([])

        self.assertIn("No commits found for this branch.", output)

    def test_missing_fields_render_placeholders(self):
        """A merge record missing its branch or author degrades to dashes."""
        output = self._render([{"mergedAt": ""}])

        self.assertIn("—", output)
        self.assertNotIn("None", output)


class ResolveParentBranchLabelTest(unittest.TestCase):
    """Tests for resolve_parent_branch_label, which names an archived branch's parent."""

    def test_main_parent_is_named_directly(self):
        """A top-level branch reports main without needing a lookup."""
        label = resolve_parent_branch_label({"parentBranchId": "main"})

        self.assertEqual(label, "main")

    def test_parent_id_is_resolved_to_a_name(self):
        """A sub-branch's parent id is resolved through the lookup."""
        label = resolve_parent_branch_label(
            {"parentBranchId": "BRANCH-P"}, {"BRANCH-P": "Release 1"}
        )

        self.assertEqual(label, "Release 1")

    def test_unknown_parent_id_falls_back_to_the_id(self):
        """An unresolvable parent shows its id rather than going blank."""
        label = resolve_parent_branch_label({"parentBranchId": "BRANCH-GONE"}, {})

        self.assertEqual(label, "BRANCH-GONE")

    def test_missing_parent_renders_a_placeholder(self):
        """An entry with no parent at all renders a dash."""
        for branch in ({}, {"parentBranchId": None}, {"parentBranchId": ""}):
            with self.subTest(branch=branch):
                self.assertEqual(resolve_parent_branch_label(branch), "—")


class PrintArchivedBranchesParentColumnTest(unittest.TestCase):
    """Tests for the parent column in print_archived_branches."""

    def _render(self, branches: list[dict], name_by_branch_id: dict | None = None) -> str:
        with console.capture() as capture:
            print_archived_branches(branches, name_by_branch_id)
        return capture.get()

    def test_parent_column_is_shown(self):
        """The table gains a Parent header so lineage is visible."""
        output = self._render([{"name": "old", "branchId": "b-1", "parentBranchId": "main"}])

        self.assertIn("Parent", output)
        self.assertIn("main", output)

    def test_sub_branch_shows_its_parent_name(self):
        """A branch archived under another branch names that parent, not its id."""
        output = self._render(
            [{"name": "child", "branchId": "b-2", "parentBranchId": "b-1"}],
            {"b-1": "Release 1"},
        )

        self.assertIn("Release 1", output)

    def test_renders_without_a_lookup(self):
        """Omitting the lookup still renders, falling back to raw parent ids."""
        output = self._render([{"name": "child", "branchId": "b-2", "parentBranchId": "b-1"}])

        self.assertIn("b-1", output)


class ArchivedParentMarkerTest(unittest.TestCase):
    """Tests for marking a parent that is itself archived."""

    def _render(self, branches: list[dict], name_by_branch_id: dict | None = None) -> str:
        with console.capture() as capture:
            print_archived_branches(branches, name_by_branch_id)
        return capture.get()

    def test_archived_parent_is_marked(self):
        """A parent that is also in the archive is flagged, since restoring a child
        does not bring the parent back."""
        label = resolve_parent_branch_label(
            {"parentBranchId": "b-1"}, {"b-1": "Release 1"}, {"b-1"}
        )

        self.assertEqual(label, "Release 1 (archived)")

    def test_live_parent_is_not_marked(self):
        """A parent that is still active is left unmarked."""
        label = resolve_parent_branch_label({"parentBranchId": "b-1"}, {"b-1": "Release 1"}, set())

        self.assertEqual(label, "Release 1")

    def test_main_is_never_marked_archived(self):
        """Main cannot be archived, so it is never flagged even if ids are passed."""
        label = resolve_parent_branch_label({"parentBranchId": "main"}, {}, {"main"})

        self.assertEqual(label, "main")

    def test_unresolved_archived_parent_marks_the_raw_id(self):
        """An archived parent with no known name still gets the marker."""
        label = resolve_parent_branch_label({"parentBranchId": "b-9"}, {}, {"b-9"})

        self.assertEqual(label, "b-9 (archived)")

    def test_table_marks_parents_present_in_the_same_listing(self):
        """The table derives the archived set from its own rows, so a parent listed
        alongside its child is marked without the caller passing anything extra."""
        output = self._render(
            [
                {"name": "Release 1", "branchId": "b-1", "parentBranchId": "main"},
                {"name": "child", "branchId": "b-2", "parentBranchId": "b-1"},
            ],
            {"b-1": "Release 1", "b-2": "child"},
        )

        self.assertIn("(archived)", output)

    def test_table_does_not_mark_a_live_parent(self):
        """A parent absent from the listing is still live, so it is not marked."""
        output = self._render(
            [{"name": "child", "branchId": "b-2", "parentBranchId": "b-live"}],
            {"b-live": "Active Release"},
        )

        self.assertIn("Active Release", output)
        self.assertNotIn("(archived)", output)


class OverflowPagerTest(unittest.TestCase):
    """Tests for _OverflowPager, which pages only when output overflows."""

    SCREEN_HEIGHT = 25

    def setUp(self):
        size_patcher = patch.object(
            Console,
            "size",
            new_callable=PropertyMock,
            return_value=ConsoleDimensions(80, self.SCREEN_HEIGHT),
        )
        size_patcher.start()
        self.addCleanup(size_patcher.stop)

    def _show(self, content: str, less_command: str | None = None, **pager_kwargs):
        """Run the pager over content, returning (written_directly, system_pager, pipe_pager).

        less_command is what the reader's pager resolves to; None means it isn't less.
        """
        written = []
        with (
            patch.object(
                Console,
                "file",
                new_callable=PropertyMock,
                return_value=MagicMock(write=written.append),
            ),
            patch("poly.output.console.SystemPager") as mock_system_pager,
            patch("poly.output.console._less_command", return_value=less_command),
            patch("poly.output.console.pydoc.pipe_pager") as mock_pipe_pager,
        ):
            _OverflowPager(**pager_kwargs).show(content)
        return "".join(written), mock_system_pager, mock_pipe_pager

    def test_content_shorter_than_screen_is_written_directly(self):
        """Output that fits on one screen bypasses the pager entirely."""
        content = "row\n" * (self.SCREEN_HEIGHT - 1)

        written, mock_system_pager, mock_pipe_pager = self._show(content, "less -i")

        self.assertEqual(written, content)
        mock_system_pager.assert_not_called()
        mock_pipe_pager.assert_not_called()

    def test_content_longer_than_screen_is_handed_to_the_pager(self):
        """Output that overflows the screen goes to a pager other than less, not stdout."""
        content = "row\n" * (self.SCREEN_HEIGHT + 10)

        written, mock_system_pager, mock_pipe_pager = self._show(content)

        self.assertEqual(written, "")
        mock_system_pager.return_value.show.assert_called_once_with(content)
        mock_pipe_pager.assert_not_called()

    def test_less_is_run_with_its_search_options_and_a_hint(self):
        """With less, the content goes to the resolved command, with the title and a hint."""
        content = "row\n" * (self.SCREEN_HEIGHT + 10)

        written, mock_system_pager, mock_pipe_pager = self._show(
            content, "less -i --header=1", title="TTS voices", header_lines=1
        )

        self.assertEqual(written, "")
        mock_system_pager.assert_not_called()
        mock_pipe_pager.assert_called_once_with(
            content, "less -i --header=1", "TTS voices · / to search, & to filter ·"
        )

    def test_less_without_a_title_shows_only_the_hint(self):
        """A caller that gives no title still gets the search hint in the prompt."""
        content = "row\n" * (self.SCREEN_HEIGHT + 10)

        _, _, mock_pipe_pager = self._show(content, "less -i")

        self.assertEqual(mock_pipe_pager.call_args.args[2], "/ to search, & to filter ·")

    def test_content_exactly_filling_the_screen_is_not_paged(self):
        """The boundary case stays inline rather than opening the pager."""
        content = "row\n" * (self.SCREEN_HEIGHT - 1)

        _, mock_system_pager, mock_pipe_pager = self._show(content, "less -i")

        mock_system_pager.assert_not_called()
        mock_pipe_pager.assert_not_called()


class LessCommandTest(unittest.TestCase):
    """Tests for _less_command, which adds search options when the pager is less."""

    def _command(self, header_lines=1, env=None, version=668, which="/usr/bin/less"):
        environ = {key: value for key, value in os.environ.items()}
        for key in ("PAGER", "MANPAGER", "TERM"):
            environ.pop(key, None)
        environ.update(env or {})
        with (
            patch.dict(os.environ, environ, clear=True),
            patch("poly.output.console.sys.platform", "darwin"),
            patch("poly.output.console.shutil.which", return_value=which),
            patch("poly.output.console._less_version", return_value=version),
        ):
            return _less_command(header_lines)

    def test_default_less_gets_case_insensitive_search_and_a_pinned_header(self):
        """With no PAGER set, the less on the PATH runs with -i and --header."""
        self.assertEqual(self._command(), "/usr/bin/less -i --header=1")

    def test_pager_set_to_less_keeps_its_own_options(self):
        """A PAGER of less with options keeps them, with the search options added."""
        self.assertEqual(self._command(env={"PAGER": "less -R"}), "less -R -i --header=1")

    def test_manpager_wins_over_pager(self):
        """MANPAGER is read first, matching pydoc."""
        self.assertIsNone(self._command(env={"MANPAGER": "bat", "PAGER": "less"}))

    def test_other_pagers_are_left_to_pydoc(self):
        """A pager that isn't less gets no options added."""
        self.assertIsNone(self._command(env={"PAGER": "bat"}))
        self.assertIsNone(self._command(env={"PAGER": "more"}))

    def test_no_header_without_header_lines(self):
        """Output with no header row only gets case-insensitive search."""
        self.assertEqual(self._command(header_lines=0), "/usr/bin/less -i")

    def test_less_older_than_600_gets_no_header_option(self):
        """--header needs less 600, so older versions run without it."""
        self.assertEqual(self._command(version=581), "/usr/bin/less -i")

    def test_no_less_on_the_path(self):
        """Without less installed, the pager is left to pydoc."""
        self.assertIsNone(self._command(which=None))

    def test_dumb_terminal_is_left_to_pydoc(self):
        """pydoc strips styles on dumb and emacs terminals, so it keeps those."""
        self.assertIsNone(self._command(env={"TERM": "dumb"}))

    def test_command_that_is_not_really_less(self):
        """A pager named less that doesn't report a less version gets no options."""
        self.assertIsNone(self._command(version=None))


class PagedOutputTest(unittest.TestCase):
    """Tests for the paged_output context manager's TTY and enabled guards."""

    def test_no_paging_when_stdout_is_not_a_terminal(self):
        """Piped and redirected output is never paged, matching git."""
        with (
            patch.object(Console, "is_terminal", new_callable=PropertyMock, return_value=False),
            patch.object(console, "pager") as mock_pager,
        ):
            with paged_output():
                pass

        mock_pager.assert_not_called()

    def test_no_paging_when_explicitly_disabled(self):
        """Passing enabled=False opts a caller out even on a terminal."""
        with (
            patch.object(Console, "is_terminal", new_callable=PropertyMock, return_value=True),
            patch.object(console, "pager") as mock_pager,
        ):
            with paged_output(enabled=False):
                pass

        mock_pager.assert_not_called()

    def test_paging_uses_the_overflow_pager_with_styles(self):
        """On a terminal the custom pager is used, with styles kept for colour."""
        with (
            patch.object(Console, "is_terminal", new_callable=PropertyMock, return_value=True),
            patch.object(console, "pager") as mock_pager,
        ):
            with paged_output():
                pass

        mock_pager.assert_called_once()
        self.assertIsInstance(mock_pager.call_args.kwargs["pager"], _OverflowPager)
        self.assertTrue(mock_pager.call_args.kwargs["styles"])

    def test_title_and_header_lines_reach_the_pager(self):
        """The prompt title and pinned header rows are passed through to the pager."""
        with (
            patch.object(Console, "is_terminal", new_callable=PropertyMock, return_value=True),
            patch.object(console, "pager") as mock_pager,
        ):
            with paged_output(title="TTS voices", header_lines=1):
                pass

        pager = mock_pager.call_args.kwargs["pager"]
        self.assertEqual((pager.title, pager.header_lines), ("TTS voices", 1))


def _topic(content: str, timestamp: str) -> dict:
    """A knowledge base topic as the platform returns it in a merge conflict."""
    return {
        "id": "TOPICS-396d40fd",
        "name": "Topic 3",
        "content": content,
        "actions": "",
        "exampleQueries": [{"query": "Topic 3"}],
        "references": {"sms": {}, "handoff": {}, "variables": {}},
        "isActive": True,
        "tags": [],
        "createdAt": timestamp,
        "createdBy": "user@example.com",
        "updatedAt": timestamp,
        "updatedBy": "user@example.com",
    }


class MergeLeafDiffsTest(unittest.TestCase):
    """Tests for _merge_leaf_diffs, which reduces a whole-resource conflict to its fields."""

    def test_reports_only_the_field_that_differs(self):
        """A resource copied then edited on one side reports that field alone."""
        diffs = _merge_leaf_diffs(
            _topic("A second topic", "2026-09-09T09:29:23.574Z"),
            _topic("A third topic", "2026-09-09T09:30:02.188Z"),
        )

        self.assertEqual(diffs, [("content", "A second topic", "A third topic")])

    def test_audit_fields_alone_report_nothing(self):
        """Two independently created copies differ only in audit fields, which are excluded."""
        diffs = _merge_leaf_diffs(
            _topic("New content", "2026-09-07T13:37:30.232Z"),
            _topic("New content", "2026-09-07T13:55:55.175Z"),
        )

        self.assertEqual(diffs, [])

    def test_nested_fields_are_reported_by_dotted_path(self):
        """A difference inside a nested object names the full path to the leaf."""
        main = {"references": {"sms": {"enabled": False}}}
        branch = {"references": {"sms": {"enabled": True}}}

        self.assertEqual(_merge_leaf_diffs(main, branch), [("references.sms.enabled", False, True)])

    def test_key_present_on_one_side_only(self):
        """A field only one side carries is reported against a missing counterpart."""
        self.assertEqual(
            _merge_leaf_diffs({"content": "a"}, {"content": "a", "actions": "run"}),
            [("actions", None, "run")],
        )

    def test_list_values_are_compared_whole(self):
        """Lists are not walked element by element; the differing list is reported as one leaf."""
        diffs = _merge_leaf_diffs(
            {"exampleQueries": [{"query": "one"}]},
            {"exampleQueries": [{"query": "two"}]},
        )

        self.assertEqual(diffs, [("exampleQueries", [{"query": "one"}], [{"query": "two"}])])


class PrintMergeConflictInteractiveHeaderTest(unittest.TestCase):
    """Tests for print_merge_conflict_interactive_header, the panel above each conflict prompt."""

    def _render(self, parent_value, branch_value) -> str:
        with console.capture() as capture:
            print_merge_conflict_interactive_header(
                field_path="topics/greeting/content",
                resource_key="topics/greeting",
                conflict_index=1,
                conflict_total=1,
                auto_mergeable=False,
                heavy=False,
                base_value="Hello",
                branch_label="feature-a-child",
                branch_value=branch_value,
                parent_label="Release 1",
                parent_value=parent_value,
            )
        return capture.get()

    def test_labels_the_parent_value_with_the_parent_branch(self):
        """The parent's value is labelled with the parent branch's name, not as main."""
        output = self._render("Hello from the parent", "Hello from the branch")

        self.assertIn("Parent (Release 1)", output)
        self.assertNotIn("Main", output)

    def test_labels_each_differing_field_with_the_parent_branch(self):
        """A whole-resource conflict labels each differing field's parent value the same way."""
        output = self._render({"content": "From the parent"}, {"content": "From the branch"})

        self.assertIn("Parent (Release 1)", output)
        self.assertNotIn("Main", output)


_EXPERIMENT = {
    "id": "exp-001",
    "name": "v2 test",
    "traffic_percentage": 30,
    "versions": [
        {"branch_id": "br-main", "kind": "control", "traffic_percentage": 70},
        {"branch_id": "br-v2", "kind": "release", "traffic_percentage": 30},
    ],
    "created_by": "miles",
}
_EXPERIMENT_BRANCHES = {"br-main": {"name": "main"}, "br-v2": {"name": "v2-branch"}}


class PrintExperimentsTest(unittest.TestCase):
    """Tests for print_experiments, the table used by `deployments experiment list`."""

    def _render(self, experiments: list, branches: dict | None = None) -> str:
        with console.capture() as capture:
            print_experiments(experiments, branches=branches)
        return capture.get()

    def test_empty_list_prints_no_experiments_message(self):
        """No experiments renders an informational message instead of a table."""
        self.assertIn("No experiments found", self._render([]))

    def test_row_shows_variant_branch_name_and_active_status(self):
        """Each row names the variant branch and marks an unended experiment active."""
        output = self._render([_EXPERIMENT], branches=_EXPERIMENT_BRANCHES)

        self.assertIn("exp-001", output)
        self.assertIn("v2-branch", output)
        self.assertIn("active", output)

    def test_ended_experiment_without_branch_map_shows_raw_id(self):
        """Without a branch map the variant branch ID is shown, and status is ended."""
        output = self._render([dict(_EXPERIMENT, ended_at="2026-01-01T00:00:00Z")])

        self.assertIn("br-v2", output)
        self.assertIn("ended", output)


class PrintExperimentDetailTest(unittest.TestCase):
    """Tests for print_experiment_detail, the panel used by `deployments experiment active`."""

    def _render(self, experiment: dict | None, branches: dict | None = None) -> str:
        with console.capture() as capture:
            print_experiment_detail(experiment, branches=branches)
        return capture.get()

    def test_none_prints_no_active_experiment_message(self):
        """A missing experiment renders an informational message instead of a panel."""
        self.assertIn("No active experiment", self._render(None))

    def test_traffic_split_is_shown_for_control_and_variant(self):
        """The control gets the remainder of the variant's traffic percentage."""
        output = self._render(_EXPERIMENT, branches=_EXPERIMENT_BRANCHES)

        self.assertIn("(70% traffic)  main", output)
        self.assertIn("(30% traffic)  v2-branch", output)

    def test_ended_experiment_shows_winner(self):
        """An ended experiment with a chosen version shows the winning branch."""
        ended = dict(
            _EXPERIMENT,
            ended_at="2026-01-01T00:00:00Z",
            chosen_version={"branch_id": "br-v2"},
        )

        output = self._render(ended, branches=_EXPERIMENT_BRANCHES)

        self.assertIn("Ended", output)
        self.assertIn("Winner", output)

    def test_missing_version_traffic_shows_placeholder(self):
        """A version missing its own traffic_percentage falls back to a dash."""
        experiment = dict(_EXPERIMENT)
        experiment["versions"] = [
            {"branch_id": "br-main", "kind": "control"},
            {"branch_id": "br-v2", "kind": "release"},
        ]
        output = self._render(experiment)

        self.assertIn("(— traffic)", output)


class PrintAvailableMetricsTest(unittest.TestCase):
    """Tests for print_available_metrics, the `metrics available` table."""

    def _render(self, metrics: list[dict]) -> str:
        with console.capture() as capture:
            print_available_metrics(metrics)
        return capture.get()

    def test_metrics_are_sorted_with_values_and_description(self):
        """Rows are alphabetical; string metrics list their expected values."""
        output = self._render(
            [
                {"name": "poly_score", "type": "float", "description": "Overall score"},
                {"name": "OUTCOME", "type": "string", "values": ["booked", "cancelled"]},
            ]
        )

        self.assertLess(output.index("OUTCOME"), output.index("poly_score"))
        self.assertIn("booked, cancelled", output)
        self.assertIn("Overall score", output)
        self.assertIn("2 metrics", output)

    def test_empty_catalog(self):
        """No metrics prints a one-line notice rather than an empty table."""
        self.assertIn("No metrics available", self._render([]))


class PrintAggregateTest(unittest.TestCase):
    """Tests for print_aggregate, the `metrics query` / `metrics score` table."""

    def _render(self, result: dict, headline: str | None = None, **query) -> str:
        with patch.object(console, "_width", 200), console.capture() as capture:
            print_aggregate(result, headline=headline, **query)
        return capture.get()

    def _bucket_label(self, bucket: str, **query) -> str:
        output = self._render({"columns": ["bucket"], "rows": [[bucket]]}, **query)
        return output.splitlines()[-1].strip()

    def test_numbers_and_buckets_are_formatted(self):
        """Floats get two decimals, counts get separators, buckets a date."""
        output = self._render(
            {
                "columns": ["bucket", "channel", "avg", "conversation_count"],
                "rows": [["2026-09-01T00:00:00+00:00", "VOICE-SIP", 4.2134, 1318]],
                "limit": 20,
                "offset": 0,
            },
            headline="Poly Score: 4.21 average",
        )

        self.assertIn("Poly Score: 4.21 average", output)
        self.assertIn("VOICE-SIP", output)
        self.assertIn("4.21", output)
        self.assertIn("1,318", output)
        self.assertNotIn("2026-09-01T00:00:00+00:00", output)
        self.assertIn("2026-09-01 ", output)
        self.assertNotIn("Use --offset", output)

    def test_bucket_labels_do_not_depend_on_the_machine_timezone(self):
        """UTC buckets are labelled in UTC: the date alone, or with the hour when hourly."""
        bucket = "2026-10-01T00:00:00+00:00"

        self.assertEqual(self._bucket_label(bucket, interval="daily"), "2026-10-01")
        self.assertEqual(self._bucket_label(bucket, interval="weekly"), "2026-10-01")
        self.assertEqual(self._bucket_label(bucket, interval="monthly"), "2026-10-01")
        self.assertEqual(self._bucket_label(bucket, interval="hourly"), "2026-10-01 00:00 UTC")

    def test_bucket_labels_stay_in_the_query_timezone(self):
        """Hourly and daily buckets are labelled in the timezone they were bucketed in."""
        zone = "America/New_York"
        bucket = "2026-11-01T04:00:00+00:00"

        self.assertEqual(self._bucket_label(bucket, interval="daily", timezone=zone), "2026-11-01")
        self.assertEqual(
            self._bucket_label(bucket, interval="hourly", timezone=zone), "2026-11-01 00:00 EDT"
        )

    def test_hourly_labels_tell_apart_the_repeated_hour(self):
        """When the clocks go back, 01:00 happens twice; the zone name says which is which."""
        labels = [
            self._bucket_label(bucket, interval="hourly", timezone="America/New_York")
            for bucket in ("2026-11-01T05:00:00+00:00", "2026-11-01T06:00:00+00:00")
        ]

        self.assertEqual(labels, ["2026-11-01 01:00 EDT", "2026-11-01 01:00 EST"])

    def test_weekly_and_monthly_labels_ignore_the_timezone(self):
        """The Data API buckets weeks and months in UTC whatever timezone is sent."""
        label = self._bucket_label(
            "2026-11-02T00:00:00+00:00", interval="weekly", timezone="America/New_York"
        )

        self.assertEqual(label, "2026-11-02")

    def test_full_page_hints_at_the_next_offset(self):
        """When the page is full, the footer says where the next page starts."""
        output = self._render({"columns": ["avg"], "rows": [[1.0], [2.0]], "limit": 2, "offset": 2})

        self.assertIn("Use --offset 4", output)

    def test_no_rows(self):
        """An empty window prints a notice and no table."""
        self.assertIn("No data in this window", self._render({"columns": ["avg"], "rows": []}))


class PrintConversationSearchTest(unittest.TestCase):
    """Tests for print_conversation_search, the `conversations search` table."""

    def test_metric_columns_and_pii_warning(self):
        """Requested fields become columns; missing PII fields produce a warning."""
        result = {
            "conversations": [
                {
                    "conversation_id": "conv-1",
                    "started_at": "2026-09-30T10:00:00+00:00",
                    "duration_seconds": 95,
                    "metrics": {"poly_score_v2": 4.5, "channel": "CHAT"},
                }
            ],
            "total": 30,
            "limit": 1,
            "offset": 0,
        }

        with (
            patch("poly.output.console.warning") as mock_warning,
            # Wide enough that no column truncates, whatever the platform calls UTC.
            patch.object(console, "_width", 200),
            console.capture() as capture,
        ):
            print_conversation_search(
                result, fields=["poly_score_v2", "duration", "channel", "call_summary"]
            )
        output = capture.get()

        self.assertIn("conv-1", output)
        self.assertIn("poly_score", output)
        self.assertIn("4.50", output)
        self.assertIn("CHAT", output)
        self.assertEqual(output.lower().count("duration"), 1)
        self.assertIn("--offset 1", output)
        self.assertIn("call_summary", mock_warning.call_args[0][0])


class PrintTranscriptTest(unittest.TestCase):
    """Tests for print_transcript_matches and print_transcript."""

    def test_matches_show_context_in_order_with_the_phrase(self):
        """Matched turns print between their context turns."""
        result = {
            "results": [
                {
                    "conversation_id": "conv-1",
                    "project_id": "proj1",
                    "matched_turns": [
                        {
                            "turn_index": 2,
                            "user_input": "I want to cancel my booking please",
                            "user_input_datetime": "2026-09-30T10:00:05+00:00",
                            "agent_response": "Sure, which booking?",
                            "context": {
                                "before": [
                                    {"turn_index": 1, "user_input": "hello", "agent_response": "hi"}
                                ],
                                "after": [{"turn_index": 3, "user_input": "the one on friday"}],
                            },
                        }
                    ],
                }
            ],
            "total": 1,
            "limit": 20,
            "offset": 0,
        }

        with console.capture() as capture:
            print_transcript_matches(result, "cancel my booking")
        output = capture.get()

        self.assertIn("conv-1", output)
        self.assertIn("1 match", output)
        self.assertLess(output.index("hello"), output.index("cancel my booking"))
        self.assertLess(output.index("cancel my booking"), output.index("the one on friday"))

    def test_transcript_prefers_english_when_asked(self):
        """--english swaps in the translated text where it exists and falls back otherwise."""
        transcript = {
            "conversation_id": "conv-1",
            "total_turns": 1,
            "turns": [
                {
                    "turn_index": 0,
                    "user_input": "hola",
                    "english_user_input": "hello",
                    "user_input_datetime": "2026-09-30T10:00:00+00:00",
                    "agent_response": "buenos días",
                }
            ],
        }

        with console.capture() as capture:
            print_transcript(transcript)
        original = capture.get()
        with console.capture() as capture:
            print_transcript(transcript, english=True)
        english = capture.get()

        self.assertIn("hola", original)
        self.assertIn("hello", english)
        self.assertIn("buenos días", english)
        self.assertIn("1 turns", english)


def _is_poly(model: dict) -> bool:
    return model["name"].startswith("PolyAI")


class PrintLlmModelsTest(unittest.TestCase):
    """Tests for print_llm_models, the table used by `poly library llm`."""

    def _render(self, models: list) -> str:
        with console.capture() as capture:
            print_llm_models(models, is_poly=_is_poly)
        return capture.get()

    def test_empty_list_prints_no_models_message(self):
        """No models renders a message instead of a table."""
        self.assertIn("No language models available", self._render([]))

    def test_row_shows_name_both_ids_and_count(self):
        """Each row shows the name, model ID and provider model ID, with a count below."""
        output = self._render(
            [{"id": "MODEL-1", "name": "GPT-4.1 mini", "providerModelId": "gpt-41-mini"}]
        )

        self.assertIn("GPT-4.1 mini", output)
        self.assertIn("MODEL-1", output)
        self.assertIn("gpt-41-mini", output)
        self.assertIn("1 language models", output)

    def test_polyai_model_is_tagged(self):
        """Only rows the is_poly check accepts carry the PolyAI tag."""
        output = self._render(
            [
                {"id": "MODEL-1", "name": "PolyAI Raven 3.5", "providerModelId": "polywhirl-3-5"},
                {"id": "MODEL-2", "name": "GPT-4.1 mini", "providerModelId": "gpt-41-mini"},
            ]
        )
        poly_row = next(line for line in output.splitlines() if "polywhirl-3-5" in line)
        other_row = next(line for line in output.splitlines() if "gpt-41-mini" in line)

        self.assertIn("PolyAI  MODEL-1", poly_row)
        self.assertNotIn("PolyAI", other_row)

    def test_flags_render_as_ticks_and_crosses(self):
        """Capability flags show a tick when set and a cross when false or missing."""
        output = self._render(
            [{"name": "M", "providerModelId": "m-1", "endToEnd": True, "supportsWebchat": False}]
        )
        row = next(line for line in output.splitlines() if "m-1" in line)

        self.assertEqual(row.count("✓"), 1)
        self.assertEqual(row.count("✗"), 1)

    def test_temperature_support_is_not_shown(self):
        """Temperature can't be set in Agent Studio, so the table has no column for it."""
        output = self._render(
            [{"name": "M", "providerModelId": "m-1", "supportsTemperature": True}]
        )

        self.assertNotIn("Temperature", output)


class PrintAsrModelsTest(unittest.TestCase):
    """Tests for print_asr_models, the table used by `poly library asr`."""

    def _render(self, models: list) -> str:
        with console.capture() as capture:
            print_asr_models(models, is_poly=_is_poly)
        return capture.get()

    def test_empty_list_prints_no_models_message(self):
        """No models renders a message instead of a table."""
        self.assertIn("No ASR models available", self._render([]))

    def test_row_shows_name_provider_and_model(self):
        """Each row shows the name, provider and model, with a count below the table."""
        output = self._render(
            [{"name": "Deepgram Nova 3", "provider": "deepgram", "model": "nova-3"}]
        )

        self.assertIn("Deepgram Nova 3", output)
        self.assertIn("deepgram", output)
        self.assertIn("nova-3", output)
        self.assertIn("1 ASR models", output)

    def test_missing_fields_show_a_dash(self):
        """A row missing its provider and model shows dashes rather than failing."""
        output = self._render([{"name": "Partial"}])

        row = next(line for line in output.splitlines() if "Partial" in line)
        self.assertEqual(row.count("—"), 2)

    def test_polyai_model_is_tagged(self):
        """Only rows the is_poly check accepts carry the PolyAI tag."""
        output = self._render(
            [
                {"name": "PolyAI Latency", "provider": "default", "model": "poly-latency"},
                {"name": "Deepgram Nova 3", "provider": "deepgram", "model": "nova-3"},
            ]
        )
        poly_row = next(line for line in output.splitlines() if "poly-latency" in line)
        other_row = next(line for line in output.splitlines() if "nova-3" in line)

        self.assertIn("PolyAI  default", poly_row)
        self.assertNotIn("PolyAI", other_row)


def _voice(**overrides) -> TTSVoice:
    """A TTS voice as the library holds it, with any field overridden."""
    fields = {
        "voice_id": "VOICE-1a2b3c4d",
        "name": "Anne",
        "provider": "ELEVEN_LABS",
        "provider_voice_id": "DAgjOaO8Ats7",
        "config": {"stability": 0.3, "model_id": "eleven_multilingual_v2"},
        "metadata": {
            "accent": "en-US",
            "language": "English (United States)",
            "gender": "female",
            "tags": ["Sophisticated", "Clear"],
            "description": "English, Sophisticated, Clear",
            "suggested_use": "informative_educational",
            "live_projects": 3,
            "sample_voice": ["https://example.com/anne.mp3"],
        },
        "poly_ai_voice": False,
        "owner": "global",
    }
    fields.update(overrides)
    return TTSVoice(**fields)


class PrintTtsVoiceTest(unittest.TestCase):
    """Tests for print_tts_voice, the panel `poly library voice show` prints."""

    def _render(self, voice: TTSVoice) -> str:
        with console.capture() as capture:
            print_tts_voice(voice)
        return capture.get()

    def test_identifying_fields_are_shown(self):
        """The panel shows the voice's ID, provider name and vendor voice ID."""
        output = self._render(_voice())

        self.assertIn("Anne", output)
        self.assertIn("VOICE-1a2b3c4d", output)
        self.assertIn("ElevenLabs", output)
        self.assertIn("DAgjOaO8Ats7", output)

    def test_language_shows_the_code_and_its_name(self):
        """The accent is followed by the language's name when the voice has one."""
        self.assertIn("en-US (English (United States))", self._render(_voice()))

    def test_descriptive_fields_are_readable(self):
        """Gender is capitalised, tags are joined and the suggested use loses its underscores."""
        output = self._render(_voice())

        self.assertIn("Female", output)
        self.assertIn("Sophisticated, Clear", output)
        self.assertIn("Informative educational", output)
        self.assertIn("Live projects", output)

    def test_description_is_left_out(self):
        """The description only repeats the language and tags, so it isn't shown."""
        self.assertNotIn("Description", self._render(_voice()))

    def test_sample_url_is_shown(self):
        """The first recording's URL is shown so it can be opened."""
        self.assertIn("https://example.com/anne.mp3", self._render(_voice()))

    def test_voice_without_a_recording_says_so(self):
        """A voice with no sample_voice says it has no recording."""
        voice = _voice(metadata={"accent": "en-US", "gender": "male"})

        self.assertIn("No recording", self._render(voice))

    def test_default_settings_are_listed_in_order(self):
        """The library's settings are listed under their own heading, sorted by name."""
        output = self._render(_voice())

        self.assertIn("Default settings", output)
        self.assertLess(output.index("model_id"), output.index("stability"))
        self.assertIn("eleven_multilingual_v2", output)

    def test_voice_without_settings_has_no_settings_section(self):
        """A voice with an empty config doesn't show the settings heading."""
        self.assertNotIn("Default settings", self._render(_voice(config={})))

    def test_polyai_voice_is_tagged_in_the_title(self):
        """A PolyAI voice carries the PolyAI tag next to its name."""
        self.assertIn("Anne PolyAI", self._render(_voice(poly_ai_voice=True)))
        self.assertNotIn("PolyAI", self._render(_voice()))

    def test_archived_voice_shows_when_who_and_why(self):
        """An archived voice shows who archived it and why; others have no Archived row."""
        archived = _voice(
            metadata={
                "accent": "en-GB",
                "archived": True,
                "archived_at": "2026-07-27T12:15:00+00:00",
                "archived_by": "someone@example.com",
                "archive_reason": "Internal test voice",
            }
        )

        # The time zone's name varies by machine and moves where the row wraps, so compare words.
        words = " ".join(self._render(archived).replace("│", " ").split())

        self.assertIn("Archived", words)
        self.assertIn("by someone@example.com: Internal test voice", words)
        self.assertNotIn("Archived", self._render(_voice()))

    def test_missing_fields_show_a_dash(self):
        """A voice missing its gender and vendor ID shows a dash for each."""
        voice = _voice(provider_voice_id=None, metadata={"accent": "en-US"})

        output = self._render(voice)

        self.assertIn("Vendor voice ID  —", output)
        self.assertIn("Gender           —", output)


class PrintTtsVoicesTest(unittest.TestCase):
    """Tests for print_tts_voices, the table `poly library voice list` prints."""

    def _render(self, voices: list[TTSVoice]) -> str:
        with console.capture() as capture:
            print_tts_voices(voices)
        return capture.get()

    def test_no_voices_says_so(self):
        """An empty list prints a message instead of an empty table."""
        self.assertIn("No voices available.", self._render([]))

    def test_rows_follow_the_given_order(self):
        """The table keeps the caller's order, which is Agent Studio's ranking."""
        output = self._render([_voice(name="Zed"), _voice(name="Amy")])

        self.assertLess(output.index("Zed"), output.index("Amy"))

    def test_hidden_tags_are_left_out(self):
        """Tags Agent Studio hides, such as PolyVoice, don't appear in the table."""
        voice = _voice(metadata={"accent": "en-US", "tags": ["Calm", "PolyVoice"]})

        output = self._render([voice])

        self.assertIn("Calm", output)
        self.assertNotIn("PolyVoice", output)

    def test_polyai_voices_are_tagged(self):
        """A PolyAI voice's row carries the PolyAI tag."""
        self.assertIn("PolyAI", self._render([_voice(poly_ai_voice=True)]))

    def test_vendor_id_is_shown_only_where_voices_clash(self):
        """Voices sharing a name, provider and language show their vendor voice IDs."""
        voices = [
            _voice(provider_voice_id="first-vendor-id"),
            _voice(voice_id="VOICE-2", provider_voice_id="second-vendor-id"),
            _voice(name="Ben", provider_voice_id="ben-vendor-id"),
        ]

        output = self._render(voices)

        self.assertIn("first-vendor-id", output)
        self.assertIn("second-vendor-id", output)
        self.assertNotIn("ben-vendor-id", output)


class VoiceOwnerOutputTest(unittest.TestCase):
    """Tests for how a voice's owner shows in `voice list` and `voice show`."""

    def _list(self, voices: list[TTSVoice]) -> str:
        with console.capture() as capture:
            print_tts_voices(voices)
        return capture.get()

    def _show(self, voice: TTSVoice) -> str:
        with console.capture() as capture:
            print_tts_voice(voice)
        return capture.get()

    def test_imported_voices_are_labelled_in_the_list(self):
        """An account's own voice is labelled Imported; a global one isn't."""
        output = self._list([_voice(name="Cloned", owner="account"), _voice(owner="global")])

        self.assertIn("Imported", output)
        self.assertEqual(output.count("Imported"), 1)

    def test_polyai_label_wins_over_imported(self):
        """A PolyAI voice keeps its PolyAI label."""
        output = self._list([_voice(poly_ai_voice=True, owner="global")])

        self.assertIn("PolyAI", output)
        self.assertNotIn("Imported", output)

    def test_show_says_who_owns_the_voice(self):
        """The panel has an Owner row when the platform said whose voice it is."""
        self.assertIn("This account", self._show(_voice(owner="account")))
        self.assertIn("Global library", self._show(_voice(owner="global")))
