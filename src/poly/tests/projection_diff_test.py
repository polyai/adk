"""Tests for the projection_diff module (poly diff --proto).

Copyright PolyAI Limited
"""

import copy
import unittest
from unittest.mock import MagicMock

from poly.handlers.protobuf.commands_pb2 import Command
from poly.projection_diff import (
    apply_command,
    apply_commands,
    deep_merge,
    diff_projections,
    generate_projection_diff,
    snake_to_camel_keys,
)


class SnakeToCamelKeysTests(unittest.TestCase):
    """Tests for snake_to_camel_keys recursive key conversion."""

    def test_flat_dict_converts_keys(self):
        """A flat dict with snake_case keys should have them converted to camelCase."""
        result = snake_to_camel_keys({"hello_world": 1, "foo_bar": 2})
        self.assertEqual(result, {"helloWorld": 1, "fooBar": 2})

    def test_nested_dict_converts_keys_at_all_levels(self):
        """Keys in nested dicts should all be converted to camelCase."""
        result = snake_to_camel_keys({"outer_key": {"inner_key": "value"}})
        self.assertEqual(result, {"outerKey": {"innerKey": "value"}})

    def test_list_of_dicts_converts_each_dict(self):
        """Each dict in a list should have its keys converted."""
        result = snake_to_camel_keys([{"is_active": True}, {"flow_id": "f1"}])
        self.assertEqual(result, [{"isActive": True}, {"flowId": "f1"}])

    def test_non_dict_values_pass_through_unchanged(self):
        """Scalar values should be returned as-is."""
        self.assertEqual(snake_to_camel_keys("hello"), "hello")
        self.assertEqual(snake_to_camel_keys(42), 42)
        self.assertIsNone(snake_to_camel_keys(None))
        self.assertTrue(snake_to_camel_keys(True))

    def test_empty_dict_returns_empty_dict(self):
        """An empty dict should return an empty dict."""
        self.assertEqual(snake_to_camel_keys({}), {})

    def test_single_word_key_stays_lowercase(self):
        """A single-word key with no underscores should remain lowercase."""
        result = snake_to_camel_keys({"name": 1})
        self.assertEqual(result, {"name": 1})

    def test_mixed_nested_structure(self):
        """A dict containing lists of dicts should convert all keys recursively."""
        data = {
            "top_level": [
                {"nested_key": {"deep_key": "val"}},
            ]
        }
        result = snake_to_camel_keys(data)
        self.assertEqual(
            result,
            {"topLevel": [{"nestedKey": {"deepKey": "val"}}]},
        )


class DeepMergeTests(unittest.TestCase):
    """Tests for deep_merge in-place dict merging."""

    def test_shallow_merge_adds_new_keys_and_overwrites_existing(self):
        """New keys should be added and existing scalar keys overwritten."""
        base = {"a": 1, "b": 2}
        deep_merge(base, {"b": 99, "c": 3})
        self.assertEqual(base, {"a": 1, "b": 99, "c": 3})

    def test_nested_merge_only_overwrites_changed_keys(self):
        """In nested dicts, only the keys present in override should change."""
        base = {"config": {"name": "old", "timeout": 30}}
        deep_merge(base, {"config": {"name": "new"}})
        self.assertEqual(base, {"config": {"name": "new", "timeout": 30}})

    def test_override_dict_with_non_dict_replaces_entirely(self):
        """Overriding a dict value with a scalar replaces it."""
        base = {"config": {"name": "old"}}
        deep_merge(base, {"config": "flat_value"})
        self.assertEqual(base, {"config": "flat_value"})

    def test_override_non_dict_with_dict_replaces_entirely(self):
        """Overriding a scalar value with a dict replaces it."""
        base = {"config": "flat_value"}
        deep_merge(base, {"config": {"name": "new"}})
        self.assertEqual(base, {"config": {"name": "new"}})

    def test_deeply_nested_merge(self):
        """Merging should work through multiple levels of nesting."""
        base = {"a": {"b": {"c": 1, "d": 2}}}
        deep_merge(base, {"a": {"b": {"d": 99}}})
        self.assertEqual(base, {"a": {"b": {"c": 1, "d": 99}}})


class ApplyCommandTests(unittest.TestCase):
    """Tests for apply_command applying a single command to a projection."""

    def test_create_topic_adds_entry(self):
        """A create_topic command should add an entry with camelCase keys."""
        projection = {"knowledgeBase": {"topics": {"entities": {}}}}
        command_dict = {
            "type": "create_topic",
            "create_topic": {"id": "t1", "name": "greet", "content": "hi", "is_active": True},
        }

        apply_command(projection, command_dict)

        self.assertEqual(
            projection["knowledgeBase"]["topics"]["entities"]["t1"],
            {"id": "t1", "name": "greet", "content": "hi", "isActive": True},
        )

    def test_update_topic_merges_into_existing(self):
        """An update_topic command should merge into the existing topic, preserving unchanged fields."""
        projection = {
            "knowledgeBase": {
                "topics": {
                    "entities": {
                        "t1": {"id": "t1", "name": "greet", "content": "hi", "isActive": True}
                    }
                }
            }
        }
        command_dict = {
            "type": "update_topic",
            "update_topic": {"id": "t1", "content": "hello there"},
        }

        apply_command(projection, command_dict)

        self.assertEqual(
            projection["knowledgeBase"]["topics"]["entities"]["t1"],
            {"id": "t1", "name": "greet", "content": "hello there", "isActive": True},
        )

    def test_delete_topic_removes_entry(self):
        """A delete_topic command should remove the entry from the projection."""
        projection = {
            "knowledgeBase": {
                "topics": {"entities": {"t1": {"id": "t1", "name": "greet", "content": "hi"}}}
            }
        }
        command_dict = {
            "type": "delete_topic",
            "delete_topic": {"id": "t1"},
        }

        apply_command(projection, command_dict)

        self.assertNotIn("t1", projection["knowledgeBase"]["topics"]["entities"])

    def test_create_entity_adds_at_correct_path(self):
        """An entity_create command should add at entities.entities.entities with camelCase keys."""
        projection = {"entities": {"entities": {"entities": {}}}}
        command_dict = {
            "type": "entity_create",
            "entity_create": {"id": "e1", "name": "color", "entity_type": "list"},
        }

        apply_command(projection, command_dict)

        self.assertEqual(
            projection["entities"]["entities"]["entities"]["e1"],
            {"id": "e1", "name": "color", "entityType": "list"},
        )

    def test_update_singleton_personality_merges(self):
        """An update_personality command should merge into agentSettings.personality."""
        projection = {"agentSettings": {"personality": {"tone": "friendly", "verbosity": "low"}}}
        command_dict = {
            "type": "update_personality",
            "update_personality": {"tone": "formal"},
        }

        apply_command(projection, command_dict)

        self.assertEqual(
            projection["agentSettings"]["personality"],
            {"tone": "formal", "verbosity": "low"},
        )

    def test_channel_routed_voice_greeting(self):
        """A channel_update_greeting with voice channel_type should update channels.voice.config.greeting."""
        projection = {"channels": {"voice": {"config": {"greeting": {"text": "old"}}}}}
        command_dict = {
            "type": "channel_update_greeting",
            "channel_update_greeting": {"channel_type": 1, "text": "Welcome!"},
        }

        apply_command(projection, command_dict)

        self.assertEqual(
            projection["channels"]["voice"]["config"]["greeting"],
            {"text": "Welcome!", "channelType": 1},
        )

    def test_channel_routed_chat_greeting(self):
        """A channel_update_greeting with channel_type=2 should route to channels.webChat.config.greeting."""
        projection = {"channels": {"webChat": {"config": {"greeting": {"text": "old"}}}}}
        command_dict = {
            "type": "channel_update_greeting",
            "channel_update_greeting": {"channel_type": 2, "text": "Hi there"},
        }

        apply_command(projection, command_dict)

        self.assertEqual(
            projection["channels"]["webChat"]["config"]["greeting"],
            {"text": "Hi there", "channelType": 2},
        )

    def test_unknown_command_type_is_skipped(self):
        """An unrecognized command type should be skipped without raising an error."""
        projection = {"some": "data"}
        command_dict = {"type": "nonexistent_command", "nonexistent_command": {"id": "x"}}

        apply_command(projection, command_dict)

        self.assertEqual(projection, {"some": "data"})

    def test_create_in_empty_projection_full_structure(self):
        """Creating a topic in an empty projection should produce the full nested structure."""
        projection = {}
        command_dict = {
            "type": "create_topic",
            "create_topic": {"id": "t1", "name": "greet", "is_active": True},
        }

        apply_command(projection, command_dict)

        self.assertEqual(
            projection,
            {
                "knowledgeBase": {
                    "topics": {
                        "entities": {
                            "t1": {"id": "t1", "name": "greet", "isActive": True},
                        }
                    }
                }
            },
        )

    def test_delete_nonexistent_entry_does_not_raise(self):
        """Deleting an entry that does not exist should not raise."""
        projection = {"knowledgeBase": {"topics": {"entities": {}}}}
        command_dict = {
            "type": "delete_topic",
            "delete_topic": {"id": "missing"},
        }

        apply_command(projection, command_dict)

        self.assertEqual(projection["knowledgeBase"]["topics"]["entities"], {})


class ApplyCommandsTests(unittest.TestCase):
    """Tests for apply_commands applying multiple commands to a projection copy."""

    def test_empty_commands_returns_unchanged_deep_copy(self):
        """An empty command list should return a deep copy identical to the original."""
        projection = {"knowledgeBase": {"topics": {"entities": {"t1": {"name": "greet"}}}}}

        result = apply_commands(projection, [])

        self.assertEqual(result, projection)

    def test_multiple_commands_applied_in_sequence(self):
        """Multiple commands should be applied in order, with later commands seeing earlier changes."""
        projection = {"knowledgeBase": {"topics": {"entities": {}}}}
        commands = [
            {
                "type": "create_topic",
                "create_topic": {"id": "t1", "name": "greet", "content": "hello"},
            },
            {
                "type": "update_topic",
                "update_topic": {"id": "t1", "content": "updated hello"},
            },
        ]

        result = apply_commands(projection, commands)

        self.assertEqual(
            result,
            {
                "knowledgeBase": {
                    "topics": {
                        "entities": {
                            "t1": {"id": "t1", "name": "greet", "content": "updated hello"},
                        }
                    }
                }
            },
        )

    def test_original_projection_not_mutated(self):
        """The original projection dict should not be modified."""
        projection = {"knowledgeBase": {"topics": {"entities": {}}}}
        original = copy.deepcopy(projection)
        commands = [
            {
                "type": "create_topic",
                "create_topic": {"id": "t1", "name": "new_topic"},
            },
        ]

        apply_commands(projection, commands)

        self.assertEqual(projection, original)

    def test_create_then_delete_leaves_no_entry(self):
        """Creating then deleting the same entity should result in it not being present."""
        projection = {"knowledgeBase": {"topics": {"entities": {}}}}
        commands = [
            {
                "type": "create_topic",
                "create_topic": {"id": "t1", "name": "temp"},
            },
            {
                "type": "delete_topic",
                "delete_topic": {"id": "t1"},
            },
        ]

        result = apply_commands(projection, commands)

        self.assertNotIn("t1", result["knowledgeBase"]["topics"]["entities"])


class DiffProjectionsTests(unittest.TestCase):
    """Tests for diff_projections recursive diff computation."""

    def test_identical_dicts_returns_empty(self):
        """Two identical dicts should produce an empty diff."""
        d = {"a": 1, "b": {"c": 2}}
        self.assertEqual(diff_projections(d, d), {})

    def test_added_key_shows_before_none(self):
        """A key present only in 'after' should have before=None."""
        before = {}
        after = {"new_key": "new_value"}

        result = diff_projections(before, after)

        self.assertEqual(result, {"new_key": {"before": None, "after": "new_value"}})

    def test_deleted_key_shows_after_none(self):
        """A key present only in 'before' should have after=None."""
        before = {"old_key": "old_value"}
        after = {}

        result = diff_projections(before, after)

        self.assertEqual(result, {"old_key": {"before": "old_value", "after": None}})

    def test_modified_leaf_value(self):
        """A changed leaf value should show both before and after."""
        before = {"name": "old"}
        after = {"name": "new"}

        result = diff_projections(before, after)

        self.assertEqual(result, {"name": {"before": "old", "after": "new"}})

    def test_nested_changes_only_shows_changed_paths(self):
        """Unchanged nested keys should be omitted from the diff."""
        before = {"config": {"name": "same", "timeout": 30}}
        after = {"config": {"name": "same", "timeout": 60}}

        result = diff_projections(before, after)

        self.assertEqual(result, {"config": {"timeout": {"before": 30, "after": 60}}})
        self.assertNotIn("name", result.get("config", {}))

    def test_deeply_nested_change_in_otherwise_identical_tree(self):
        """A single change deep in a large tree should only show that path."""
        before = {"a": {"b": {"c": {"d": 1, "e": 2}}}}
        after = {"a": {"b": {"c": {"d": 1, "e": 99}}}}

        result = diff_projections(before, after)

        self.assertEqual(result, {"a": {"b": {"c": {"e": {"before": 2, "after": 99}}}}})

    def test_both_dicts_with_different_keys(self):
        """When both sides are dicts but have different keys, report all differences."""
        before = {"only_before": "x", "shared": "same"}
        after = {"only_after": "y", "shared": "same"}

        result = diff_projections(before, after)

        self.assertEqual(
            result,
            {
                "only_after": {"before": None, "after": "y"},
                "only_before": {"before": "x", "after": None},
            },
        )

    def test_non_dict_leaf_change(self):
        """Diffing two non-dict, non-equal values should return before/after directly."""
        result = diff_projections("old", "new")
        self.assertEqual(result, {"before": "old", "after": "new"})

    def test_equal_non_dict_values_return_empty(self):
        """Two equal scalar values should produce an empty diff."""
        self.assertEqual(diff_projections(42, 42), {})

    def test_list_value_change(self):
        """Changed list values should be reported as a leaf before/after."""
        before = {"tags": ["a", "b"]}
        after = {"tags": ["a", "b", "c"]}

        result = diff_projections(before, after)

        self.assertEqual(result, {"tags": {"before": ["a", "b"], "after": ["a", "b", "c"]}})


class GenerateProjectionDiffTests(unittest.TestCase):
    """Tests for the generate_projection_diff orchestrator."""

    def test_update_topic_diff_nested_in_command(self):
        """Each command should include a diff key showing only the changed fields."""
        projection = {
            "knowledgeBase": {
                "topics": {"entities": {"t1": {"id": "t1", "name": "greeting", "content": "Hello"}}}
            }
        }

        cmd = Command()
        cmd.type = "update_topic"
        cmd.command_id = "cmd-001"
        cmd.update_topic.id = "t1"
        cmd.update_topic.name = "greeting"
        cmd.update_topic.content = "Hello updated"

        project = MagicMock()
        project.fetch_projection.return_value = projection
        project.generate_push_commands.return_value = [cmd]

        result = generate_projection_diff(project)

        self.assertEqual(len(result["commands"]), 1)
        command = result["commands"][0]
        self.assertEqual(command["type"], "update_topic")
        self.assertEqual(command["command_id"], "cmd-001")
        self.assertEqual(
            command["diff"],
            {
                "content": {
                    "before": "Hello",
                    "after": "Hello updated",
                },
            },
        )

    def test_no_changes_returns_empty_commands(self):
        """When there are no commands, output should have an empty commands list."""
        projection = {"knowledgeBase": {"topics": {"entities": {}}}}

        project = MagicMock()
        project.fetch_projection.return_value = projection
        project.generate_push_commands.return_value = []

        result = generate_projection_diff(project)

        self.assertEqual(result, {"commands": []})

    def test_calls_fetch_projection_and_generate_push_commands(self):
        """The orchestrator should call fetch_projection and generate_push_commands on the project."""
        project = MagicMock()
        project.fetch_projection.return_value = {}
        project.generate_push_commands.return_value = []

        generate_projection_diff(project)

        project.fetch_projection.assert_called_once()
        project.generate_push_commands.assert_called_once_with(skip_validation=True)

    def test_original_projection_not_mutated(self):
        """The projection returned by fetch_projection should not be modified."""
        projection = {
            "knowledgeBase": {
                "topics": {"entities": {"t1": {"id": "t1", "name": "greeting", "content": "Hello"}}}
            }
        }
        original = copy.deepcopy(projection)

        cmd = Command()
        cmd.type = "update_topic"
        cmd.command_id = "cmd-001"
        cmd.update_topic.id = "t1"
        cmd.update_topic.content = "Hello updated"

        project = MagicMock()
        project.fetch_projection.return_value = projection
        project.generate_push_commands.return_value = [cmd]

        generate_projection_diff(project)

        self.assertEqual(projection, original)
