"""Unit tests for migration utilities.

Copyright PolyAI Limited
"""

import os
import tempfile
import unittest

from poly.migration_utils import migrate_legacy_topic_files
from poly.resources import resource_utils


class TestMigrateLegacyTopicFiles(unittest.TestCase):
    """Tests for migrate_legacy_topic_files."""

    def _write_topic(self, topics_dir: str, filename: str, content: dict) -> str:
        """Helper to write a topic YAML file."""
        path = os.path.join(topics_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(resource_utils.dump_yaml(content))
        return path

    def test_no_topics_dir(self):
        """Should be a no-op when topics/ doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp:
            migrate_legacy_topic_files(tmp)
            self.assertFalse(os.path.isdir(os.path.join(tmp, "topics")))

    def test_renames_legacy_file(self):
        """Legacy 'Topic Name.yaml' should become 'topic_name.yaml' with name key."""
        with tempfile.TemporaryDirectory() as tmp:
            topics_dir = os.path.join(tmp, "topics")
            os.makedirs(topics_dir)
            self._write_topic(topics_dir, "Topic Name.yaml", {"enabled": True, "content": "hello"})

            migrate_legacy_topic_files(tmp)

            self.assertFalse(os.path.exists(os.path.join(topics_dir, "Topic Name.yaml")))
            new_path = os.path.join(topics_dir, "topic_name.yaml")
            self.assertTrue(os.path.exists(new_path))
            with open(new_path, "r", encoding="utf-8") as f:
                data = resource_utils.load_yaml(f.read())
            self.assertEqual(data["name"], "Topic Name")
            self.assertTrue(data["enabled"])
            self.assertEqual(data["content"], "hello")

    def test_skips_already_migrated_files(self):
        """Files that already have a 'name' key should be left untouched."""
        with tempfile.TemporaryDirectory() as tmp:
            topics_dir = os.path.join(tmp, "topics")
            os.makedirs(topics_dir)
            self._write_topic(topics_dir, "my_topic.yaml", {"name": "My Topic", "enabled": True})

            migrate_legacy_topic_files(tmp)

            with open(os.path.join(topics_dir, "my_topic.yaml"), "r", encoding="utf-8") as f:
                data = resource_utils.load_yaml(f.read())
            self.assertEqual(data["name"], "My Topic")

    def test_clean_filename_not_deleted(self):
        """Legacy file whose name is already clean should be updated in place, not deleted."""
        with tempfile.TemporaryDirectory() as tmp:
            topics_dir = os.path.join(tmp, "topics")
            os.makedirs(topics_dir)
            self._write_topic(topics_dir, "my_topic.yaml", {"enabled": True})

            migrate_legacy_topic_files(tmp)

            new_path = os.path.join(topics_dir, "my_topic.yaml")
            self.assertTrue(os.path.exists(new_path))
            with open(new_path, "r", encoding="utf-8") as f:
                data = resource_utils.load_yaml(f.read())
            self.assertEqual(data["name"], "my_topic")
            self.assertTrue(data["enabled"])

    def test_mixed_legacy_and_migrated(self):
        """Migration should handle a mix of legacy and already-migrated files."""
        with tempfile.TemporaryDirectory() as tmp:
            topics_dir = os.path.join(tmp, "topics")
            os.makedirs(topics_dir)
            self._write_topic(topics_dir, "existing.yaml", {"name": "Existing", "enabled": True})
            self._write_topic(topics_dir, "New Topic.yaml", {"enabled": False})

            migrate_legacy_topic_files(tmp)

            files = sorted(os.listdir(topics_dir))
            self.assertEqual(files, ["existing.yaml", "new_topic.yaml"])

            with open(os.path.join(topics_dir, "existing.yaml"), "r", encoding="utf-8") as f:
                data = resource_utils.load_yaml(f.read())
            self.assertEqual(data["name"], "Existing")

            with open(os.path.join(topics_dir, "new_topic.yaml"), "r", encoding="utf-8") as f:
                data = resource_utils.load_yaml(f.read())
            self.assertEqual(data["name"], "New Topic")
