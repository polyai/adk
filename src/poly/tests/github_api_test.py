"""Tests for GitHub API gist interactions: review, list_gists, delete_gists, and gist formatting.

Copyright PolyAI Limited
"""

import unittest
from unittest.mock import patch

from poly.cli import AgentStudioCLI, _format_gist_choice
from poly.handlers.github_api_handler import GitHubAPIHandler


class FormatGistChoiceTest(unittest.TestCase):
    """Tests for the _format_gist_choice module-level helper."""

    def test_formats_date_short_id_and_description(self):
        """All three parts are joined with double-space separators."""
        gist = {
            "id": "abc1234567890",
            "description": "my-project: local → remote",
            "created_at": "2026-03-25T10:30:00Z",
            "html_url": "https://gist.github.com/abc1234567890",
        }

        result = _format_gist_choice(gist)

        self.assertEqual(result, "2026-03-25  abc1234  my-project: local → remote")

    def test_id_truncated_to_seven_characters(self):
        """Only the first 7 characters of the gist ID appear."""
        gist = {
            "id": "deadbeef12345",
            "description": "desc",
            "created_at": "2026-01-01T00:00:00Z",
        }

        result = _format_gist_choice(gist)

        self.assertIn("deadbee", result)
        self.assertNotIn("deadbeef", result)

    def test_missing_created_at_omits_date(self):
        """When created_at is absent, the output starts with the ID."""
        gist = {
            "id": "abc1234567890",
            "description": "some description",
        }

        result = _format_gist_choice(gist)

        self.assertEqual(result, "abc1234  some description")

    def test_empty_created_at_omits_date(self):
        """When created_at is an empty string, the output starts with the ID."""
        gist = {
            "id": "abc1234567890",
            "description": "desc",
            "created_at": "",
        }

        result = _format_gist_choice(gist)

        self.assertEqual(result, "abc1234  desc")

    def test_empty_description_omits_it(self):
        """When description is empty, only date and ID appear."""
        gist = {
            "id": "abc1234567890",
            "description": "",
            "created_at": "2026-03-25T10:30:00Z",
        }

        result = _format_gist_choice(gist)

        self.assertEqual(result, "2026-03-25  abc1234")


class ListDiffGistsTest(unittest.TestCase):
    """Tests for GitHubAPIHandler.list_diff_gists filtering logic."""

    @patch.object(GitHubAPIHandler, "list_gists")
    def test_returns_only_diff_file_gists(self, mock_list):
        """Gists whose files are all .diff are included; others are excluded."""
        mock_list.return_value = [
            {
                "id": "aaa1111",
                "description": "review diff",
                "created_at": "2026-03-20T00:00:00Z",
                "html_url": "https://gist.github.com/aaa1111",
                "files": {"config.diff": {}, "flows.diff": {}},
            },
            {
                "id": "bbb2222",
                "description": "not a review",
                "created_at": "2026-03-21T00:00:00Z",
                "html_url": "https://gist.github.com/bbb2222",
                "files": {"notes.txt": {}},
            },
        ]

        result = GitHubAPIHandler.list_diff_gists()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "aaa1111")

    @patch.object(GitHubAPIHandler, "list_gists")
    def test_returns_expected_keys(self, mock_list):
        """Each returned dict contains id, description, created_at, and html_url."""
        mock_list.return_value = [
            {
                "id": "aaa1111",
                "description": "review",
                "created_at": "2026-03-20T00:00:00Z",
                "html_url": "https://gist.github.com/aaa1111",
                "files": {"flow.diff": {}},
            },
        ]

        result = GitHubAPIHandler.list_diff_gists()

        self.assertEqual(set(result[0].keys()), {"id", "description", "created_at", "html_url"})

    @patch.object(GitHubAPIHandler, "list_gists")
    def test_empty_gist_list_returns_empty(self, mock_list):
        """When there are no gists at all, returns an empty list."""
        mock_list.return_value = []

        result = GitHubAPIHandler.list_diff_gists()

        self.assertEqual(result, [])

    @patch.object(GitHubAPIHandler, "list_gists")
    def test_excludes_gists_with_no_files(self, mock_list):
        """Gists with no files key or empty files are excluded."""
        mock_list.return_value = [
            {"id": "ccc3333", "description": "empty", "files": {}},
            {"id": "ddd4444", "description": "none"},
        ]

        result = GitHubAPIHandler.list_diff_gists()

        self.assertEqual(result, [])

    @patch.object(GitHubAPIHandler, "list_gists")
    def test_description_falls_back_to_id_when_missing(self, mock_list):
        """When description is None or empty, the gist ID is used instead."""
        mock_list.return_value = [
            {
                "id": "eee5555",
                "description": None,
                "created_at": "",
                "html_url": "",
                "files": {"a.diff": {}},
            },
        ]

        result = GitHubAPIHandler.list_diff_gists()

        self.assertEqual(result[0]["description"], "eee5555")

    @patch.object(GitHubAPIHandler, "list_gists")
    def test_mixed_diff_and_non_diff_files_excluded(self, mock_list):
        """A gist with both .diff and non-.diff files is excluded."""
        mock_list.return_value = [
            {
                "id": "fff6666",
                "description": "mixed",
                "files": {"a.diff": {}, "readme.md": {}},
            },
        ]

        result = GitHubAPIHandler.list_diff_gists()

        self.assertEqual(result, [])


class DeleteGistsTest(unittest.TestCase):
    """Tests for AgentStudioCLI.delete_gists interactive deletion flow."""

    SAMPLE_GISTS = [
        {
            "id": "aaa1111111",
            "description": "proj: local → remote",
            "created_at": "2026-03-20T00:00:00Z",
            "html_url": "https://gist.github.com/aaa1111111",
        },
        {
            "id": "bbb2222222",
            "description": "proj: main → dev",
            "created_at": "2026-03-21T00:00:00Z",
            "html_url": "https://gist.github.com/bbb2222222",
        },
    ]

    @patch("poly.cli.GitHubAPIHandler.list_diff_gists", return_value=[])
    @patch("poly.cli.plain")
    def test_no_gists_found_prints_message(self, mock_plain, mock_list):
        """When no review gists exist, a 'no gists found' message is displayed."""
        AgentStudioCLI.delete_gists()

        mock_plain.assert_called_once()
        self.assertIn("No review gists found", mock_plain.call_args[0][0])

    @patch("poly.cli.GitHubAPIHandler.list_diff_gists")
    @patch("poly.cli.questionary")
    @patch("poly.cli.warning")
    def test_user_selects_none_shows_warning(self, mock_warning, mock_q, mock_list):
        """When user cancels or selects nothing, a warning is shown and no deletions occur."""
        mock_list.return_value = self.SAMPLE_GISTS
        mock_q.checkbox.return_value.ask.return_value = []

        AgentStudioCLI.delete_gists()

        mock_warning.assert_called_once()
        self.assertIn("No gists selected", mock_warning.call_args[0][0])

    @patch("poly.cli.GitHubAPIHandler.list_diff_gists")
    @patch("poly.cli.GitHubAPIHandler.delete_gist")
    @patch("poly.cli.questionary")
    @patch("poly.cli.success")
    @patch("poly.cli.plain")
    def test_user_selects_and_deletes_gists(
        self, mock_plain, mock_success, mock_q, mock_delete, mock_list
    ):
        """Selected gists are deleted and a success message reports the count."""
        mock_list.return_value = self.SAMPLE_GISTS
        # Simulate user selecting the first gist
        first_choice = _format_gist_choice(self.SAMPLE_GISTS[0])
        mock_q.checkbox.return_value.ask.return_value = [first_choice]

        AgentStudioCLI.delete_gists()

        mock_delete.assert_called_once_with("aaa1111111")
        mock_success.assert_called_once()
        self.assertIn("1 gist(s)", mock_success.call_args[0][0])

    @patch("poly.cli.GitHubAPIHandler.list_diff_gists")
    @patch("poly.cli.GitHubAPIHandler.delete_gist")
    @patch("poly.cli.questionary")
    @patch("poly.cli.success")
    @patch("poly.cli.plain")
    def test_deleting_multiple_gists(
        self, mock_plain, mock_success, mock_q, mock_delete, mock_list
    ):
        """Selecting multiple gists deletes each and reports total count."""
        mock_list.return_value = self.SAMPLE_GISTS
        choices = [_format_gist_choice(g) for g in self.SAMPLE_GISTS]
        mock_q.checkbox.return_value.ask.return_value = choices

        AgentStudioCLI.delete_gists()

        self.assertEqual(mock_delete.call_count, 2)
        self.assertIn("2 gist(s)", mock_success.call_args[0][0])

    @patch("poly.cli.GitHubAPIHandler.list_diff_gists")
    @patch("poly.cli.GitHubAPIHandler.delete_gist")
    @patch("poly.cli.success")
    def test_direct_gist_id_skips_interactive_prompt(self, mock_success, mock_delete, mock_list):
        """Passing a full gist_id deletes it directly without showing a checkbox prompt."""
        mock_list.return_value = self.SAMPLE_GISTS

        AgentStudioCLI.delete_gists(gist_id="aaa1111111")

        mock_delete.assert_called_once_with("aaa1111111")
        mock_success.assert_called_once()

    @patch("poly.cli.GitHubAPIHandler.list_diff_gists")
    @patch("poly.cli.GitHubAPIHandler.delete_gist")
    @patch("poly.cli.success")
    def test_short_gist_id_prefix_matches(self, mock_success, mock_delete, mock_list):
        """Passing the first 7 characters of a gist ID resolves and deletes the full gist."""
        mock_list.return_value = self.SAMPLE_GISTS

        AgentStudioCLI.delete_gists(gist_id="aaa1111")

        mock_delete.assert_called_once_with("aaa1111111")
        mock_success.assert_called_once()

    @patch("poly.cli.GitHubAPIHandler.list_diff_gists")
    @patch("poly.cli.GitHubAPIHandler.delete_gist")
    @patch("poly.cli.error")
    def test_unmatched_gist_id_shows_error(self, mock_error, mock_delete, mock_list):
        """An ID that doesn't match any review gist shows an error and does not delete."""
        mock_list.return_value = self.SAMPLE_GISTS

        AgentStudioCLI.delete_gists(gist_id="zzz9999")

        mock_delete.assert_not_called()
        mock_error.assert_called_once()

    @patch("poly.cli.GitHubAPIHandler.list_diff_gists")
    @patch("poly.cli.GitHubAPIHandler.delete_gist")
    @patch("poly.cli.json_print")
    def test_direct_gist_id_with_json_output(self, mock_json_print, mock_delete, mock_list):
        """With output_json=True and a gist_id, result is printed as JSON."""
        mock_list.return_value = self.SAMPLE_GISTS

        AgentStudioCLI.delete_gists(gist_id="aaa1111111", output_json=True)

        mock_delete.assert_called_once_with("aaa1111111")
        mock_json_print.assert_called_once_with({"success": True})

    @patch("poly.cli.GitHubAPIHandler.list_diff_gists")
    @patch("poly.cli.GitHubAPIHandler.delete_gist")
    @patch("poly.cli.questionary")
    @patch("poly.cli.json_print")
    def test_json_output_prints_success(self, mock_json_print, mock_q, mock_delete, mock_list):
        """With output_json=True, a success JSON object is printed after deletion."""
        mock_list.return_value = self.SAMPLE_GISTS
        first_choice = _format_gist_choice(self.SAMPLE_GISTS[0])
        mock_q.checkbox.return_value.ask.return_value = [first_choice]

        AgentStudioCLI.delete_gists(output_json=True)

        mock_json_print.assert_called_once_with({"success": True})


class ListGistsTest(unittest.TestCase):
    """Tests for AgentStudioCLI.list_gists interactive selection flow."""

    SAMPLE_GISTS = [
        {
            "id": "aaa1111111",
            "description": "proj: local → remote",
            "created_at": "2026-03-20T00:00:00Z",
            "html_url": "https://gist.github.com/aaa1111111",
        },
    ]

    @patch("poly.cli.GitHubAPIHandler.list_diff_gists", return_value=[])
    @patch("poly.cli.plain")
    def test_no_gists_found_prints_message(self, mock_plain, mock_list):
        """When no review gists exist, a 'no gists found' message is displayed."""
        AgentStudioCLI.list_gists()

        mock_plain.assert_called_once()
        self.assertIn("No review gists found", mock_plain.call_args[0][0])

    @patch("poly.cli.GitHubAPIHandler.list_diff_gists")
    @patch("poly.cli.questionary")
    @patch("poly.cli.webbrowser")
    def test_user_selects_gist_opens_browser(self, mock_browser, mock_q, mock_list):
        """Selecting a gist opens its html_url in the browser."""
        mock_list.return_value = self.SAMPLE_GISTS
        choice_label = _format_gist_choice(self.SAMPLE_GISTS[0])
        mock_q.select.return_value.ask.return_value = choice_label

        AgentStudioCLI.list_gists()

        mock_browser.open.assert_called_once_with("https://gist.github.com/aaa1111111")

    @patch("poly.cli.GitHubAPIHandler.list_diff_gists")
    @patch("poly.cli.questionary")
    @patch("poly.cli.webbrowser")
    def test_user_cancels_selection_does_not_open_browser(self, mock_browser, mock_q, mock_list):
        """When user cancels the selection prompt, no browser is opened."""
        mock_list.return_value = self.SAMPLE_GISTS
        mock_q.select.return_value.ask.return_value = None

        AgentStudioCLI.list_gists()

        mock_browser.open.assert_not_called()

    @patch("poly.cli.GitHubAPIHandler.list_diff_gists")
    @patch("poly.cli.json_print")
    def test_json_output_prints_gist_list(self, mock_json_print, mock_list):
        """With output_json=True, gists are printed as JSON without an interactive prompt."""
        mock_list.return_value = self.SAMPLE_GISTS

        AgentStudioCLI.list_gists(output_json=True)

        mock_json_print.assert_called_once_with(self.SAMPLE_GISTS)


class ReviewDescriptionTest(unittest.TestCase):
    """Tests for AgentStudioCLI.review gist description formatting."""

    @patch("poly.cli.GitHubAPIHandler.create_gist", return_value="https://gist.github.com/xyz")
    @patch("poly.cli.AgentStudioCLI._review", return_value={"file.diff": {"content": "+line"}})
    @patch("poly.cli.success")
    def test_local_to_remote_description_includes_project_name(
        self, mock_success, mock_review, mock_create
    ):
        """Local-to-remote review uses 'project_name: local -> remote' description."""
        AgentStudioCLI.review(base_path="/some/my-project")

        description = mock_create.call_args[1]["description"]
        self.assertIn("my-project", description)
        self.assertIn("local → remote", description)

    @patch("poly.cli.GitHubAPIHandler.create_gist", return_value="https://gist.github.com/xyz")
    @patch("poly.cli.AgentStudioCLI._review", return_value={"file.diff": {"content": "+line"}})
    @patch("poly.cli.success")
    def test_branch_comparison_description_includes_branch_names(
        self, mock_success, mock_review, mock_create
    ):
        """Branch-to-branch review uses 'project_name: before -> after' description."""
        AgentStudioCLI.review(
            base_path="/some/my-project",
            before_name="main",
            after_name="dev",
        )

        description = mock_create.call_args[1]["description"]
        self.assertIn("my-project", description)
        self.assertIn("main → dev", description)

    @patch("poly.cli.GitHubAPIHandler.create_gist")
    @patch("poly.cli.AgentStudioCLI._review", return_value={})
    def test_empty_diff_does_not_create_gist(self, mock_review, mock_create):
        """When _review returns an empty dict, no gist is created."""
        AgentStudioCLI.review(base_path="/some/my-project")

        mock_create.assert_not_called()

    @patch("poly.cli.GitHubAPIHandler.create_gist", return_value="https://gist.github.com/xyz")
    @patch("poly.cli.AgentStudioCLI._review", return_value={"file.diff": {"content": "+line"}})
    @patch("poly.cli.success")
    def test_gist_created_as_private(self, mock_success, mock_review, mock_create):
        """Review gists are always created as private (public=False)."""
        AgentStudioCLI.review(base_path="/some/my-project")

        self.assertFalse(mock_create.call_args[1]["public"])

    @patch("poly.cli.GitHubAPIHandler.create_gist", return_value="https://gist.github.com/xyz")
    @patch("poly.cli.AgentStudioCLI._review", return_value={"file.diff": {"content": "+line"}})
    @patch("poly.cli.json_print")
    def test_json_output_prints_success_and_link(self, mock_json_print, mock_review, mock_create):
        """With output_json=True, a successful review prints {success: true, link: url}."""
        AgentStudioCLI.review(base_path="/some/my-project", output_json=True)

        mock_json_print.assert_called_once_with(
            {"success": True, "link": "https://gist.github.com/xyz"}
        )

    @patch("poly.cli.GitHubAPIHandler.create_gist")
    @patch("poly.cli.AgentStudioCLI._review", return_value={})
    @patch("poly.cli.json_print")
    def test_json_output_empty_diff_prints_failure(self, mock_json_print, mock_review, mock_create):
        """With output_json=True, an empty diff prints {success: false, message: ...}."""
        AgentStudioCLI.review(base_path="/some/my-project", output_json=True)

        mock_json_print.assert_called_once()
        result = mock_json_print.call_args[0][0]
        self.assertFalse(result["success"])
        self.assertIn("message", result)


if __name__ == "__main__":
    unittest.main()
