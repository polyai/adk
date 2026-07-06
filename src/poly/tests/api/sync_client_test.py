"""Tests for the SyncClientHandler projection parsers and command queue.

The static ``_read_*_from_projection`` parsers consume the RAW sourcerer
projection format (nested under keys like ``knowledgeBase``, ``specialFunctions``,
``flows.flows.entities`` etc.), which is distinct from the resource-model JSON
stored in ``test_projects/test_project/test_project.json``. Because there is no
raw-projection fixture on disk, these tests build small, focused projection dicts
inline in the same spirit as the ``_projection`` helper in ``project_test.py``.

Copyright PolyAI Limited
"""

import unittest
from unittest.mock import MagicMock, patch

from poly.handlers.protobuf.commands_pb2 import Command
from poly.handlers.sdk import SourcererSDK
from poly.handlers.sync_client import SyncClientHandler
from poly.resources import (
    AsrSettings,
    Condition,
    Entity,
    FlowConfig,
    FlowStep,
    Function,
    FunctionStep,
    FunctionType,
    SettingsPersonality,
    SettingsRole,
    SettingsRules,
    Topic,
    Variable,
    VoiceGreeting,
)


def build_handler():
    """Build a SyncClientHandler with a mocked SDK, bypassing SDK construction.

    The region validity check reads ``SourcererSDK.ENVIRONMENT_URLS``, so the real
    class attribute is preserved while the constructor call is replaced.
    """
    with patch("poly.handlers.sync_client.SourcererSDK") as mock_sdk_cls:
        mock_sdk_cls.ENVIRONMENT_URLS = SourcererSDK.ENVIRONMENT_URLS
        handler = SyncClientHandler("studio", "acc-1", "proj-1", branch_id="branch-1")
    handler._sdk = MagicMock()
    return handler


class ReadTopics(unittest.TestCase):
    """Tests for SyncClientHandler._read_topics_from_projection."""

    def test_parses_topic_fields_and_example_queries(self):
        """Topics are parsed with their content, actions, and flattened queries."""
        projection = {
            "knowledgeBase": {
                "topics": {
                    "entities": {
                        "TOPIC-1": {
                            "name": "Opening Hours",
                            "actions": "Answer politely",
                            "content": "We open at 9am",
                            "exampleQueries": [{"query": "when do you open"}, {"noquery": "x"}],
                            "isActive": True,
                        }
                    }
                }
            }
        }

        topics = SyncClientHandler._read_topics_from_projection(projection)

        self.assertEqual(list(topics), ["TOPIC-1"])
        topic = topics["TOPIC-1"]
        self.assertIsInstance(topic, Topic)
        self.assertEqual(topic.name, "Opening Hours")
        self.assertEqual(topic.content, "We open at 9am")
        self.assertEqual(topic.example_queries, ["when do you open"])

    def test_empty_projection_yields_no_topics(self):
        """A projection with no topics yields an empty mapping."""
        self.assertEqual(SyncClientHandler._read_topics_from_projection({}), {})


class ReadFunctions(unittest.TestCase):
    """Tests for SyncClientHandler._read_functions_from_projection."""

    def test_reads_special_flow_and_regular_functions(self):
        """Special, flow-transition, and regular functions are all parsed with types."""
        projection = {
            "specialFunctions": {
                "startFunction": {
                    "id": "FN-START",
                    "name": "start",
                    "description": "greeting",
                    "code": "pass",
                },
                "archivedFunction": {
                    "id": "FN-OLD",
                    "name": "old",
                    "description": "",
                    "code": "",
                    "archived": True,
                },
            },
            "flows": {
                "flows": {
                    "entities": {
                        "FLOW-1": {
                            "name": "Booking",
                            "transitionFunctions": {
                                "entities": {
                                    "FN-T": {
                                        "name": "transition",
                                        "description": "moves on",
                                        "code": "pass",
                                    }
                                }
                            },
                        }
                    }
                }
            },
            "functions": {
                "functions": {
                    "entities": {
                        "FN-G": {
                            "name": "lookup",
                            "description": "global fn",
                            "code": "pass",
                            "parameters": {
                                "entities": {
                                    "p1": {"id": "p1", "name": "arg", "type": "string"}
                                }
                            },
                        }
                    }
                }
            },
        }

        functions = SyncClientHandler._read_functions_from_projection(projection)

        self.assertEqual(set(functions), {"FN-START", "FN-T", "FN-G"})  # archived skipped
        self.assertEqual(functions["FN-START"].function_type, FunctionType.START)
        self.assertEqual(functions["FN-T"].function_type, FunctionType.TRANSITION)
        self.assertEqual(functions["FN-T"].flow_id, "FLOW-1")
        self.assertEqual(functions["FN-G"].function_type, FunctionType.GLOBAL)
        self.assertEqual(functions["FN-G"].parameters[0].name, "arg")
        self.assertIsInstance(functions["FN-G"], Function)


class ReadAgentSettings(unittest.TestCase):
    """Tests for SyncClientHandler._read_agent_settings_from_projection."""

    def test_parses_personality_role_and_rules(self):
        """Personality, role, and rules each produce a keyed settings resource."""
        projection = {
            "agentSettings": {
                "personality": {"adjectives": {"a": "friendly"}, "custom": "warm"},
                "role": {"value": "assistant", "additionalInfo": "helps callers", "custom": ""},
                "rules": {"behaviour": "never swear"},
            }
        }

        settings = SyncClientHandler._read_agent_settings_from_projection(projection)

        self.assertEqual(settings[SettingsPersonality]["personality"].custom, "warm")
        self.assertEqual(settings[SettingsRole]["role"].value, "assistant")
        self.assertEqual(
            settings[SettingsRole]["role"].additional_info, "helps callers"
        )
        self.assertEqual(settings[SettingsRules]["rules"].behaviour, "never swear")

    def test_missing_settings_yield_empty_mapping(self):
        """A projection with no agent settings yields an empty mapping."""
        self.assertEqual(SyncClientHandler._read_agent_settings_from_projection({}), {})


class ReadChannelSettings(unittest.TestCase):
    """Tests for SyncClientHandler._read_channel_settings_from_projection."""

    def test_parses_voice_greeting(self):
        """A voice greeting config produces a VoiceGreeting resource."""
        projection = {
            "channels": {
                "voice": {
                    "config": {
                        "greeting": {
                            "welcomeMessage": "Hello there",
                            "languageCode": "en-US",
                        }
                    }
                }
            }
        }

        settings = SyncClientHandler._read_channel_settings_from_projection(projection)

        greeting = settings[VoiceGreeting]["voice_greeting"]
        self.assertEqual(greeting.welcome_message, "Hello there")
        self.assertEqual(greeting.language_code, "en-US")

    def test_disabled_web_chat_skips_chat_settings(self):
        """When web chat status is falsy, chat settings are not parsed."""
        projection = {
            "channels": {
                "voice": {},
                "webChat": {"status": False, "config": {"greeting": {"welcomeMessage": "hi"}}},
            }
        }

        settings = SyncClientHandler._read_channel_settings_from_projection(projection)

        self.assertEqual(settings, {})


class ReadEntities(unittest.TestCase):
    """Tests for SyncClientHandler._read_entities_from_projection."""

    def test_parses_entity_fields(self):
        """Entities are parsed with their name, type, and config value."""
        projection = {
            "entities": {
                "entities": {
                    "entities": {
                        "ENT-1": {
                            "name": "colour",
                            "description": "a colour",
                            "type": "enum",
                            "config": {"value": {"values": ["red", "blue"]}},
                        }
                    }
                }
            }
        }

        entities = SyncClientHandler._read_entities_from_projection(projection)

        self.assertEqual(list(entities), ["ENT-1"])
        self.assertIsInstance(entities["ENT-1"], Entity)
        self.assertEqual(entities["ENT-1"].name, "colour")


class ReadFlows(unittest.TestCase):
    """Tests for SyncClientHandler._read_flows_from_projection nesting."""

    def test_parses_flow_config_step_and_condition(self):
        """A flow yields a FlowConfig, a FlowStep, and nested Conditions."""
        projection = {
            "flows": {
                "flows": {
                    "entities": {
                        "FLOW-1": {
                            "name": "Booking",
                            "description": "make a booking",
                            "startStepId": "STEP-1",
                            "steps": {
                                "entities": {
                                    "STEP-1": {
                                        "name": "Ask date",
                                        "type": "advanced_step",
                                        "prompt": "What date?",
                                        "position": {"x": 1.0, "y": 2.0},
                                        "conditions": [
                                            {
                                                "id": "COND-1",
                                                "config": {
                                                    "$case": "step_condition",
                                                    "value": {
                                                        "childStepId": "STEP-2",
                                                        "details": {
                                                            "label": "wants booking",
                                                            "description": "user wants to book",
                                                            "requiredEntities": ["ENT-1"],
                                                        },
                                                    },
                                                },
                                            }
                                        ],
                                    }
                                }
                            },
                        }
                    }
                }
            }
        }

        resources = SyncClientHandler._read_flows_from_projection(projection)

        flow_config = resources[FlowConfig]["FLOW-1"]
        self.assertIsInstance(flow_config, FlowConfig)
        self.assertEqual(flow_config.start_step, "STEP-1")

        step = resources[FlowStep]["Booking_STEP-1"]
        self.assertIsInstance(step, FlowStep)
        self.assertEqual(step.name, "Ask date")
        self.assertEqual(step.step_type, "advanced_step")

        condition = step.conditions[0]
        self.assertIsInstance(condition, Condition)
        self.assertEqual(condition.name, "wants booking")
        self.assertEqual(condition.condition_type, "step_condition")
        self.assertEqual(condition.child_step, "STEP-2")

    def test_function_step_parsed_separately(self):
        """A function_step within a flow yields a FunctionStep resource."""
        projection = {
            "flows": {
                "flows": {
                    "entities": {
                        "FLOW-1": {
                            "name": "Booking",
                            "startStepId": "STEP-FN",
                            "steps": {
                                "entities": {
                                    "STEP-FN": {
                                        "name": "Run lookup",
                                        "type": "function_step",
                                        "function": {"id": "FN-1", "code": "return 1"},
                                    }
                                }
                            },
                        }
                    }
                }
            }
        }

        resources = SyncClientHandler._read_flows_from_projection(projection)

        function_step = resources[FunctionStep]["Booking_STEP-FN"]
        self.assertIsInstance(function_step, FunctionStep)
        self.assertEqual(function_step.function_id, "FN-1")
        self.assertEqual(function_step.code, "return 1")


class ReadAsrSettings(unittest.TestCase):
    """Tests for SyncClientHandler._read_asr_settings_from_projection."""

    def test_parses_barge_in_and_interaction_style(self):
        """ASR settings expose barge-in and the latency interaction style."""
        projection = {
            "channels": {
                "voice": {
                    "asrSettings": {
                        "bargeIn": True,
                        "latencyConfig": {"interactionStyle": "fast"},
                    }
                }
            }
        }

        settings = SyncClientHandler._read_asr_settings_from_projection(projection)

        asr = settings["asr_settings"]
        self.assertIsInstance(asr, AsrSettings)
        self.assertTrue(asr.barge_in)
        self.assertEqual(asr.interaction_style, "fast")

    def test_missing_asr_settings_yield_empty_mapping(self):
        """Absent ASR settings yield an empty mapping."""
        self.assertEqual(SyncClientHandler._read_asr_settings_from_projection({}), {})


class QueueResources(unittest.TestCase):
    """Tests for SyncClientHandler.queue_resources ordering and command shape."""

    def setUp(self):
        self.handler = build_handler()
        # create_metadata is used to stamp each command; a bare Command works.
        self.handler._sdk.create_metadata.return_value = Command().metadata

    def test_creates_deletes_and_updates_produce_commands(self):
        """New, updated, and deleted resources each produce a queued command."""
        new = {Entity: {"ENT-1": Entity(resource_id="ENT-1", name="new", entity_type="free_text")}}
        updated = {
            Entity: {"ENT-2": Entity(resource_id="ENT-2", name="upd", entity_type="free_text")}
        }
        deleted = {
            Entity: {"ENT-3": Entity(resource_id="ENT-3", name="old", entity_type="free_text")}
        }

        commands = self.handler.queue_resources(
            deleted_resources=deleted, new_resources=new, updated_resources=updated
        )

        types = [c.type for c in commands]
        self.assertEqual(types, ["entity_delete", "entity_create", "entity_update"])
        self.assertEqual(self.handler._sdk.add_command_to_queue.call_count, 3)

    def test_priority_create_types_are_queued_first(self):
        """Variables (a priority-create type) are created before non-priority types."""
        new = {
            Topic: {"TOPIC-1": Topic(
                resource_id="TOPIC-1", name="t", actions="", content="c", example_queries=[]
            )},
            Variable: {"VAR-1": Variable(resource_id="VAR-1", name="balance")},
        }

        commands = self.handler.queue_resources(
            deleted_resources={}, new_resources=new, updated_resources={}
        )

        types = [c.type for c in commands]
        self.assertLess(types.index("variable_create"), types.index("create_topic"))

    def test_priority_delete_types_are_queued_first(self):
        """Variables (a priority-delete type) are deleted before non-priority types."""
        deleted = {
            Topic: {"TOPIC-1": Topic(
                resource_id="TOPIC-1", name="t", actions="", content="c", example_queries=[]
            )},
            Variable: {"VAR-1": Variable(resource_id="VAR-1", name="balance")},
        }

        commands = self.handler.queue_resources(
            deleted_resources=deleted, new_resources={}, updated_resources={}
        )

        types = [c.type for c in commands]
        self.assertLess(types.index("variable_delete"), types.index("delete_topic"))


class QueueCommand(unittest.TestCase):
    """Tests for SyncClientHandler.queue_command."""

    def test_sets_metadata_and_uuid_before_queueing(self):
        """A single command is stamped with metadata and a command id, then queued."""
        handler = build_handler()
        handler._sdk.create_metadata.return_value = Command().metadata
        command = Command(type="entity_create")

        handler.queue_command(command)

        self.assertTrue(command.command_id)  # a UUID was assigned
        handler._sdk.add_command_to_queue.assert_called_once_with(command)


class SendQueuedCommands(unittest.TestCase):
    """Tests for SyncClientHandler.send_queued_commands."""

    def test_empty_queue_returns_true_without_sending(self):
        """With nothing queued, the send is a no-op that reports success."""
        handler = build_handler()
        handler._sdk.get_queue_size.return_value = 0

        self.assertTrue(handler.send_queued_commands())
        handler._sdk.send_command_batch.assert_not_called()

    def test_successful_send_returns_true(self):
        """A successful batch send on a non-main branch reports success."""
        handler = build_handler()
        handler._sdk.get_queue_size.return_value = 2
        handler._sdk.branch_id = "branch-1"
        handler._sdk._command_queue = [Command(), Command()]
        # The branch must exist remotely, or the handler falls back to main and
        # tries to create a new branch before sending
        handler._sdk.fetch_branches.return_value = {"branches": [{"branchId": "branch-1"}]}

        self.assertTrue(handler.send_queued_commands())
        handler._sdk.send_command_batch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
