"""Tests for the AgentStudioProject class
Uses test project in tests/test_project


Copyright PolyAI Limited
"""

import json
import os
import unittest
from copy import deepcopy
from unittest import mock
from unittest.mock import MagicMock, patch

import poly.resources.resource_utils as resource_utils
from poly.project import AgentStudioProject
from poly.resources import (
    AsrSettings,
    ChatGreeting,
    ChatStylePrompt,
    Entity,
    ExperimentalConfig,
    FlowConfig,
    FlowStep,
    Function,
    FunctionStep,
    KeyphraseBoosting,
    Pronunciation,
    Resource,
    ResourceMapping,
    SettingsPersonality,
    SettingsRole,
    SettingsRules,
    SMSTemplate,
    Topic,
    TranscriptCorrection,
    Variable,
    VariantAttribute,
    VoiceDisclaimerMessage,
    VoiceGreeting,
    VoiceStylePrompt,
)
from poly.resources.resource import MultiResourceYamlResource
from poly.resources.flows import (
    ASRBiasing,
    Condition,
    DTMFConfig,
    StepType,
)
from poly.resources.function import FunctionType
from poly.tests.testing_utils import mock_read_from_file

DIR = os.path.dirname(os.path.abspath(__file__))
TEST_PROJECT_DIR = os.path.join(DIR, "test_projects")
TEST_DIR = os.path.join(TEST_PROJECT_DIR, "test_project")
PROJECT_DATA_LOC = os.path.join(TEST_DIR, "test_project.json")
PROJECT_DATA = json.loads(open(PROJECT_DATA_LOC).read())
EMPTY_PROJECT_DIR = os.path.join(TEST_PROJECT_DIR, "test_empty_project")
EMPTY_PROJECT_DATA_LOC = os.path.join(EMPTY_PROJECT_DIR, "empty_project.json")
EMPTY_PROJECT_DATA = json.loads(open(EMPTY_PROJECT_DATA_LOC).read())


class InitTest(unittest.TestCase):
    """Tests for the AgentStudioProject class"""

    def test_init(self):
        """Test the initialization of the AgentStudioProject class"""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        self.assertEqual(project.region, "us-1")
        self.assertEqual(project.account_id, "test_account")
        self.assertEqual(project.project_id, "test_project")


class SortPathsForReverseDeletionTest(unittest.TestCase):
    """Tests for _sort_paths_for_reverse_deletion (Pronunciation vs lexicographic order)."""

    def test_sort_paths_for_reverse_deletion(self):
        base = os.path.join("voice", "response_control", "pronunciations.yaml", "pronunciations")
        # Pronunciation: must be numeric reverse (11, 10, 9, ...), not lexicographic (9 before 10)
        pron_paths = {
            os.path.join(base, "9"),
            os.path.join(base, "10"),
            os.path.join(base, "11"),
        }
        result = AgentStudioProject._sort_paths_for_reverse_deletion(pron_paths, Pronunciation)
        self.assertEqual(
            result,
            [
                os.path.join(base, "11"),
                os.path.join(base, "10"),
                os.path.join(base, "9"),
            ],
            "Pronunciation paths must sort by integer position descending (11, 10, 9), not lexicographic",
        )
        # Non-Pronunciation: lexicographic reverse order
        entity_base = os.path.join("config", "entities.yaml", "entities")
        entity_paths = {
            os.path.join(entity_base, "a"),
            os.path.join(entity_base, "b"),
            os.path.join(entity_base, "c"),
        }
        result_entity = AgentStudioProject._sort_paths_for_reverse_deletion(entity_paths, Entity)
        self.assertEqual(
            result_entity,
            [
                os.path.join(entity_base, "c"),
                os.path.join(entity_base, "b"),
                os.path.join(entity_base, "a"),
            ],
            "Other resource types use lexicographic reverse order",
        )


class SerializationRoundTripTest(unittest.TestCase):
    """Tests for resource serialization/deserialization round-trip"""

    def test_flow_config_round_trip_excludes_extra_fields(self):
        """Regression test: resource_to_dict only serializes __init__ params.

        FlowConfig has 'functions' and 'steps' as dataclass fields but not
        in __init__. These must not appear in the serialized dict, so that
        deserialization via resource_class(**dict) works without TypeError.
        """
        config = FlowConfig(
            resource_id="flow-123",
            name="Test Flow",
            description="A test flow",
            start_step="step-1",
        )
        serialized = resource_utils.resource_to_dict(config)
        self.assertNotIn("functions", serialized)
        self.assertNotIn("steps", serialized)

        # Deserialize back — must not raise TypeError
        restored = FlowConfig(**serialized)
        self.assertEqual(restored.name, "Test Flow")
        self.assertEqual(restored.start_step, "step-1")

    def test_flow_step_round_trip_excludes_sub_resource_internals(self):
        """ASRBiasing/DTMFConfig set 'name' and 'resource_id' internally,
        but these are not __init__ params. They must be excluded from
        serialization so nested deserialization works.
        """
        step = FlowStep(
            resource_id="flow_step-1",
            name="Test Step",
            step_id="step-1",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type="advanced_step",
            prompt="Hello",
            asr_biasing=ASRBiasing(step_id="step-1", flow_id="flow-123"),
            dtmf_config=DTMFConfig(step_id="step-1", flow_id="flow-123"),
        )
        serialized = resource_utils.resource_to_dict(step)
        asr_dict = serialized["asr_biasing"]
        dtmf_dict = serialized["dtmf_config"]

        # Internal fields must not leak into serialized output
        self.assertNotIn("name", asr_dict)
        self.assertNotIn("resource_id", asr_dict)
        self.assertNotIn("name", dtmf_dict)
        self.assertNotIn("resource_id", dtmf_dict)

        # Deserialize back — must not raise TypeError
        restored = FlowStep(**serialized)
        self.assertEqual(restored.name, "Test Step")
        self.assertEqual(restored.asr_biasing.step_id, "step-1")


class DiscoverLocalResourcesTest(unittest.TestCase):
    """Tests for the discover_local_resources method"""

    def test_discover_local_resources(self):
        """Test the discovery of local resources"""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        local_resources = project.discover_local_resources()
        # Finds all entities (one path per entity in entities.yaml)
        self.assertEqual(len(local_resources[Entity]), 6)
        self.assertCountEqual(
            local_resources[Entity],
            [
                os.path.join(TEST_DIR, "config", "entities.yaml", "entities", "customer_name"),
                os.path.join(TEST_DIR, "config", "entities.yaml", "entities", "phone_number"),
                os.path.join(TEST_DIR, "config", "entities.yaml", "entities", "date"),
                os.path.join(TEST_DIR, "config", "entities.yaml", "entities", "party_size"),
                os.path.join(
                    TEST_DIR, "config", "entities.yaml", "entities", "confirmation_status"
                ),
                os.path.join(TEST_DIR, "config", "entities.yaml", "entities", "email"),
            ],
        )
        # Finds both Flows (order may vary due to filesystem)
        expected_flows = [
            os.path.join(TEST_DIR, "flows", "test_flow", "flow_config.yaml"),
            os.path.join(TEST_DIR, "flows", "test_flow_with_punctuation", "flow_config.yaml"),
        ]
        self.assertCountEqual(local_resources[FlowConfig], expected_flows)
        # Finds Settings (voice greeting/style_prompt/disclaimer in voice/configuration.yaml)
        self.assertEqual(
            local_resources[VoiceDisclaimerMessage],
            [os.path.join(TEST_DIR, "voice", "configuration.yaml", "disclaimer_messages")],
        )
        self.assertEqual(
            local_resources[VoiceGreeting],
            [os.path.join(TEST_DIR, "voice", "configuration.yaml", "greeting")],
        )
        self.assertEqual(
            local_resources[VoiceStylePrompt],
            [os.path.join(TEST_DIR, "voice", "configuration.yaml", "style_prompt")],
        )
        # Chat greeting/style_prompt in chat/configuration.yaml
        self.assertEqual(
            local_resources[ChatGreeting],
            [os.path.join(TEST_DIR, "chat", "configuration.yaml", "greeting")],
        )
        self.assertEqual(
            local_resources[ChatStylePrompt],
            [os.path.join(TEST_DIR, "chat", "configuration.yaml", "style_prompt")],
        )
        self.assertEqual(
            local_resources[SettingsPersonality],
            [os.path.join(TEST_DIR, "agent_settings", "personality.yaml")],
        )
        self.assertEqual(
            local_resources[SettingsRole],
            [os.path.join(TEST_DIR, "agent_settings", "role.yaml")],
        )
        self.assertEqual(
            local_resources[SettingsRules],
            [os.path.join(TEST_DIR, "agent_settings", "rules.txt")],
        )

        # Finds all Functions and Flow Steps
        self.assertEqual(len(local_resources[Function]), 13)
        self.assertEqual(len(local_resources[FlowStep]), 9)
        self.assertEqual(len(local_resources[FunctionStep]), 2)

        # Find Experimental Config
        self.assertEqual(
            local_resources[ExperimentalConfig],
            [os.path.join(TEST_DIR, "agent_settings", "experimental_config.json")],
        )

        # Find SMS Templates (one path per template in sms_templates.yaml)
        self.assertEqual(len(local_resources[SMSTemplate]), 2)
        self.assertCountEqual(
            local_resources[SMSTemplate],
            [
                os.path.join(
                    TEST_DIR, "config", "sms_templates.yaml", "sms_templates", "test_template_1"
                ),
                os.path.join(
                    TEST_DIR, "config", "sms_templates.yaml", "sms_templates", "test_template_2"
                ),
            ],
        )

        # Find Variables
        self.assertEqual(len(local_resources[Variable]), 3)
        self.assertCountEqual(
            local_resources[Variable],
            [
                os.path.join(TEST_DIR, "variables", "customer_name"),
                os.path.join(TEST_DIR, "variables", "payment_success"),
                os.path.join(TEST_DIR, "variables", "data_processed"),
            ],
        )

        # Find Keyphrase Boosting entries (canonical path: voice/speech_recognition)
        speech_recognition_path = os.path.join("voice", "speech_recognition")
        self.assertEqual(len(local_resources[KeyphraseBoosting]), 3)
        self.assertCountEqual(
            local_resources[KeyphraseBoosting],
            [
                os.path.join(
                    TEST_DIR,
                    speech_recognition_path,
                    "keyphrase_boosting.yaml",
                    "keyphrases",
                    "PolyAI",
                ),
                os.path.join(
                    TEST_DIR,
                    speech_recognition_path,
                    "keyphrase_boosting.yaml",
                    "keyphrases",
                    "reservation",
                ),
                os.path.join(
                    TEST_DIR,
                    speech_recognition_path,
                    "keyphrase_boosting.yaml",
                    "keyphrases",
                    "check_in",
                ),
            ],
        )

        # Find Transcript Corrections
        self.assertEqual(len(local_resources[TranscriptCorrection]), 2)
        self.assertCountEqual(
            local_resources[TranscriptCorrection],
            [
                os.path.join(
                    TEST_DIR,
                    speech_recognition_path,
                    "transcript_corrections.yaml",
                    "corrections",
                    "Email_domain_fix",
                ),
                os.path.join(
                    TEST_DIR,
                    speech_recognition_path,
                    "transcript_corrections.yaml",
                    "corrections",
                    "Number_normalization",
                ),
            ],
        )

        # Find ASR Settings (singleton)
        self.assertEqual(len(local_resources[AsrSettings]), 1)
        self.assertEqual(
            local_resources[AsrSettings],
            [os.path.join(TEST_DIR, speech_recognition_path, "asr_settings.yaml")],
        )

    def test_discover_local_resources_empty_project(self):
        project = AgentStudioProject.from_dict(EMPTY_PROJECT_DATA, EMPTY_PROJECT_DIR)
        local_resources = project.discover_local_resources()
        for resource_type in local_resources:
            self.assertEqual(local_resources[resource_type], [])


class FindNewKeptDeletedTest(unittest.TestCase):
    """Tests for the find_new_kept_deleted method"""

    def test_find_new_kept_deleted_nothing_changed(self):
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        local_resources = project.discover_local_resources()
        new_mappings, kept_mappings, deleted_mappings = project.find_new_kept_deleted(
            local_resources
        )
        self.assertEqual(new_mappings, [])
        self.assertEqual(deleted_mappings, [])

        # Kept mappings should be the same as the local resources
        expected_total_mappings = sum(len(v) for v in local_resources.values())
        self.assertEqual(len(kept_mappings), expected_total_mappings)

    def test_find_new_kept_deleted_new_resource(self):
        project_data = deepcopy(PROJECT_DATA)
        # Remove a topic so it seems there's a new one
        project_data["resources"]["topics"].pop("TOPIC-Topic 1")

        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        local_resources = project.discover_local_resources()
        new_mappings, kept_mappings, deleted_mappings = project.find_new_kept_deleted(
            local_resources
        )

        # No deleted mappings
        self.assertEqual(deleted_mappings, [])

        # Kept mappings should be the same as the local resources - 1
        expected_total_mappings = sum(len(v) for v in local_resources.values()) - 1
        self.assertEqual(len(kept_mappings), expected_total_mappings)

        # New mappings should have exactly 1 new entity
        self.assertEqual(len(new_mappings), 1)
        new_mapping = new_mappings[0]

        # Check that resource_id is randomly generated (format: TOPIC-{8 hex chars})
        self.assertRegex(new_mapping.resource_id, r"^TOPICS-[a-f0-9]{8}$")

        # Check all other fields match expected values
        self.assertEqual(new_mapping.resource_type, Topic)
        self.assertEqual(new_mapping.resource_name, "Topic 1")
        self.assertEqual(
            new_mapping.file_path,
            os.path.join(TEST_DIR, "topics", "Topic 1.yaml"),
        )
        self.assertEqual(new_mapping.flow_name, None)
        self.assertEqual(new_mapping.resource_prefix, None)

    def test_find_new_kept_deleted_deleted_resource(self):
        project_data = deepcopy(PROJECT_DATA)
        # Add an extra function so it seems there's a deleted one
        project_data["resources"]["functions"]["FUNCTION-extra_function"] = {
            "resource_id": "FUNCTION-extra_function",
            "name": "extra_function",
            "description": "An extra test function for global use.",
            "code": 'from _gen import *  # <AUTO GENERATED>\n\n@func_description(\'A test function for global use.\')\ndef extra_function(conv: Conversation):\n    """A test function for global use."""\n    return "Hello from global function"\n',
            "parameters": [],
            "latency_control": {},
            "flow_id": None,
            "flow_name": None,
            "function_type": "global",
        }

        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        local_resources = project.discover_local_resources()

        new_mappings, kept_mappings, deleted_mappings = project.find_new_kept_deleted(
            local_resources
        )

        # No new mappings
        self.assertEqual(new_mappings, [])

        # Kept mappings should be the same as the local resources
        expected_total_mappings = sum(len(v) for v in local_resources.values())
        self.assertEqual(len(kept_mappings), expected_total_mappings)

        # Deleted mappings should have exactly 1 deleted function
        self.assertEqual(
            deleted_mappings,
            [
                ResourceMapping(
                    resource_id="FUNCTION-extra_function",
                    resource_type=Function,
                    resource_name="extra_function",
                    file_path=os.path.join(TEST_DIR, "functions", "extra_function.py"),
                    flow_name=None,
                    resource_prefix="fn",
                )
            ],
        )

    def test_find_new_kept_deleted_mixed_changes(self):
        project_data = deepcopy(PROJECT_DATA)
        # Remove a function so it seems there's a new one
        project_data["resources"]["topics"].pop("TOPIC-Topic 1")
        # Add an extra function so it seems there's a deleted one
        project_data["resources"]["functions"]["FUNCTION-extra_function"] = {
            "resource_id": "FUNCTION-extra_function",
            "name": "extra_function",
            "description": "An extra test function for global use.",
            "code": 'from _gen import *  # <AUTO GENERATED>\n\n@func_description(\'A test function for global use.\')\ndef extra_function(conv: Conversation):\n    """A test function for global use."""\n    return "Hello from global function"\n',
            "parameters": [],
            "latency_control": {},
            "flow_id": None,
            "flow_name": None,
            "function_type": "global",
        }

        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        local_resources = project.discover_local_resources()
        new_mappings, kept_mappings, deleted_mappings = project.find_new_kept_deleted(
            local_resources
        )

        # New mappings should have exactly 1 new topic
        self.assertEqual(len(new_mappings), 1)
        new_mapping = new_mappings[0]
        self.assertEqual(new_mapping.resource_type, Topic)

        # Kept mappings should be the same as the local resources - 1
        expected_total_mappings = sum(len(v) for v in local_resources.values()) - 1
        self.assertEqual(len(kept_mappings), expected_total_mappings)

        # Deleted mappings should have exactly 1 deleted function
        self.assertEqual(len(deleted_mappings), 1)
        deleted_mapping = deleted_mappings[0]
        self.assertEqual(deleted_mapping.resource_type, Function)


class ProjectStatusTest(unittest.TestCase):
    """Tests for the project_status method"""

    def test_project_status_no_changes(self):
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        files_with_conflicts, modified_files, new_files, deleted_files = project.project_status()
        self.assertEqual(files_with_conflicts, [])
        self.assertEqual(modified_files, [])
        self.assertEqual(new_files, [])
        self.assertEqual(deleted_files, [])

    def test_project_status_new_resource(self):
        project_data = deepcopy(PROJECT_DATA)
        # Remove a function so it seems there's a new one
        project_data["resources"]["topics"].pop("TOPIC-Topic 1")
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        files_with_conflicts, modified_files, new_files, deleted_files = project.project_status()
        self.assertEqual(files_with_conflicts, [])
        self.assertEqual(new_files, [os.path.join(TEST_DIR, "topics", "Topic 1.yaml")])
        self.assertEqual(modified_files, [])
        self.assertEqual(deleted_files, [])

    def test_project_status_deleted_resource(self):
        project_data = deepcopy(PROJECT_DATA)
        # Add an extra function so it seems there's a deleted one
        project_data["resources"]["functions"]["FUNCTION-extra_function"] = {
            "resource_id": "FUNCTION-extra_function",
            "name": "extra_function",
            "description": "An extra test function for global use.",
            "code": 'from _gen import *  # <AUTO GENERATED>\n\n@func_description(\'A test function for global use.\')\ndef extra_function(conv: Conversation):\n    """A test function for global use."""\n    return "Hello from global function"\n',
            "parameters": [],
            "latency_control": {},
            "flow_id": None,
            "flow_name": None,
            "function_type": "global",
        }
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        files_with_conflicts, modified_files, new_files, deleted_files = project.project_status()
        self.assertEqual(files_with_conflicts, [])
        self.assertEqual(modified_files, [])
        self.assertEqual(new_files, [])
        self.assertEqual(deleted_files, [os.path.join(TEST_DIR, "functions", "extra_function.py")])

    def test_project_status_modified_resource(self):
        project_data = deepcopy(PROJECT_DATA)
        # Modify a function so it seems there's a modified one
        project_data["resources"]["functions"]["FUNCTION-test_function"]["code"] = (
            'from _gen import *  # <AUTO GENERATED>\n\n@func_description(\'A test function for global use.\')\ndef extra_function(conv: Conversation):\n    """A test function for global use."""\n    return "Hello from global function"\n'
        )
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        files_with_conflicts, modified_files, new_files, deleted_files = project.project_status()
        self.assertEqual(files_with_conflicts, [])
        self.assertEqual(modified_files, [os.path.join(TEST_DIR, "functions", "test_function.py")])
        self.assertEqual(new_files, [])
        self.assertEqual(deleted_files, [])

    def test_project_status_merge_conflict(self):
        project_data = deepcopy(PROJECT_DATA)

        # Add a merge conflict to a file read from local
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        with mock_read_from_file(
            {
                os.path.join(
                    TEST_DIR, "functions", "test_function.py"
                ): 'from _gen import *  # <AUTO GENERATED>\n\n@func_description(\'A test function for global use.\')\ndef test_function(conv: Conversation):\n    """A test function for global use."""\n<<<<<<<\n    return "Hello from global function"\n=======\n    return "Hello from merge conflict function"\n>>>>>>>\n'
            }
        ):
            files_with_conflicts, modified_files, new_files, deleted_files = (
                project.project_status()
            )
        self.assertEqual(
            files_with_conflicts, [os.path.join(TEST_DIR, "functions", "test_function.py")]
        )
        self.assertEqual(modified_files, [os.path.join(TEST_DIR, "functions", "test_function.py")])
        self.assertEqual(new_files, [])
        self.assertEqual(deleted_files, [])

    def test_project_status_mixed_changes(self):
        project_data = deepcopy(PROJECT_DATA)
        # Remove a function so it seems there's a new one
        project_data["resources"]["topics"].pop("TOPIC-Topic 1")
        # Add an extra function so it seems there's a deleted one
        project_data["resources"]["functions"]["FUNCTION-extra_function"] = {
            "resource_id": "FUNCTION-extra_function",
            "name": "extra_function",
            "description": "An extra test function for global use.",
            "code": 'from _gen import *  # <AUTO GENERATED>\n\n@func_description(\'A test function for global use.\')\ndef extra_function(conv: Conversation):\n    """A test function for global use."""\n    return "Hello from global function"\n',
            "parameters": [],
            "latency_control": {},
            "flow_id": None,
            "flow_name": None,
            "function_type": "global",
        }
        # Modify a flow step so it seems there's a modified one
        project_data["resources"]["flow_steps"]["test_flow_start_step"]["prompt"] = (
            "Modified prompt"
        )

        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        files_with_conflicts, modified_files, new_files, deleted_files = project.project_status()
        self.assertEqual(files_with_conflicts, [])
        self.assertEqual(
            modified_files,
            [os.path.join(TEST_DIR, "flows", "test_flow", "steps", "start_step.yaml")],
        )
        self.assertEqual(new_files, [os.path.join(TEST_DIR, "topics", "Topic 1.yaml")])
        self.assertEqual(deleted_files, [os.path.join(TEST_DIR, "functions", "extra_function.py")])


class GetDiffsTest(unittest.TestCase):
    """Tests for the get_diffs method"""

    def test_get_diffs_no_changes(self):
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        diffs = project.get_diffs(all_files=True)
        self.assertEqual(diffs, {})

    def test_get_diffs_new_resource(self):
        project_data = deepcopy(PROJECT_DATA)
        # Remove a topic so it seems there's a new one
        project_data["resources"]["topics"].pop("TOPIC-Topic 1")
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        diffs = project.get_diffs(all_files=True)

        topic_path = "topics/Topic 1.yaml"
        self.assertIn(topic_path, diffs)

        diff = diffs[topic_path]
        self.assertIn("--- original", diff)
        self.assertIn("+++ updated", diff)
        self.assertIn("+content: This topic covers general inquiries", diff)

    def test_get_diffs_deleted_resource(self):
        project_data = deepcopy(PROJECT_DATA)
        # Add an extra function so it seems there's a deleted one
        project_data["resources"]["functions"]["FUNCTION-extra_function"] = {
            "resource_id": "FUNCTION-extra_function",
            "name": "extra_function",
            "description": "An extra test function for global use.",
            "code": 'def extra_function(conv: Conversation):\n    """A test function for global use."""\n    return "Hello from global function"\n',
            "parameters": [],
            "latency_control": {},
            "flow_id": None,
            "flow_name": None,
            "function_type": "global",
        }
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        diffs = project.get_diffs(all_files=True)

        func_path = os.path.join(TEST_DIR, "functions", "extra_function.py")
        self.assertIn(func_path, diffs)

        diff = diffs[func_path]
        self.assertIn("--- original", diff)
        self.assertIn("+++ updated", diff)
        self.assertIn("-def extra_function", diff)

    def test_get_diffs_modified_resource(self):
        project_data = deepcopy(PROJECT_DATA)
        # Modify a function so it seems there's a modified one
        project_data["resources"]["functions"]["FUNCTION-test_function"]["code"] = (
            'from _gen import *  # <AUTO GENERATED>\n\n@func_description(\'A test function for global use.\')\ndef test_function(conv: Conversation):\n    """A modified test function."""\n    return "Modified return value"\n'
        )
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        diffs = project.get_diffs(all_files=True)

        func_path = "functions/test_function.py"
        self.assertIn(func_path, diffs)

        diff = diffs[func_path]
        self.assertIn("--- original", diff)
        self.assertIn("+++ updated", diff)
        self.assertTrue(len(diff) > 0)

    def test_get_diffs_mixed_changes(self):
        project_data = deepcopy(PROJECT_DATA)
        # Remove a topic so it seems there's a new one
        project_data["resources"]["topics"].pop("TOPIC-Topic 1")
        # Add an extra function so it seems there's a deleted one
        project_data["resources"]["functions"]["FUNCTION-extra_function"] = {
            "resource_id": "FUNCTION-extra_function",
            "name": "extra_function",
            "description": "An extra test function for global use.",
            "code": 'def extra_function(conv: Conversation):\n    """A test function for global use."""\n    return "Hello from global function"\n',
            "parameters": [],
            "latency_control": {},
            "flow_id": None,
            "flow_name": None,
            "function_type": "global",
        }
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        diffs = project.get_diffs(all_files=True)

        topic_path = "topics/Topic 1.yaml"
        func_path = os.path.join(TEST_DIR, "functions", "extra_function.py")
        self.assertIn(topic_path, diffs)
        self.assertIn(func_path, diffs)

        topic_diff = diffs[topic_path]
        self.assertIn("--- original", topic_diff)
        self.assertIn("+++ updated", topic_diff)

        func_diff = diffs[func_path]
        self.assertIn("--- original", func_diff)
        self.assertIn("+++ updated", func_diff)

    def test_get_diffs_specific_files(self):
        project_data = deepcopy(PROJECT_DATA)
        # Remove a topic so it seems there's a new one
        project_data["resources"]["topics"].pop("TOPIC-Topic 1")
        # Add an extra function so it seems there's a deleted one
        project_data["resources"]["functions"]["FUNCTION-extra_function"] = {
            "resource_id": "FUNCTION-extra_function",
            "name": "extra_function",
            "description": "An extra test function for global use.",
            "code": 'def extra_function(conv: Conversation):\n    """A test function for global use."""\n    return "Hello from global function"\n',
            "parameters": [],
            "latency_control": {},
            "flow_id": None,
            "flow_name": None,
            "function_type": "global",
        }
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        requested_file = os.path.join(TEST_DIR, "topics", "Topic 1.yaml")
        diffs = project.get_diffs(files=[requested_file])

        # Topic diff
        topic_path = "topics/Topic 1.yaml"
        self.assertIn(topic_path, diffs)
        diff = diffs[topic_path]
        self.assertIn("--- original", diff)
        self.assertIn("+++ updated", diff)

        # No diff for function
        func_path = os.path.join(TEST_DIR, "functions", "extra_function.py")
        self.assertNotIn(func_path, diffs)


class CleanResourcesBeforePushTest(unittest.TestCase):
    """Tests for the _clean_resources_before_push method"""

    def setUp(self):
        self.project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

    def test_clean_resources_before_push_groups_steps_and_functions(self):
        # Create a flow config with steps and functions
        flow_config = FlowConfig(
            resource_id="flow-123",
            name="Test Flow",
            description="A test flow",
            start_step="step-1",
        )
        flow_step = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Start Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.ADVANCED_STEP,
            prompt="Hello",
            position={"x": 0.0, "y": 0.0},
        )
        flow_function = Function(
            resource_id="flow-123_func-1",
            name="test_func",
            description="A test function",
            code="def test_func(conv): pass",
            parameters=[],
            latency_control={},
            flow_id="flow-123",
            flow_name="Test Flow",
            function_type=None,
        )

        new_resources = {
            FlowConfig: {"flow-123": flow_config},
            FlowStep: {"flow-123_step-1": flow_step},
            Function: {"flow-123_func-1": flow_function},
        }
        updated_resources = {}
        deleted_resources = {}

        push_changes = self.project._clean_resources_before_push(
            {},
            new_resources,
            updated_resources,
            deleted_resources,
        )
        cleaned_new = push_changes.main.new

        # Flow config should have steps and functions attached
        self.assertEqual(len(cleaned_new[FlowConfig]["flow-123"].steps), 1)
        self.assertEqual(len(cleaned_new[FlowConfig]["flow-123"].functions), 1)
        # Steps and functions should be removed from top-level dict
        self.assertNotIn(FlowStep, cleaned_new)
        self.assertNotIn(Function, cleaned_new)

    def test_clean_resources_before_push_removes_steps_on_flow_delete(self):
        # Create a flow config to be deleted
        flow_config = FlowConfig(
            resource_id="flow-123",
            name="Test Flow",
            description="A test flow",
            start_step="step-1",
        )
        flow_step = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Start Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.ADVANCED_STEP,
            prompt="Hello",
            position={"x": 0.0, "y": 0.0},
        )
        flow_function = Function(
            resource_id="flow-123_func-1",
            name="test_func",
            description="A test function",
            code="def test_func(conv): pass",
            parameters=[],
            latency_control={},
            flow_id="flow-123",
            flow_name="Test Flow",
            function_type=None,
        )

        new_resources = {}
        updated_resources = {}
        deleted_resources = {
            FlowConfig: {"flow-123": flow_config},
            FlowStep: {"flow-123_step-1": flow_step},
            Function: {"flow-123_func-1": flow_function},
        }

        push_changes = self.project._clean_resources_before_push(
            {},
            new_resources,
            updated_resources,
            deleted_resources,
        )
        cleaned_deleted = push_changes.main.deleted

        # Steps and functions should be removed from deleted_resources
        # (The dict keys remain but are empty)
        self.assertEqual(len(cleaned_deleted.get(FlowStep, {})), 0)
        self.assertEqual(len(cleaned_deleted.get(Function, {})), 0)
        # Only flow config should remain
        self.assertIn("flow-123", cleaned_deleted[FlowConfig])

    def test_clean_resources_before_push_deletes_and_recreates_changed_flow_steps(self):
        # Create an original flow step with ADVANCED_STEP type
        original_flow_step = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Start Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.ADVANCED_STEP,
            prompt="Hello",
            position={"x": 0.0, "y": 0.0},
        )

        # Add the original step to project resources
        self.project.resources.setdefault(FlowStep, {})["flow-123_step-1"] = original_flow_step

        # Create an updated flow step with DEFAULT_STEP type (changed step_type)
        updated_flow_step = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Start Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.DEFAULT_STEP,  # Changed from ADVANCED_STEP
            prompt="Hello",
            position={"x": 0.0, "y": 0.0},
            conditions=[],  # DEFAULT_STEP requires conditions
        )

        new_resources = {}
        updated_resources = {
            FlowStep: {"flow-123_step-1": updated_flow_step},
        }
        deleted_resources = {}

        push_changes = self.project._clean_resources_before_push(
            {},
            new_resources,
            updated_resources,
            deleted_resources,
        )
        cleaned_new = push_changes.main.new
        cleaned_updated = push_changes.main.updated
        cleaned_deleted = push_changes.main.deleted

        # The original step should be in deleted_resources
        self.assertIn(FlowStep, cleaned_deleted)
        self.assertIn("flow-123_step-1", cleaned_deleted[FlowStep])
        self.assertEqual(
            cleaned_deleted[FlowStep]["flow-123_step-1"].step_type, StepType.ADVANCED_STEP
        )

        # The updated step should be in new_resources
        self.assertIn(FlowStep, cleaned_new)
        self.assertIn("flow-123_step-1", cleaned_new[FlowStep])
        self.assertEqual(cleaned_new[FlowStep]["flow-123_step-1"].step_type, StepType.DEFAULT_STEP)

        # The step should NOT be in updated_resources anymore
        self.assertNotIn("flow-123_step-1", cleaned_updated.get(FlowStep, {}))

    def test_clean_resources_before_push_start_step_type_change_uses_dummy_workaround(self):
        """When changing start step type, use pre/post push with empty default_step dummy."""
        flow_config = FlowConfig(
            resource_id="flow-123",
            name="Test Flow",
            description="A test flow",
            start_step="step-1",
        )
        original_flow_step = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Start Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.ADVANCED_STEP,
            prompt="Hello",
            position={"x": 0.0, "y": 0.0},
        )
        updated_flow_step = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Start Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.DEFAULT_STEP,
            prompt="Hello",
            position={"x": 0.0, "y": 0.0},
            conditions=[],
        )

        self.project.resources.setdefault(FlowStep, {})["flow-123_step-1"] = original_flow_step
        self.project.resources.setdefault(FlowConfig, {})["flow-123"] = flow_config

        new_resources = {}
        updated_resources = {FlowStep: {"flow-123_step-1": updated_flow_step}}
        deleted_resources = {}

        push_changes = self.project._clean_resources_before_push(
            {FlowConfig: {"flow-123": flow_config}},
            new_resources,
            updated_resources,
            deleted_resources,
        )
        cleaned_new = push_changes.main.new
        cleaned_updated = push_changes.main.updated
        cleaned_deleted = push_changes.main.deleted
        pre_push_new = push_changes.pre.new
        pre_push_updated = push_changes.pre.updated
        post_push_deleted = push_changes.post.deleted

        # Pre-push: dummy step and flow config switch to dummy
        self.assertIn(FlowStep, pre_push_new)
        dummy_id = "Test Flow_step-1_temp"
        self.assertIn(dummy_id, pre_push_new[FlowStep])
        dummy = pre_push_new[FlowStep][dummy_id]
        self.assertEqual(dummy.step_id, "step-1_temp")
        self.assertEqual(dummy.step_type, StepType.DEFAULT_STEP)
        self.assertEqual(dummy.conditions, [])
        self.assertEqual(dummy.extracted_entities, [])

        self.assertIn(FlowConfig, pre_push_updated)
        self.assertEqual(pre_push_updated[FlowConfig]["flow-123"].start_step, "step-1_temp")

        # Post-push: delete dummy
        self.assertIn(FlowStep, post_push_deleted)
        self.assertIn(dummy_id, post_push_deleted[FlowStep])

        # Main push: original in deleted, new in new, flow config restore in updated
        self.assertIn(FlowStep, cleaned_deleted)
        self.assertIn("flow-123_step-1", cleaned_deleted[FlowStep])
        self.assertEqual(
            cleaned_deleted[FlowStep]["flow-123_step-1"].step_type,
            StepType.ADVANCED_STEP,
        )
        self.assertIn(FlowStep, cleaned_new)
        self.assertIn("flow-123_step-1", cleaned_new[FlowStep])
        self.assertEqual(
            cleaned_new[FlowStep]["flow-123_step-1"].step_type,
            StepType.DEFAULT_STEP,
        )
        self.assertIn(FlowConfig, cleaned_updated)
        self.assertEqual(cleaned_updated[FlowConfig]["flow-123"].start_step, "step-1")

    def test_clean_resources_before_push_deletes_start_step_after_switching_to_different_step(
        self,
    ):
        """When deleting start step and switching to different step, defer delete to post-push."""
        flow_config = FlowConfig(
            resource_id="flow-123",
            name="Test Flow",
            description="A test flow",
            start_step="step-1",
        )
        old_start_step = FlowStep(
            resource_id="Test Flow_step-1",
            step_id="step-1",
            name="Start Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.DEFAULT_STEP,
            prompt="Hello",
            position={"x": 0.0, "y": 0.0},
            conditions=[],
            extracted_entities=[],
        )
        new_start_step = FlowStep(
            resource_id="Test Flow_step-2",
            step_id="step-2",
            name="Other Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.DEFAULT_STEP,
            prompt="Hi",
            position={"x": 0.0, "y": 0.0},
            conditions=[],
            extracted_entities=[],
        )
        updated_flow_config = FlowConfig(
            resource_id="flow-123",
            name="Test Flow",
            description="A test flow",
            start_step="step-2",
        )

        self.project.resources.setdefault(FlowStep, {})["Test Flow_step-1"] = old_start_step
        self.project.resources.setdefault(FlowConfig, {})["flow-123"] = flow_config

        new_resources = {FlowStep: {"Test Flow_step-2": new_start_step}}
        updated_resources = {FlowConfig: {"flow-123": updated_flow_config}}
        deleted_resources = {FlowStep: {"Test Flow_step-1": old_start_step}}

        push_changes = self.project._clean_resources_before_push(
            {},
            new_resources,
            updated_resources,
            deleted_resources,
        )
        cleaned_new = push_changes.main.new
        cleaned_updated = push_changes.main.updated
        cleaned_deleted = push_changes.main.deleted
        post_push_deleted = push_changes.post.deleted

        # Old step should be moved to post-push deleted (not in main push deleted)
        self.assertNotIn("Test Flow_step-1", cleaned_deleted.get(FlowStep, {}))
        self.assertIn(FlowStep, post_push_deleted)
        self.assertIn("Test Flow_step-1", post_push_deleted[FlowStep])

        # New step in new, flow config in updated
        self.assertIn("Test Flow_step-2", cleaned_new[FlowStep])
        self.assertIn(FlowConfig, cleaned_updated)
        self.assertEqual(cleaned_updated[FlowConfig]["flow-123"].start_step, "step-2")

    def test_clean_resources_before_push_same_name_start_step_replacement_uses_dummy(
        self,
    ):
        """When replacing start step with same name (sync_ids), use dummy workaround.

        Sync scenario: old step from branch has different step_id (e.g. UUID), new step
        from main has step_id from file name. Same name triggers dummy workaround.
        """
        # Old flow config points to old step (from branch)
        flow_config = FlowConfig(
            resource_id="flow-123",
            name="Test Flow",
            description="A test flow",
            start_step="step-abc123",
        )
        # Old step from branch - different step_id (e.g. from UUID before sync)
        old_start_step = FlowStep(
            resource_id="Test Flow_step-abc123",
            step_id="step-abc123",
            name="Start Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.DEFAULT_STEP,
            prompt="Old prompt",
            position={"x": 0.0, "y": 0.0},
            conditions=[],
            extracted_entities=[],
        )
        # New step from main - same name, step_id from file
        new_start_step = FlowStep(
            resource_id="Test Flow_step-1",
            step_id="step-1",
            name="Start Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.DEFAULT_STEP,
            prompt="New prompt",
            position={"x": 0.0, "y": 0.0},
            conditions=[],
            extracted_entities=[],
        )
        updated_flow_config = FlowConfig(
            resource_id="flow-123",
            name="Test Flow",
            description="A test flow",
            start_step="step-1",
        )

        self.project.resources.setdefault(FlowStep, {})["Test Flow_step-abc123"] = old_start_step
        self.project.resources.setdefault(FlowConfig, {})["flow-123"] = flow_config

        new_resources = {FlowStep: {"Test Flow_step-1": new_start_step}}
        updated_resources = {FlowConfig: {"flow-123": updated_flow_config}}
        deleted_resources = {FlowStep: {"Test Flow_step-abc123": old_start_step}}

        push_changes = self.project._clean_resources_before_push(
            {},
            new_resources,
            updated_resources,
            deleted_resources,
        )
        cleaned_new = push_changes.main.new
        cleaned_updated = push_changes.main.updated
        cleaned_deleted = push_changes.main.deleted
        pre_push_new = push_changes.pre.new
        pre_push_updated = push_changes.pre.updated
        post_push_deleted = push_changes.post.deleted

        # Pre-push: dummy step and flow config switch to dummy
        self.assertIn(FlowStep, pre_push_new)
        dummy_id = "Test Flow_step-abc123_temp"
        self.assertIn(dummy_id, pre_push_new[FlowStep])
        dummy = pre_push_new[FlowStep][dummy_id]
        self.assertEqual(dummy.step_id, "step-abc123_temp")

        self.assertIn(FlowConfig, pre_push_updated)
        self.assertEqual(pre_push_updated[FlowConfig]["flow-123"].start_step, "step-abc123_temp")

        # Post-push: delete dummy (not old step - old stays in main push deleted)
        self.assertIn(FlowStep, post_push_deleted)
        self.assertIn(dummy_id, post_push_deleted[FlowStep])

        # Main push: old in deleted, new in new, flow config in updated
        self.assertIn("Test Flow_step-abc123", cleaned_deleted[FlowStep])
        self.assertIn("Test Flow_step-1", cleaned_new[FlowStep])
        self.assertIn(FlowConfig, cleaned_updated)
        self.assertEqual(cleaned_updated[FlowConfig]["flow-123"].start_step, "step-1")

    def test_clean_resources_before_push_function_step_start_step_defer_delete(
        self,
    ):
        """When deleting FunctionStep start step and switching to different step, defer to post-push."""
        flow_config = FlowConfig(
            resource_id="flow-123",
            name="Test Flow",
            description="A test flow",
            start_step="func_step",
        )
        old_function_step = FunctionStep(
            resource_id="Test Flow_func_step",
            step_id="func_step",
            name="Func Start",
            flow_id="flow-123",
            flow_name="Test Flow",
            code="def handler(conv): pass",
            position={"x": 0.0, "y": 0.0},
            function_id="FUNC-123",
        )
        new_flow_step = FlowStep(
            resource_id="Test Flow_step-2",
            step_id="step-2",
            name="New Start",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.DEFAULT_STEP,
            prompt="Hi",
            position={"x": 0.0, "y": 0.0},
            conditions=[],
            extracted_entities=[],
        )
        updated_flow_config = FlowConfig(
            resource_id="flow-123",
            name="Test Flow",
            description="A test flow",
            start_step="step-2",
        )

        self.project.resources.setdefault(FunctionStep, {})["Test Flow_func_step"] = (
            old_function_step
        )
        self.project.resources.setdefault(FlowConfig, {})["flow-123"] = flow_config

        new_resources = {FlowStep: {"Test Flow_step-2": new_flow_step}}
        updated_resources = {FlowConfig: {"flow-123": updated_flow_config}}
        deleted_resources = {FunctionStep: {"Test Flow_func_step": old_function_step}}

        push_changes = self.project._clean_resources_before_push(
            {},
            new_resources,
            updated_resources,
            deleted_resources,
        )
        cleaned_deleted = push_changes.main.deleted
        post_push_deleted = push_changes.post.deleted

        # Old FunctionStep should be in post-push deleted
        self.assertNotIn("Test Flow_func_step", cleaned_deleted.get(FunctionStep, {}))
        self.assertIn(FunctionStep, post_push_deleted)
        self.assertIn("Test Flow_func_step", post_push_deleted[FunctionStep])

    def test_clean_resources_before_push_function_step_same_name_uses_dummy(
        self,
    ):
        """When replacing FunctionStep start step with same name, use dummy workaround.

        Sync scenario: old from branch has different step_id, new from main has
        step_id from file name. Same name triggers dummy workaround.
        """
        # Old flow config points to old step (from branch)
        flow_config = FlowConfig(
            resource_id="flow-123",
            name="Test Flow",
            description="A test flow",
            start_step="func_step_old",
        )
        old_function_step = FunctionStep(
            resource_id="Test Flow_func_step_old",
            step_id="func_step_old",
            name="Func Start",
            flow_id="flow-123",
            flow_name="Test Flow",
            code="def handler(conv): pass",
            position={"x": 0.0, "y": 0.0},
            function_id="FUNC-123",
        )
        new_function_step = FunctionStep(
            resource_id="Test Flow_func_step",
            step_id="func_step",
            name="Func Start",
            flow_id="flow-123",
            flow_name="Test Flow",
            code="def handler(conv): return conv",
            position={"x": 0.0, "y": 0.0},
            function_id="FUNC-456",
        )
        updated_flow_config = FlowConfig(
            resource_id="flow-123",
            name="Test Flow",
            description="A test flow",
            start_step="func_step",
        )

        self.project.resources.setdefault(FunctionStep, {})["Test Flow_func_step_old"] = (
            old_function_step
        )
        self.project.resources.setdefault(FlowConfig, {})["flow-123"] = flow_config

        new_resources = {FunctionStep: {"Test Flow_func_step": new_function_step}}
        updated_resources = {FlowConfig: {"flow-123": updated_flow_config}}
        deleted_resources = {FunctionStep: {"Test Flow_func_step_old": old_function_step}}

        push_changes = self.project._clean_resources_before_push(
            {},
            new_resources,
            updated_resources,
            deleted_resources,
        )
        cleaned_new = push_changes.main.new
        cleaned_deleted = push_changes.main.deleted
        pre_push_new = push_changes.pre.new
        pre_push_updated = push_changes.pre.updated
        post_push_deleted = push_changes.post.deleted

        # Pre-push: dummy step (uses old step_id for dummy)
        self.assertIn(FlowStep, pre_push_new)
        self.assertIn("Test Flow_func_step_old_temp", pre_push_new[FlowStep])
        self.assertIn(FlowConfig, pre_push_updated)

        # Post-push: delete dummy
        self.assertIn(FlowStep, post_push_deleted)
        self.assertIn("Test Flow_func_step_old_temp", post_push_deleted[FlowStep])

        # Main push: old in deleted, new in new
        self.assertIn("Test Flow_func_step_old", cleaned_deleted[FunctionStep])
        self.assertIn("Test Flow_func_step", cleaned_new[FunctionStep])

    def test_clean_resources_before_push_new_flow_function_step_as_start_fixes_with_dummy(
        self,
    ):
        """When creating a new flow with a function step as start step, use dummy then fix.

        API requires a non-function step as start when creating a flow. We create a
        temporary default step as start, then update the flow to use the function step
        and delete the dummy in post-push.
        """
        flow_config_id = "flow-new-func-start"
        flow_config = FlowConfig(
            resource_id=flow_config_id,
            name="New Flow",
            description="Flow with function step as start",
            start_step="entry_func",
        )
        function_start_step = FunctionStep(
            resource_id="New Flow_entry_func",
            step_id="entry_func",
            name="Entry",
            flow_id=flow_config_id,
            flow_name="New Flow",
            code="def entry_func(conv, flow): pass",
            position={"x": 0.0, "y": 0.0},
            function_id="FUNC-entry",
        )

        new_resources = {
            FlowConfig: {flow_config_id: flow_config},
            FunctionStep: {"New Flow_entry_func": function_start_step},
        }
        push_changes = self.project._clean_resources_before_push(
            {},
            new_resources,
            {},
            {},
        )
        main_new = push_changes.main.new
        main_updated = push_changes.main.updated
        post_deleted = push_changes.post.deleted

        # Flow is created with a dummy default step as start
        self.assertIn(FlowConfig, main_new)
        created_flow = main_new[FlowConfig][flow_config_id]
        self.assertEqual(created_flow.start_step, "entry_func_start_step_temp")
        step_ids = [s.step_id for s in created_flow.steps]
        self.assertIn("entry_func_start_step_temp", step_ids)
        dummy_step = next(
            s for s in created_flow.steps if s.step_id == "entry_func_start_step_temp"
        )
        self.assertEqual(dummy_step.step_type, StepType.DEFAULT_STEP)

        # Flow config update is scheduled to reset start to the function step
        self.assertIn(FlowConfig, main_updated)
        reset_flow = main_updated[FlowConfig][flow_config_id]
        self.assertEqual(reset_flow.start_step, "entry_func")

        # Dummy step is scheduled for post-push deletion
        self.assertIn(FlowStep, post_deleted)
        self.assertIn("New Flow_entry_func_start_step_temp", post_deleted[FlowStep])

    def test_clean_resources_before_push_orphaned_variable_delete_and_recreate(self):
        """When all functions referencing a variable are deleted, variable is delete+recreated."""
        var_id = "VAR-orphan"
        variable = Variable(resource_id=var_id, name="orphan_var")
        fn_a = Function(
            resource_id="FUNCTIONS-fn-a",
            name="fn_a",
            description="",
            code="def fn_a(conv): conv.state.orphan_var = 1",
            parameters=[],
            latency_control={},
            flow_id=None,
            flow_name=None,
            function_type=FunctionType.GLOBAL,
            variable_references={var_id: True},
        )

        self.project.resources.setdefault(Variable, {})[var_id] = variable
        self.project.resources.setdefault(Function, {})["FUNCTIONS-fn-a"] = fn_a

        new_resources = {}
        updated_resources = {}
        deleted_resources = {Function: {"FUNCTIONS-fn-a": fn_a}}

        push_changes = self.project._clean_resources_before_push(
            {Variable: {var_id: variable}},
            new_resources,
            updated_resources,
            deleted_resources,
        )
        cleaned_new = push_changes.main.new
        cleaned_deleted = push_changes.main.deleted

        self.assertIn(var_id, cleaned_deleted.get(Variable, {}))
        self.assertIn(var_id, cleaned_new.get(Variable, {}))

    def test_clean_resources_before_push_handoff_updates_variable_refs(
        self,
    ):
        """When refs are handed off (A removes, B adds), update variable refs; fn_a stays in main batch."""
        var_id = "VAR-handoff"
        variable = Variable(resource_id=var_id, name="handoff_var")
        fn_a = Function(
            resource_id="FUNCTIONS-fn-a",
            name="fn_a",
            description="",
            code="def fn_a(conv): conv.state.handoff_var = 1",
            parameters=[],
            latency_control={},
            flow_id=None,
            flow_name=None,
            function_type=FunctionType.GLOBAL,
            variable_references={var_id: True},
        )
        fn_b = Function(
            resource_id="FUNCTIONS-fn-b",
            name="fn_b",
            description="",
            code="def fn_b(conv): conv.state.handoff_var = 2",
            parameters=[],
            latency_control={},
            flow_id=None,
            flow_name=None,
            function_type=FunctionType.GLOBAL,
            variable_references={var_id: True},
        )

        self.project.resources.setdefault(Variable, {})[var_id] = variable
        self.project.resources.setdefault(Function, {})["FUNCTIONS-fn-a"] = fn_a

        fn_a_updated = Function(
            resource_id="FUNCTIONS-fn-a",
            name="fn_a",
            description="",
            code="def fn_a(conv): pass",
            parameters=[],
            latency_control={},
            flow_id=None,
            flow_name=None,
            function_type=FunctionType.GLOBAL,
            variable_references={},
        )

        new_resources = {Function: {"FUNCTIONS-fn-b": fn_b}}
        updated_resources = {Function: {"FUNCTIONS-fn-a": fn_a_updated}}
        deleted_resources = {}

        push_changes = self.project._clean_resources_before_push(
            {
                Variable: {var_id: variable},
                Function: {"FUNCTIONS-fn-a": fn_a_updated, "FUNCTIONS-fn-b": fn_b},
            },
            new_resources,
            updated_resources,
            deleted_resources,
        )
        cleaned_updated = push_changes.main.updated
        post_push_updated = push_changes.post.updated

        self.assertIn("FUNCTIONS-fn-a", cleaned_updated.get(Function, {}))
        self.assertIn(var_id, cleaned_updated.get(Variable, {}))
        self.assertEqual(
            cleaned_updated[Variable][var_id].references,
            {"functions": {"FUNCTIONS-fn-b": True}},
        )
        # Variable updates run first (PRIORITY_UPDATE_TYPES), so no need to defer fn_a
        self.assertNotIn(Function, post_push_updated)

    def test_clean_resources_before_push_variable_already_deleted_skipped(self):
        """Variable already in deleted_resources is skipped (no delete+recreate)."""
        var_id = "VAR-skip"
        variable = Variable(resource_id=var_id, name="skip_var")
        fn_a = Function(
            resource_id="FUNCTIONS-fn-a",
            name="fn_a",
            description="",
            code="def fn_a(conv): conv.state.skip_var = 1",
            parameters=[],
            latency_control={},
            flow_id=None,
            flow_name=None,
            function_type=FunctionType.GLOBAL,
            variable_references={var_id: True},
        )

        self.project.resources.setdefault(Variable, {})[var_id] = variable
        self.project.resources.setdefault(Function, {})["FUNCTIONS-fn-a"] = fn_a

        new_resources = {}
        updated_resources = {}
        deleted_resources = {
            Function: {"FUNCTIONS-fn-a": fn_a},
            Variable: {var_id: variable},
        }

        push_changes = self.project._clean_resources_before_push(
            {},
            new_resources,
            updated_resources,
            deleted_resources,
        )
        cleaned_new = push_changes.main.new
        cleaned_deleted = push_changes.main.deleted

        self.assertIn(var_id, cleaned_deleted.get(Variable, {}))
        self.assertNotIn(var_id, cleaned_new.get(Variable, {}))

    def test_clean_resources_before_push_variable_with_surviving_ref_not_orphaned(self):
        """Variable with at least one non-deleted ref is not delete+recreated."""
        var_id = "VAR-survive"
        variable = Variable(resource_id=var_id, name="survive_var")
        fn_a = Function(
            resource_id="FUNCTIONS-fn-a",
            name="fn_a",
            description="",
            code="def fn_a(conv): conv.state.survive_var = 1",
            parameters=[],
            latency_control={},
            flow_id=None,
            flow_name=None,
            function_type=FunctionType.GLOBAL,
            variable_references={var_id: True},
        )
        fn_b = Function(
            resource_id="FUNCTIONS-fn-b",
            name="fn_b",
            description="",
            code="def fn_b(conv): conv.state.survive_var = 2",
            parameters=[],
            latency_control={},
            flow_id=None,
            flow_name=None,
            function_type=FunctionType.GLOBAL,
            variable_references={var_id: True},
        )

        self.project.resources.setdefault(Variable, {})[var_id] = variable
        self.project.resources.setdefault(Function, {})["FUNCTIONS-fn-a"] = fn_a
        self.project.resources.setdefault(Function, {})["FUNCTIONS-fn-b"] = fn_b

        new_resources = {}
        updated_resources = {}
        deleted_resources = {Function: {"FUNCTIONS-fn-a": fn_a}}

        push_changes = self.project._clean_resources_before_push(
            {
                Variable: {var_id: variable},
                Function: {"FUNCTIONS-fn-b": fn_b},
            },
            new_resources,
            updated_resources,
            deleted_resources,
        )
        cleaned_new = push_changes.main.new
        cleaned_deleted = push_changes.main.deleted

        self.assertNotIn(var_id, cleaned_deleted.get(Variable, {}))
        self.assertNotIn(var_id, cleaned_new.get(Variable, {}))


class PushProjectTest(unittest.TestCase):
    """Tests for the push_project method"""

    def setUp(self):
        """Set up common mocks for push_project tests"""
        self.mock_pull = patch.object(AgentStudioProject, "pull_project").start()
        self.mock_api_handler = patch.object(
            AgentStudioProject, "api_handler", new_callable=MagicMock
        ).start()
        self.mock_save_config = patch.object(AgentStudioProject, "save_config").start()
        self.mock_pull.return_value = []
        self.mock_api_handler.push_resources = MagicMock(return_value=True)
        self.mock_load_project = patch.object(AgentStudioProject, "load_project").start()

    def tearDown(self):
        """Clean up patches"""
        patch.stopall()

    def test_push_project_no_changes(self):
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

        success, message, _ = project.push_project(force=True)

        self.assertFalse(success)
        self.assertEqual(message, "No changes detected")
        self.mock_api_handler.push_resources.assert_not_called()

    def test_push_project_merge_conflict(self):
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        self.mock_pull.return_value = ["functions/test_function.py"]

        success, message, _ = project.push_project(force=False)

        self.assertFalse(success)
        self.assertIn("Merge conflicts detected", message)
        self.assertIn("test_function.py", message)

    def test_push_project_new_resources(self):
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["topics"].pop("TOPIC-Topic 1")
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, _ = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.push_resources.assert_called_once()
        call_args = self.mock_api_handler.push_resources.call_args
        new_resources = call_args.kwargs["new_resources"]
        self.assertIn(Topic, new_resources)
        # New resources get random IDs, so check by name
        topic_names = [r.name for r in new_resources[Topic].values()]
        self.assertIn("Topic 1", topic_names)

    def test_push_project_new_resource_flow(self):
        project_data = deepcopy(PROJECT_DATA)
        # Remove a flow so it appears as new
        project_data["resources"]["flow_config"].pop("FLOW_CONFIG-test_flow")
        number_steps = 0
        for step_id, step in list(project_data["resources"]["flow_steps"].items()):
            if step.get("flow_id") == "test_flow":
                project_data["resources"]["flow_steps"].pop(step_id)
                number_steps += 1
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, _ = project.push_project(force=True, skip_validation=True)

        self.assertTrue(success, f"Push failed: {message}")
        self.mock_api_handler.push_resources.assert_called_once()
        call_args = self.mock_api_handler.push_resources.call_args
        new_resources = call_args.kwargs["new_resources"]
        self.assertIn(FlowConfig, new_resources)
        # New resources get random IDs, so check by name
        flow_configs = list(new_resources[FlowConfig].values())
        test_flow = next((f for f in flow_configs if f.name == "test_flow"), None)
        self.assertIsNotNone(test_flow)
        self.assertIsNotNone(test_flow.steps)
        self.assertEqual(len(test_flow.steps), number_steps)

    def test_push_project_deleted_resource(self):
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["functions"]["FUNCTION-extra_function"] = {
            "resource_id": "FUNCTION-extra_function",
            "name": "extra_function",
            "description": "An extra test function for global use.",
            "code": 'def extra_function(conv: Conversation):\n    """A test function for global use."""\n    return "Hello from global function"\n',
            "parameters": [],
            "latency_control": {},
            "flow_id": None,
            "flow_name": None,
            "function_type": "global",
        }
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, _ = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.push_resources.assert_called_once()
        call_args = self.mock_api_handler.push_resources.call_args
        deleted_resources = call_args.kwargs["deleted_resources"]
        self.assertIn(Function, deleted_resources)
        self.assertIn("FUNCTION-extra_function", deleted_resources[Function])

    def test_push_project_force_does_not_delete_remote_only_resources(self):
        """push --force with load_project: variant_attributes exist remotely but not locally.
        Must NOT push them as deleted (fix for spurious deletions of new resource types).
        """
        # Load project without variant_attributes; remove Topic 1 so we have a new topic to push
        project_data = deepcopy(PROJECT_DATA)
        del project_data["resources"]["variant_attributes"]
        project_data["resources"]["topics"].pop("TOPIC-Topic 1")
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        # Mock load_project: API returns full resources including variant_attributes,
        # but omit Topic 1 so we have a "new" topic to push (otherwise "No changes detected")
        full_project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        full_project.resources[Topic].pop("TOPIC-Topic 1", None)
        full_project.file_structure_info = AgentStudioProject.compute_file_structure_info(
            full_project.resources
        )

        def load_project_side_effect(*args, **kwargs):
            project_self = args[0] if args else project
            project_self.resources = full_project.resources
            project_self.file_structure_info = AgentStudioProject.compute_file_structure_info(
                full_project.resources
            )

        self.mock_load_project.side_effect = load_project_side_effect

        # Mock discover_local_resources: return empty for VariantAttribute (no local file)
        # so variant_attributes would be "deleted" without our fix
        real_discover = AgentStudioProject.discover_local_resources

        def mock_discover(self):
            result = real_discover(self)
            result[VariantAttribute] = []
            return result

        with patch.object(AgentStudioProject, "discover_local_resources", mock_discover):
            success, message, _ = project.push_project(force=True, skip_validation=True)

        self.assertTrue(success, f"Push failed: {message}")
        self.mock_api_handler.push_resources.assert_called_once()
        call_args = self.mock_api_handler.push_resources.call_args
        deleted_resources = call_args.kwargs["deleted_resources"]
        # Must NOT include VariantAttribute - we never had them locally
        self.assertNotIn(VariantAttribute, deleted_resources)

    def test_push_project_modified_resource(self):
        project_data = deepcopy(PROJECT_DATA)
        # Modify a function so it seems there's a modified one
        project_data["resources"]["functions"]["FUNCTION-test_function"]["code"] = (
            'def test_function(conv: Conversation):\n    """A modified test function."""\n    return "Modified return value"\n'
        )
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, _ = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.push_resources.assert_called_once()
        call_args = self.mock_api_handler.push_resources.call_args
        updated_resources = call_args.kwargs["updated_resources"]
        self.assertIn(Function, updated_resources)
        self.assertIn("FUNCTION-test_function", updated_resources[Function])

    def test_push_project_modified_sub_resources_dtmf(self):
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["flow_steps"]["test_flow_start_step"]["dtmf_config"][
            "is_enabled"
        ] = True
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, _ = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.push_resources.assert_called_once()
        call_args = self.mock_api_handler.push_resources.call_args
        updated_resources = call_args.kwargs["updated_resources"]
        self.assertIn(DTMFConfig, updated_resources)

    def test_push_project_new_sub_resources_condition(self):
        project_data = deepcopy(PROJECT_DATA)
        # Delete condition in project_data to mimic new condition locally
        project_data["resources"]["flow_steps"]["test_flow_collect_name"]["conditions"] = []

        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, _ = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.push_resources.assert_called_once()
        call_args = self.mock_api_handler.push_resources.call_args
        new_resources = call_args.kwargs["new_resources"]
        self.assertIn(Condition, new_resources)
        # Deleted 2 conditions, so check that 2 new conditions are pushed
        self.assertEqual(len(new_resources[Condition]), 2)

    def test_push_project_deleted_sub_resource_condition(self):
        project_data = deepcopy(PROJECT_DATA)
        # Mimic deleting a condition locally by adding to project data
        project_data["resources"]["flow_steps"]["test_flow_collect_name"]["conditions"].append(
            {
                "name": "delete_condition",
                "description": "A condition to be deleted",
                "required_entities": [],
                "condition_type": "step_condition",
                "child_step": "confirm_details",
                "step_id": "collect_name",
                "flow_id": "FLOW_CONFIG-test_flow",
                "resource_id": "CONDITION-to_delete",
                "position": None,
                "exit_flow_position": None,
                "ingress": "top",
            },
        )

        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, _ = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.push_resources.assert_called_once()
        call_args = self.mock_api_handler.push_resources.call_args
        deleted_resources = call_args.kwargs["deleted_resources"]
        self.assertIn(Condition, deleted_resources)

    def test_push_project_updated_sub_resource_asr_biasing(self):
        """Test pushing an updated ASRBiasing sub-resource"""
        project_data = deepcopy(PROJECT_DATA)
        # Modify ASR biasing in project_data
        project_data["resources"]["flow_steps"]["test_flow_start_step"]["asr_biasing"][
            "custom_keywords"
        ] = ["NewKeyword1", "NewKeyword2"]

        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, _ = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.push_resources.assert_called_once()
        call_args = self.mock_api_handler.push_resources.call_args
        updated_resources = call_args.kwargs["updated_resources"]
        self.assertIn(ASRBiasing, updated_resources)

    def test_push_project_mixed_changes(self):
        project_data = deepcopy(PROJECT_DATA)
        # New resource
        project_data["resources"]["topics"].pop("TOPIC-Topic 1")
        # Deleted resource
        project_data["resources"]["functions"]["FUNCTION-extra_function"] = {
            "resource_id": "FUNCTION-extra_function",
            "name": "extra_function",
            "description": "An extra test function for global use.",
            "code": 'def extra_function(conv: Conversation):\n    """A test function for global use."""\n    return "Hello from global function"\n',
            "parameters": [],
            "latency_control": {},
            "flow_id": None,
            "flow_name": None,
            "function_type": "global",
        }
        # Modified resource in subresource
        project_data["resources"]["flow_steps"]["test_flow_start_step"]["asr_biasing"][
            "is_enabled"
        ] = False
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, _ = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.push_resources.assert_called_once()
        call_args = self.mock_api_handler.push_resources.call_args
        new_resources = call_args.kwargs["new_resources"]
        updated_resources = call_args.kwargs["updated_resources"]
        deleted_resources = call_args.kwargs["deleted_resources"]
        self.assertIn(Topic, new_resources)
        self.assertIn(ASRBiasing, updated_resources)
        self.assertIn(FlowStep, updated_resources)
        self.assertIn(Function, deleted_resources)

    def test_push_project_new_keyphrase_boosting(self):
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["keyphrase_boosting"].pop("KEYPHRASE_BOOSTING-polyai")
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, _ = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.push_resources.assert_called_once()
        call_args = self.mock_api_handler.push_resources.call_args
        new_resources = call_args.kwargs["new_resources"]
        self.assertIn(KeyphraseBoosting, new_resources)
        kp_names = [r.keyphrase for r in new_resources[KeyphraseBoosting].values()]
        self.assertIn("PolyAI", kp_names)

    def test_push_project_deleted_keyphrase_boosting(self):
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["keyphrase_boosting"]["KEYPHRASE_BOOSTING-extra"] = {
            "resource_id": "KEYPHRASE_BOOSTING-extra",
            "name": "extra-word",
            "keyphrase": "extra-word",
            "level": "boosted",
        }
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, _ = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.push_resources.assert_called_once()
        call_args = self.mock_api_handler.push_resources.call_args
        deleted_resources = call_args.kwargs["deleted_resources"]
        self.assertIn(KeyphraseBoosting, deleted_resources)
        self.assertIn("KEYPHRASE_BOOSTING-extra", deleted_resources[KeyphraseBoosting])

    def test_push_project_modified_keyphrase_boosting(self):
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["keyphrase_boosting"]["KEYPHRASE_BOOSTING-polyai"]["level"] = (
            "default"
        )
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, _ = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.push_resources.assert_called_once()
        call_args = self.mock_api_handler.push_resources.call_args
        updated_resources = call_args.kwargs["updated_resources"]
        self.assertIn(KeyphraseBoosting, updated_resources)
        self.assertIn("KEYPHRASE_BOOSTING-polyai", updated_resources[KeyphraseBoosting])

    def test_push_project_new_transcript_correction(self):
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["transcript_corrections"].pop(
            "TRANSCRIPT_CORRECTIONS-email_domain"
        )
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, _ = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.push_resources.assert_called_once()
        call_args = self.mock_api_handler.push_resources.call_args
        new_resources = call_args.kwargs["new_resources"]
        self.assertIn(TranscriptCorrection, new_resources)
        tc_names = [r.name for r in new_resources[TranscriptCorrection].values()]
        self.assertIn("Email domain fix", tc_names)

    def test_push_project_deleted_transcript_correction(self):
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["transcript_corrections"]["TRANSCRIPT_CORRECTIONS-extra"] = {
            "resource_id": "TRANSCRIPT_CORRECTIONS-extra",
            "name": "Extra correction",
            "description": "Extra",
            "regular_expressions": [
                {"regular_expression": "foo", "replacement": "bar", "replacement_type": "full"},
            ],
        }
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, _ = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.push_resources.assert_called_once()
        call_args = self.mock_api_handler.push_resources.call_args
        deleted_resources = call_args.kwargs["deleted_resources"]
        self.assertIn(TranscriptCorrection, deleted_resources)
        self.assertIn("TRANSCRIPT_CORRECTIONS-extra", deleted_resources[TranscriptCorrection])

    def test_push_project_modified_asr_settings(self):
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["asr_settings"]["asr_settings"]["barge_in"] = True
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, _ = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.push_resources.assert_called_once()
        call_args = self.mock_api_handler.push_resources.call_args
        updated_resources = call_args.kwargs["updated_resources"]
        self.assertIn(AsrSettings, updated_resources)
        self.assertIn("asr_settings", updated_resources[AsrSettings])

    def test_push_project_validation_error(self):
        project_data = deepcopy(PROJECT_DATA)
        # Create invalid resource (empty description)
        project_data["resources"]["flow_config"]["FLOW_CONFIG-test_flow"]["description"] = (
            "description"
        )
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        # Modify the local file to match
        flow_config_path = os.path.join(TEST_DIR, "flows", "test_flow", "flow_config.yaml")
        invalid_content = "name: test_flow\ndescription:\nstart_step: start_step\n"

        with mock_read_from_file({flow_config_path: invalid_content}):
            success, message, _ = project.push_project(force=True, skip_validation=False)

        self.assertFalse(success)
        self.assertIn("Validation errors", message)

    def test_push_project_validation_error_skip(self):
        project_data = deepcopy(PROJECT_DATA)
        # Create invalid resource (empty description)
        project_data["resources"]["flow_config"]["FLOW_CONFIG-test_flow"]["description"] = (
            "description"
        )
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        # Modify the local file to match
        flow_config_path = os.path.join(TEST_DIR, "flows", "test_flow", "flow_config.yaml")
        invalid_content = "name: test_flow\ndescription:\nstart_step: start_step\n"

        with mock_read_from_file({flow_config_path: invalid_content}):
            success, message, _ = project.push_project(force=True, skip_validation=True)

        self.assertTrue(success)

    def test_push_project_dry_run(self):
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["topics"].pop("TOPIC-Topic 1")
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, _ = project.push_project(force=True, dry_run=True)

        self.assertTrue(success)
        self.assertIn("Dry run completed", message)
        self.mock_api_handler.push_resources.assert_called_once_with(
            new_resources=mock.ANY,
            deleted_resources=mock.ANY,
            updated_resources=mock.ANY,
            dry_run=True,
            email=None,
            queue_pushes=mock.ANY,
        )


class ValidateProjectTest(unittest.TestCase):
    """Tests for the validate_project method"""

    def test_validate_project_valid(self):
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        errors = project.validate_project()
        self.assertEqual(len(errors), 0, f"Errors: {errors}")

    def test_validate_project_invalid(self):
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        with mock_read_from_file(
            {
                os.path.join(
                    TEST_DIR, "flows", "test_flow", "flow_config.yaml"
                ): "name: test_flow\ndescription: \nstart_step: start_step\n"
            }
        ):
            errors = project.validate_project()
        self.assertEqual(len(errors), 1)
        self.assertIn("Description cannot be empty.", errors[0])

    def test_validate_project_invalid_multiple(self):
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        with mock_read_from_file(
            {
                os.path.join(
                    TEST_DIR, "topics", "Topic 1.yaml"
                ): 'name: Topic 1\ncontent: Topic 1 content\nexample_queries:\n- Topic 1 example query\nenabled: true\nactions: "{{fn:FUNCTION-missing_function}}"\n',
                os.path.join(
                    TEST_DIR, "flows", "test_flow", "flow_config.yaml"
                ): "name: test_flow\ndescription: \nstart_step: missing_step\n",
            }
        ):
            errors = project.validate_project()
        self.assertEqual(len(errors), 2)
        self.assertIn(
            "Invalid references: ['global_functions: FUNCTION-missing_function']", errors[0]
        )
        self.assertIn("Start step 'missing_step' not found.", errors[1])


class PullProjectTest(unittest.TestCase):
    """Tests for the pull_project method"""

    def setUp(self):
        """Set up common mocks for pull_project tests"""
        self.mock_api_handler = patch.object(
            AgentStudioProject, "api_handler", new_callable=MagicMock
        ).start()
        self.mock_save_config = patch.object(AgentStudioProject, "save_config").start()
        self.mock_save_imports = patch("poly.utils.save_imports").start()
        self.mock_export_decorators = patch("poly.utils.export_decorators").start()
        # Mock resource.save() calls - patch at instance level since save is called on instances
        self.patched_save = patch.object(Resource, "save")
        self.mock_resource_save = self.patched_save.start()
        # Mock file write operations to prevent test files from being modified
        self.mock_save_to_file = patch.object(Resource, "save_to_file").start()
        # Mock os.remove() to prevent test files from being deleted
        self.mock_os_remove = patch("os.remove").start()

    def tearDown(self):
        """Clean up patches"""
        patch.stopall()

    def test_pull_project_no_changes(self):
        """Test pulling when incoming resources match local resources"""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        # Incoming resources are the same as project.resources
        # Use the actual resources from the project to ensure they match
        original_resources = deepcopy(project.resources)
        self.mock_api_handler.pull_resources.return_value = original_resources

        files_with_conflicts = project.pull_project(force=False)
        self.assertEqual(files_with_conflicts, [])
        self.assertEqual(project.resources, original_resources)

    def test_pull_project_not_loaded_resources_force_save(self):
        """When a resource type was not in the loaded dict, pull incorporates the incoming
        resources via the file-level merge without reporting conflicts.  Prevents spurious
        deletions when new types like variant_attributes are added remotely but weren't in
        the local project dict when it was loaded.
        """
        # Load project with variant_attributes removed from dict (simulates old project)
        project_data = deepcopy(PROJECT_DATA)
        del project_data["resources"]["variant_attributes"]
        del project_data["resources"]["variants"]

        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        # Check _not_loaded_resources is set correctly (resource type was not in dict)
        self.assertIn(VariantAttribute, project._not_loaded_resources)
        # VariantAttribute is in resources but empty (no instances loaded from dict)
        self.assertEqual(project.resources.get(VariantAttribute, {}), {})

        # Simulate pull: incoming has variant_attributes from remote
        full_project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        incoming_resources = full_project.resources
        self.mock_api_handler.pull_resources.return_value = incoming_resources

        with mock_read_from_file(
            {os.path.join(TEST_DIR, "config", "variant_attributes.yaml"): "{}\n"}
        ):
            files_with_conflicts = project.pull_project(force=False)

        self.assertEqual(files_with_conflicts, [])
        # Variant attributes are now present in project resources with the correct keys
        self.assertIn(VariantAttribute, project.resources)
        self.assertEqual(
            set(project.resources[VariantAttribute].keys()),
            set(incoming_resources[VariantAttribute].keys()),
        )
        # The resource type is removed from _not_loaded_resources once it has been processed
        self.assertNotIn(VariantAttribute, project._not_loaded_resources)

    def test_pull_project_addition(self):
        """Test pulling when a new resource is added remotely"""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        # Add a new topic to incoming resources
        incoming_resources = deepcopy(project.resources)
        new_topic = Topic(
            resource_id="TOPIC-new_topic",
            name="new_topic",
            actions="Use {{fn:test_function}}",
            content="New topic content",
            example_queries=["New query"],
        )
        incoming_resources.setdefault(Topic, {})["TOPIC-new_topic"] = new_topic
        self.mock_api_handler.pull_resources.return_value = incoming_resources

        files_with_conflicts = project.pull_project(force=False)
        self.assertEqual(files_with_conflicts, [])
        # Verify the new resource was saved via save_to_file or save
        self.assertTrue(self.mock_save_to_file.called or self.mock_resource_save.called)
        # Verify new resource is now in project resources
        self.assertIn("TOPIC-new_topic", project.resources.get(Topic, {}))

    def test_pull_project_deletion(self):
        """Test pulling when a resource is deleted remotely"""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        # Remove a topic from incoming resources
        incoming_resources = deepcopy(project.resources)
        if Topic in incoming_resources and "TOPIC-Topic 1" in incoming_resources[Topic]:
            del incoming_resources[Topic]["TOPIC-Topic 1"]
        self.mock_api_handler.pull_resources.return_value = incoming_resources

        files_with_conflicts = project.pull_project(force=False)

        self.assertEqual(files_with_conflicts, [])
        # Verify the resource file was removed via os.remove
        self.mock_os_remove.assert_called()
        # Verify resource is no longer in project resources
        self.assertNotIn("TOPIC-Topic 1", project.resources.get(Topic, {}))

    def test_pull_project_modify_1(self):
        """Test pulling when a resource is modified remotely"""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        # Modify a function in incoming resources
        incoming_resources = deepcopy(project.resources)
        func_id = "FUNCTION-test_function"
        modified_func = deepcopy(incoming_resources[Function][func_id])
        modified_func.code = 'def test_function(conv: Conversation):\n    """Modified remotely."""\n    return "Modified"\n'
        incoming_resources[Function][func_id] = modified_func
        self.mock_api_handler.pull_resources.return_value = incoming_resources

        files_with_conflicts = project.pull_project(force=False)
        self.assertEqual(files_with_conflicts, [])
        # Verify resource is updated in project resources
        self.assertIn(func_id, project.resources.get(Function, {}))
        self.assertEqual(project.resources[Function][func_id].code, modified_func.code)

    def test_pull_project_modify_conflict(self):
        """Test pulling when a resource is modified both locally and remotely with conflicts"""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        original_resources = deepcopy(project.resources)

        # Also change incoming resource
        incoming_resources = deepcopy(original_resources)
        incoming_resources[Function][
            "FUNCTION-test_function"
        ].code = 'def test_function(conv: Conversation):\n    """Modified remotely."""\n    return "Remote change"\n'
        self.mock_api_handler.pull_resources.return_value = incoming_resources

        with mock_read_from_file(
            {
                os.path.join(
                    TEST_DIR, "functions", "test_function.py"
                ): 'from _gen import *  # <AUTO GENERATED>\n\n@func_description(\'A test function for global use.\')\ndef test_function(conv: Conversation):\n    """Modified locally."""\n    return "Local change"\n'
            }
        ):
            files_with_conflicts = project.pull_project(force=False)
        # Should detect merge conflict
        self.assertEqual(
            files_with_conflicts, [os.path.join(TEST_DIR, "functions", "test_function.py")]
        )
        # Resources are now incoming resources
        self.assertEqual(project.resources, incoming_resources)

        # Find the specific call for test_function.py
        test_func_path = os.path.join(TEST_DIR, "functions", "test_function.py")
        test_func_calls = [
            call
            for call in self.mock_save_to_file.call_args_list
            if len(call[0]) >= 2 and call[0][1] == test_func_path
        ]
        # Check that the saved content contains merge conflict
        saved_content = test_func_calls[0][0][0] if test_func_calls else ""
        merged_content = 'from _gen import *  # <AUTO GENERATED>\n\n@func_description(\'A test function for global use.\')\ndef test_function(conv: Conversation):\n<<<<<<<\n    """Modified locally."""\n    return "Local change"\n=======\n    """Modified remotely."""\n    return "Remote change"\n>>>>>>>\n'
        self.assertEqual(saved_content, merged_content)

    def test_pull_project_modify_flow_config_conflict(self):
        """Test pulling when a flow config is modified both locally and remotely with conflicts"""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        original_resources = deepcopy(project.resources)

        # Modify incoming flow config
        incoming_resources = deepcopy(original_resources)
        flow_config_id = "FLOW_CONFIG-test_flow"
        modified_flow_config = deepcopy(incoming_resources[FlowConfig][flow_config_id])
        modified_flow_config.description = "Modified remotely - new description"
        incoming_resources[FlowConfig][flow_config_id] = modified_flow_config
        self.mock_api_handler.pull_resources.return_value = incoming_resources

        # Mock local file with different changes
        flow_config_path = os.path.join(TEST_DIR, "flows", "test_flow", "flow_config.yaml")
        with mock_read_from_file(
            {
                flow_config_path: "name: test_flow\ndescription: Modified locally - different description\nstart_step: start_step\n"
            }
        ):
            files_with_conflicts = project.pull_project(force=False)
        # Should detect merge conflict
        self.assertEqual(files_with_conflicts, [flow_config_path])
        # Resources are now incoming resources
        self.assertEqual(project.resources, incoming_resources)

        # Find the specific call for flow_config.yaml
        flow_config_calls = [
            call
            for call in self.mock_save_to_file.call_args_list
            if len(call[0]) >= 2 and call[0][1] == flow_config_path
        ]
        # Check that the saved content contains merge conflict
        self.assertGreater(
            len(flow_config_calls), 0, "save_to_file should be called for flow_config.yaml"
        )
        saved_content = flow_config_calls[0][0][0] if flow_config_calls else ""
        # Verify merge conflict markers are present
        self.assertIn("<<<<<<<", saved_content)
        self.assertIn("=======", saved_content)
        self.assertIn(">>>>>>>", saved_content)
        # Verify both versions are in the conflict
        self.assertIn("Modified locally", saved_content)
        self.assertIn("Modified remotely", saved_content)

    def test_pull_project_modify_no_conflict(self):
        """Test pulling when a resource is modified both locally and remotely without conflicts"""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        original_resources = deepcopy(project.resources)

        # Also change incoming resource
        incoming_resources = deepcopy(original_resources)
        incoming_resources[Function][
            "FUNCTION-test_function"
        ].code = 'def test_function(conv: Conversation):\n    """Modified remotely."""\n    return "Remote change"\n'
        self.mock_api_handler.pull_resources.return_value = incoming_resources

        with mock_read_from_file(
            {
                os.path.join(
                    TEST_DIR, "functions", "test_function.py"
                ): 'from _gen import *  # <AUTO GENERATED>\n\ndef added_extra_function():\n    pass\n\n@func_description(\'A test function for global use.\')\ndef test_function(conv: Conversation):\n    """A test function for global use."""\n    return "Hello from global function"\n'
            }
        ):
            files_with_conflicts = project.pull_project(force=False)
        # Should detect no merge conflict
        self.assertEqual(files_with_conflicts, [])
        # Resources are now incoming resources
        self.assertEqual(project.resources, incoming_resources)

        # Find the specific call for test_function.py
        test_func_path = os.path.join(TEST_DIR, "functions", "test_function.py")
        test_func_calls = [
            call
            for call in self.mock_save_to_file.call_args_list
            if len(call[0]) >= 2 and call[0][1] == test_func_path
        ]
        # Check that the saved content contains merged version
        saved_content = test_func_calls[0][0][0] if test_func_calls else ""
        merged_content = 'from _gen import *  # <AUTO GENERATED>\n\ndef added_extra_function():\n    pass\n\n@func_description(\'A test function for global use.\')\ndef test_function(conv: Conversation):\n    """Modified remotely."""\n    return "Remote change"\n'
        self.assertEqual(saved_content, merged_content)

    def test_pull_project_force(self):
        """Test pulling with force=True to overwrite local changes"""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        original_resources = deepcopy(project.resources)

        # Also change incoming resource
        incoming_resources = deepcopy(original_resources)
        incoming_resources[Function][
            "FUNCTION-test_function"
        ].code = 'def test_function(conv: Conversation):\n    """Modified remotely."""\n    return "Remote change"\n'
        self.mock_api_handler.pull_resources.return_value = incoming_resources

        with mock_read_from_file(
            {
                os.path.join(
                    TEST_DIR, "functions", "test_function.py"
                ): 'from _gen import *  # <AUTO GENERATED>\n\n@func_description(\'A test function for global use.\')\ndef test_function(conv: Conversation):\n    """Modified locally."""\n    return "Local change"\n'
            }
        ):
            files_with_conflicts = project.pull_project(force=True)

        # Should detect no merge conflict
        self.assertEqual(files_with_conflicts, [])
        # Resources are now incoming resources
        self.assertEqual(project.resources, incoming_resources)

    def test_pull_project_added_locally_and_remote_same(self):
        """Test pulling when a resource was added locally and exists remotely"""
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["functions"].pop("FUNCTION-test_function_with_parameters")
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        full_project_resources = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR).resources
        incoming_resources = deepcopy(full_project_resources)

        self.mock_api_handler.pull_resources.return_value = incoming_resources
        files_with_conflicts = project.pull_project(force=False, format=True)
        self.assertEqual(files_with_conflicts, [])
        # Verify resource is updated in project resources
        self.assertIn("FUNCTION-test_function_with_parameters", project.resources.get(Function, {}))

        # Verify it wasn't saved to the file system
        test_func_path = os.path.join(TEST_DIR, "functions", "test_function_with_parameters.py")
        test_func_calls = [
            call
            for call in self.mock_save_to_file.call_args_list
            if len(call[0]) >= 2 and call[0][1] == test_func_path
        ]
        self.assertEqual(test_func_calls, [])

    def test_pull_project_added_locally_and_remote_different(self):
        """Test pulling when a resource was added locally and exists remotely"""
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["functions"].pop("FUNCTION-test_function_with_parameters")
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        full_project_resources = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR).resources
        incoming_resources = deepcopy(full_project_resources)
        incoming_resources[Function][
            "FUNCTION-test_function_with_parameters"
        ].code = 'def test_function_with_parameters(conv: Conversation):\n    """Test function with parameters."""\n    return "Test function with parameters"\n'

        self.mock_api_handler.pull_resources.return_value = incoming_resources
        files_with_conflicts = project.pull_project(force=False)
        self.assertEqual(len(files_with_conflicts), 1)

    def test_pull_project_deleted_locally(self):
        """Test pulling when a resource was deleted locally and exists remotely"""
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["topics"]["TOPIC-new-topic"] = {
            "resource_id": "TOPIC-new-topic",
            "name": "new-topic",
            "actions": "Use {{fn:test_function}}",
            "content": "New topic content",
            "example_queries": ["New query"],
            "enabled": True,
        }
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        incoming_resources = deepcopy(project.resources)

        self.mock_api_handler.pull_resources.return_value = incoming_resources
        files_with_conflicts = project.pull_project(force=False)
        self.assertEqual(files_with_conflicts, [])

        # Verify it wasn't saved to the file system
        test_topic_path = os.path.join(TEST_DIR, "topics", "new-topic.yaml")
        test_topic_calls = [
            call
            for call in self.mock_save_to_file.call_args_list
            if len(call[0]) >= 2 and call[0][1] == test_topic_path
        ]
        self.assertEqual(test_topic_calls, [])

    def test_pull_project_resource_moved(self):
        """Test pulling when a resource's file path has changed (e.g., renamed)"""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        original_resources = deepcopy(project.resources)
        topic_id = "TOPIC-Topic 1"
        renamed_topic = original_resources[Topic][topic_id]
        # Store original path before renaming
        original_path = renamed_topic.get_path(TEST_DIR)
        # Clear cached property so it recalculates with new name
        if hasattr(renamed_topic, "__dict__"):
            renamed_topic.__dict__.pop("file_path", None)

        # Rename the topic (this changes the file path)
        renamed_topic.name = "renamed_topic"

        self.mock_api_handler.pull_resources.return_value = original_resources

        files_with_conflicts = project.pull_project(force=False)

        self.assertEqual(files_with_conflicts, [])
        # Verify old file would be removed
        self.mock_os_remove.assert_called()
        # Verify it was called with the original path
        remove_calls = [call[0][0] for call in self.mock_os_remove.call_args_list]
        self.assertIn(original_path, remove_calls, "os.remove should be called with original path")
        # Resource should be updated in project
        self.assertEqual(project.resources[Topic][topic_id].name, "renamed_topic")

    def test_pull_project_empty_flow_folder_deletion(self):
        """Test that empty flow folders are deleted after pull"""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

        # Mock os.listdir and os.rmdir to verify empty folder deletion
        empty_flow_path = os.path.join(TEST_DIR, "flows", "test_flow")
        original_listdir = os.listdir
        original_isdir = os.path.isdir

        # Mock flow is now empty
        def mock_listdir(path):
            if path == empty_flow_path:
                return []  # Empty folder
            return original_listdir(path)

        def mock_isdir(path):
            if path == empty_flow_path:
                return True
            return original_isdir(path)

        with (
            patch("os.listdir", side_effect=mock_listdir),
            patch("os.path.isdir", side_effect=mock_isdir),
            patch("os.rmdir") as mock_rmdir,
        ):
            files_with_conflicts = project.pull_project(force=False)

            # Empty flow folder should be deleted
            # _delete_empty_folders is called after pull_project
            self.assertEqual(files_with_conflicts, [])
            # Verify rmdir was called for the empty folder
            mock_rmdir.assert_called()
            # Check that it was called with the empty flow path
            rmdir_calls = [call[0][0] for call in mock_rmdir.call_args_list]
            self.assertTrue(
                any(empty_flow_path in str(call) for call in rmdir_calls),
                f"Expected rmdir to be called for flow folder containing '{empty_flow_path}'",
            )

    def _make_kp_read_mock(self, original_kp_content, local_kp_content):
        """Return a side_effect for Resource.read_from_file that serves keyphrase_boosting.yaml
        with original_kp_content on the first two calls (pre-loop cache build and main-loop
        cache rebuild) and local_kp_content on the third call (post-loop local-file read).
        All other file paths fall through to the real file on disk.
        """
        kp_path = os.path.join(TEST_DIR, "voice", "speech_recognition", "keyphrase_boosting.yaml")
        kp_call_count = [0]

        def side_effect(path, **kwargs):
            if str(path) == kp_path or kp_path in str(path):
                kp_call_count[0] += 1
                if kp_call_count[0] <= 2:
                    return original_kp_content
                return local_kp_content
            with open(str(path)) as f:
                return f.read()

        return side_effect

    def test_pull_project_multi_resource_yaml_remote_change_no_local_change(self):
        """Remote modifies a MultiResourceYamlResource entry; local has no changes.

        The file-level 3-way merge should detect no local delta and write the
        incoming content without reporting any conflict.
        """
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        incoming_resources = deepcopy(project.resources)
        incoming_resources[KeyphraseBoosting]["KEYPHRASE_BOOSTING-polyai"].level = "boosted"
        self.mock_api_handler.pull_resources.return_value = incoming_resources

        kp_path = os.path.join(TEST_DIR, "voice", "speech_recognition", "keyphrase_boosting.yaml")
        # dump_yaml format produced by MultiResourceYamlResource.save(save_to_cache=True)
        original_kp_content = (
            "keyphrases:\n"
            "- keyphrase: PolyAI\n"
            "  level: maximum\n"
            "- keyphrase: reservation\n"
            "  level: boosted\n"
            "- keyphrase: check-in\n"
            "  level: default\n"
        )

        MultiResourceYamlResource._file_cache.clear()
        with patch(
            "poly.resources.resource.Resource.read_from_file",
            side_effect=self._make_kp_read_mock(original_kp_content, original_kp_content),
        ):
            files_with_conflicts = project.pull_project(force=False)
        MultiResourceYamlResource._file_cache.clear()

        self.assertEqual(files_with_conflicts, [])
        # save_to_file should be called for keyphrase_boosting.yaml with incoming content
        kp_calls = [
            call
            for call in self.mock_save_to_file.call_args_list
            if len(call[0]) >= 2 and kp_path in str(call[0][1])
        ]
        self.assertGreater(
            len(kp_calls), 0, "save_to_file should be called for keyphrase_boosting.yaml"
        )
        saved_content = kp_calls[-1][0][0]
        self.assertIn("level: boosted", saved_content)
        self.assertNotIn("<<<<<<<", saved_content)

    def test_pull_project_multi_resource_yaml_merge_no_conflict(self):
        """Remote modifies one entry in a MultiResourceYamlResource file while local
        modifies a different entry.  The file-level 3-way merge should apply both
        changes without conflicts.
        """
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        incoming_resources = deepcopy(project.resources)
        # Remote: PolyAI level maximum → boosted
        incoming_resources[KeyphraseBoosting]["KEYPHRASE_BOOSTING-polyai"].level = "boosted"
        self.mock_api_handler.pull_resources.return_value = incoming_resources

        kp_path = os.path.join(TEST_DIR, "voice", "speech_recognition", "keyphrase_boosting.yaml")
        original_kp_content = (
            "keyphrases:\n"
            "- keyphrase: PolyAI\n"
            "  level: maximum\n"
            "- keyphrase: reservation\n"
            "  level: boosted\n"
            "- keyphrase: check-in\n"
            "  level: default\n"
        )
        # Local: reservation level boosted → default (independent change)
        local_kp_content = (
            "keyphrases:\n"
            "- keyphrase: PolyAI\n"
            "  level: maximum\n"
            "- keyphrase: reservation\n"
            "  level: default\n"
            "- keyphrase: check-in\n"
            "  level: default\n"
        )

        MultiResourceYamlResource._file_cache.clear()
        with patch(
            "poly.resources.resource.Resource.read_from_file",
            side_effect=self._make_kp_read_mock(original_kp_content, local_kp_content),
        ):
            files_with_conflicts = project.pull_project(force=False)
        MultiResourceYamlResource._file_cache.clear()

        self.assertEqual(files_with_conflicts, [])
        kp_calls = [
            call
            for call in self.mock_save_to_file.call_args_list
            if len(call[0]) >= 2 and kp_path in str(call[0][1])
        ]
        self.assertGreater(
            len(kp_calls), 0, "save_to_file should be called for keyphrase_boosting.yaml"
        )
        saved_content = kp_calls[-1][0][0]
        # Both the remote change (PolyAI boosted) and the local change (reservation default)
        # must appear in the merged file
        self.assertIn("level: boosted", saved_content)
        self.assertIn("level: default", saved_content)
        self.assertNotIn("<<<<<<<", saved_content)

    def test_pull_project_multi_resource_yaml_conflict(self):
        """Remote and local both modify the same entry in a MultiResourceYamlResource file.

        The file-level 3-way merge should detect the conflict and surface it in
        files_with_conflicts with conflict markers written to the file.
        """
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        incoming_resources = deepcopy(project.resources)
        # Remote: PolyAI level maximum → boosted
        incoming_resources[KeyphraseBoosting]["KEYPHRASE_BOOSTING-polyai"].level = "boosted"
        self.mock_api_handler.pull_resources.return_value = incoming_resources

        kp_path = os.path.join(TEST_DIR, "voice", "speech_recognition", "keyphrase_boosting.yaml")
        original_kp_content = (
            "keyphrases:\n"
            "- keyphrase: PolyAI\n"
            "  level: maximum\n"
            "- keyphrase: reservation\n"
            "  level: boosted\n"
            "- keyphrase: check-in\n"
            "  level: default\n"
        )
        # Local: PolyAI level maximum → default (conflicts with remote "boosted")
        local_kp_content = (
            "keyphrases:\n"
            "- keyphrase: PolyAI\n"
            "  level: default\n"
            "- keyphrase: reservation\n"
            "  level: boosted\n"
            "- keyphrase: check-in\n"
            "  level: default\n"
        )

        MultiResourceYamlResource._file_cache.clear()
        with patch(
            "poly.resources.resource.Resource.read_from_file",
            side_effect=self._make_kp_read_mock(original_kp_content, local_kp_content),
        ):
            files_with_conflicts = project.pull_project(force=False)
        MultiResourceYamlResource._file_cache.clear()

        self.assertIn(kp_path, files_with_conflicts)
        kp_calls = [
            call
            for call in self.mock_save_to_file.call_args_list
            if len(call[0]) >= 2 and kp_path in str(call[0][1])
        ]
        self.assertGreater(
            len(kp_calls), 0, "save_to_file should be called for keyphrase_boosting.yaml"
        )
        saved_content = kp_calls[-1][0][0]
        self.assertIn("<<<<<<<", saved_content)
        self.assertIn("=======", saved_content)
        self.assertIn(">>>>>>>", saved_content)

    def test_pull_project_multi_resource_yaml_force(self):
        """With force=True, MultiResourceYamlResource files are written directly from
        the incoming cache without any 3-way merge.
        """
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        incoming_resources = deepcopy(project.resources)
        # Remote: PolyAI level maximum → boosted
        incoming_resources[KeyphraseBoosting]["KEYPHRASE_BOOSTING-polyai"].level = "boosted"
        self.mock_api_handler.pull_resources.return_value = incoming_resources

        kp_path = os.path.join(TEST_DIR, "voice", "speech_recognition", "keyphrase_boosting.yaml")

        MultiResourceYamlResource._file_cache.clear()
        files_with_conflicts = project.pull_project(force=True)
        MultiResourceYamlResource._file_cache.clear()

        self.assertEqual(files_with_conflicts, [])
        # write_cache_to_file() calls save_to_file for the keyphrase file directly
        kp_calls = [
            call
            for call in self.mock_save_to_file.call_args_list
            if len(call[0]) >= 2 and kp_path in str(call[0][1])
        ]
        self.assertGreater(
            len(kp_calls), 0, "save_to_file should be called for keyphrase_boosting.yaml"
        )
        saved_content = kp_calls[-1][0][0]
        self.assertIn("level: boosted", saved_content)
        self.assertNotIn("<<<<<<<", saved_content)


class DocsTest(unittest.TestCase):
    """Tests for the docs module"""

    def test_load_docs(self):
        """Test loading a docs file"""
        AgentStudioProject.load_docs("docs")


if __name__ == "__main__":
    unittest.main()
