"""Tests for poly/output/console.py display helpers.

Copyright PolyAI Limited
"""

import unittest

from poly.output.console import (
    console,
    flatten_branch_tree,
    print_archived_branches,
    print_branch_history,
    print_releases_branches,
    resolve_parent_branch_label,
)


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
