"""Tests for the AgentStudioProject class
Uses test project in tests/test_project


Copyright PolyAI Limited
"""

import json
import os
import shutil
import tempfile
import unittest
from copy import deepcopy
from unittest.mock import MagicMock, patch

import poly.resources.resource_utils as resource_utils
from poly.project import AgentStudioProject, DeploymentMode
from poly.resources import (
    AsrSettings,
    ChatGreeting,
    ChatSafetyFilters,
    ChatStylePrompt,
    Document,
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
    TestCase,
    TestCaseAssertion,
    TestCaseTags,
    Topic,
    TranscriptCorrection,
    Translation,
    Variable,
    Variant,
    VariantAttribute,
    VoiceDisclaimerMessage,
    VoiceGreeting,
    VoiceStylePrompt,
)
from poly.resources.flows import (
    ASRBiasing,
    Condition,
    DTMFConfig,
    StepType,
)
from poly.resources.function import FunctionType
from poly.resources.resource import MultiResourceYamlResource
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


class InitProjectOnSaveTest(unittest.TestCase):
    """Tests for the on_save callback in init_project"""

    def setUp(self):
        self.mock_api_handler = patch.object(
            AgentStudioProject, "api_handler", new_callable=MagicMock
        ).start()
        self.mock_save_config = patch.object(AgentStudioProject, "save_config").start()
        self.mock_save_imports = patch("poly.utils.save_imports").start()
        self.mock_export_decorators = patch("poly.utils.export_decorators").start()
        self.mock_resource_save = patch.object(Resource, "save").start()
        self.mock_write_cache = patch.object(
            MultiResourceYamlResource, "write_cache_to_file"
        ).start()

    def tearDown(self):
        patch.stopall()

    def test_on_save_called_with_correct_progress(self):
        """on_save should be called once per resource with (current, total)"""
        self.mock_api_handler.pull_resources.return_value = (
            AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR).resources,
            {},
        )
        on_save = MagicMock()

        project, _ = AgentStudioProject.init_project(
            base_path=os.path.join(TEST_DIR, "tmp"),
            region="us-1",
            account_id="test_account",
            project_id="test_project",
            on_save=on_save,
        )

        total = len(project.all_resources)
        self.assertEqual(on_save.call_count, total)
        on_save.assert_any_call(1, total)
        on_save.assert_any_call(total, total)

    def test_no_on_save_does_not_error(self):
        """init_project without on_save should work without errors"""
        self.mock_api_handler.pull_resources.return_value = (
            AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR).resources,
            {},
        )

        project, _ = AgentStudioProject.init_project(
            base_path=os.path.join(TEST_DIR, "tmp"),
            region="us-1",
            account_id="test_account",
            project_id="test_project",
        )
        self.assertIsNotNone(project)


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

    def test_document_round_trip(self):
        """Document serializes and deserializes via status dict correctly."""
        doc = Document(resource_id="test.md", name="test", path="test.md", contents="hello world\n")
        serialized = resource_utils.resource_to_dict(doc)
        restored = Document(**serialized)
        self.assertEqual(restored.resource_id, "test.md")
        self.assertEqual(restored.name, "test")
        self.assertEqual(restored.path, "TEST.MD")
        self.assertEqual(restored.contents, "hello world\n")
        self.assertEqual(restored.file_path, os.path.join("context", "TEST.MD"))
        self.assertEqual(restored.compute_hash(), doc.compute_hash())

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

        # Find test cases
        self.assertEqual(len(local_resources[TestCase]), 2)
        self.assertCountEqual(
            local_resources[TestCase],
            [
                os.path.join(TEST_DIR, "test_suite", "greeting_flow_test.yaml"),
                os.path.join(TEST_DIR, "test_suite", "webchat_smoke_test.yaml"),
            ],
        )

        # Find Translations
        self.assertEqual(len(local_resources[Translation]), 2)
        self.assertCountEqual(
            local_resources[Translation],
            [
                os.path.join(TEST_DIR, "config", "translations.yaml", "translations", "greeting"),
                os.path.join(TEST_DIR, "config", "translations.yaml", "translations", "farewell"),
            ],
        )

        # Find Documents
        self.assertEqual(len(local_resources[Document]), 1)
        self.assertCountEqual(
            local_resources[Document],
            [
                os.path.join(TEST_DIR, "context", "TEST_DOCUMENT.MD"),
            ],
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
            os.path.join(TEST_DIR, "topics", "topic_1.yaml"),
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

    def test_find_new_kept_deleted_new_flow_steps_use_flow_id_prefix(self):
        """When flow resources are not loaded, new flow steps should use
        the FlowConfig's generated flow_id as their resource_id prefix,
        not the flow_name."""
        project_data = deepcopy(PROJECT_DATA)
        # Remove all flow resources so they appear as new (not loaded)
        project_data["resources"].pop("flow_config", None)
        project_data["resources"].pop("flow_steps", None)
        project_data["resources"].pop("function_steps", None)

        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        local_resources = project.discover_local_resources()
        new_mappings, kept_mappings, _ = project.find_new_kept_deleted(local_resources)

        new_flow_configs = [m for m in new_mappings if m.resource_type == FlowConfig]
        new_flow_steps = [m for m in new_mappings if m.resource_type == FlowStep]
        new_function_steps = [m for m in new_mappings if m.resource_type == FunctionStep]

        self.assertTrue(len(new_flow_configs) > 0)
        self.assertTrue(len(new_flow_steps) > 0)

        # Build flow_name -> flow_id map from the new FlowConfig mappings
        flow_id_by_name = {m.flow_name: m.resource_id for m in new_flow_configs}

        # Every new flow step's resource_id should start with its flow's flow_id
        for step_mapping in new_flow_steps + new_function_steps:
            expected_flow_id = flow_id_by_name[step_mapping.flow_name]
            self.assertTrue(
                step_mapping.resource_id.startswith(expected_flow_id + "_"),
                f"Step {step_mapping.resource_name} resource_id '{step_mapping.resource_id}' "
                f"should start with flow_id '{expected_flow_id}_'",
            )
            self.assertEqual(step_mapping.flow_id, expected_flow_id)


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
        self.assertEqual(new_files, [os.path.join(TEST_DIR, "topics", "topic_1.yaml")])
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
        self.assertEqual(modified_files, [])
        self.assertEqual(new_files, [])
        self.assertEqual(deleted_files, [])

    def test_project_status_merge_conflict_in_multi_resource_yaml(self):
        """A conflicted multi-resource YAML file is listed (not raised) by project_status.

        The conflict is detected during discovery (discover_resources ->
        _get_top_level_data); project_status collects the true file path into
        files_with_conflicts and skips that file's resources instead of raising or
        counting them as deleted.
        """
        project = AgentStudioProject.from_dict(deepcopy(PROJECT_DATA), TEST_DIR)
        entities_path = os.path.join(TEST_DIR, "config", "entities.yaml")
        # The multi-resource file is cached by mtime; clear it so the mock is read.
        Entity._file_cache.clear()

        conflicted_entities = (
            "entities:\n"
            "<<<<<<<\n"
            "  - name: customer_name\n"
            "    entity_type: name_config\n"
            "=======\n"
            "  - name: caller_name\n"
            "    entity_type: name_config\n"
            ">>>>>>>\n"
        )

        with mock_read_from_file({entities_path: conflicted_entities}):
            files_with_conflicts, modified_files, new_files, deleted_files = (
                project.project_status()
            )

        self.assertEqual(files_with_conflicts, [entities_path])
        # The conflicted file's entities must not be reported as deleted.
        self.assertFalse(any(entities_path in path for path in deleted_files))

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
        project_data["resources"]["flow_steps"]["FLOW_CONFIG-test_flow_start_step"]["prompt"] = (
            "Modified prompt"
        )

        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        files_with_conflicts, modified_files, new_files, deleted_files = project.project_status()
        self.assertEqual(files_with_conflicts, [])
        self.assertEqual(
            modified_files,
            [os.path.join(TEST_DIR, "flows", "test_flow", "steps", "start_step.yaml")],
        )
        self.assertEqual(new_files, [os.path.join(TEST_DIR, "topics", "topic_1.yaml")])
        self.assertEqual(deleted_files, [os.path.join(TEST_DIR, "functions", "extra_function.py")])


class DiffProjectionsTest(unittest.TestCase):
    """Tests for the diff_projections method"""

    @staticmethod
    def _projection(topics: dict[str, tuple[str, str]]) -> dict:
        return {
            "knowledgeBase": {
                "topics": {
                    "entities": {
                        topic_id: {
                            "name": name,
                            "actions": "",
                            "content": content,
                            "exampleQueries": [],
                            "isActive": True,
                        }
                        for topic_id, (name, content) in topics.items()
                    }
                }
            }
        }

    def setUp(self):
        self.project = AgentStudioProject.from_dict(deepcopy(PROJECT_DATA), TEST_DIR)

    def test_identical_projections_return_none(self):
        projection = self._projection({"TOPIC-1": ("Opening Hours", "We open at 9am")})
        self.assertIsNone(self.project.diff_projections(projection, deepcopy(projection)))

    def test_modified_resource(self):
        before = self._projection({"TOPIC-1": ("Opening Hours", "We open at 9am")})
        after = self._projection({"TOPIC-1": ("Opening Hours", "We open at 8am")})
        diffs = self.project.diff_projections(before, after)

        topic_path = os.path.join("topics", "opening_hours.yaml")
        self.assertEqual(list(diffs.keys()), [topic_path])
        self.assertIn("-content: We open at 9am", diffs[topic_path])
        self.assertIn("+content: We open at 8am", diffs[topic_path])

    def test_added_and_deleted_resources(self):
        before = self._projection(
            {
                "TOPIC-1": ("Opening Hours", "We open at 9am"),
                "TOPIC-2": ("Parking", "Free parking on site"),
            }
        )
        after = self._projection(
            {
                "TOPIC-1": ("Opening Hours", "We open at 9am"),
                "TOPIC-3": ("Refunds", "Refunds within 30 days"),
            }
        )
        diffs = self.project.diff_projections(before, after)

        parking_path = os.path.join("topics", "parking.yaml")
        refunds_path = os.path.join("topics", "refunds.yaml")
        self.assertEqual(sorted(diffs.keys()), [parking_path, refunds_path])
        self.assertIn("-content: Free parking on site", diffs[parking_path])
        self.assertIn("+content: Refunds within 30 days", diffs[refunds_path])

    def test_empty_projections(self):
        after = self._projection({"TOPIC-1": ("Opening Hours", "We open at 9am")})
        diffs = self.project.diff_projections({}, after)
        self.assertIn(os.path.join("topics", "opening_hours.yaml"), diffs)
        self.assertIsNone(self.project.diff_projections({}, {}))


class GetDiffsTest(unittest.TestCase):
    """Tests for the get_diffs method"""

    def test_get_diffs_no_changes(self):
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        diffs = project.get_diffs()
        self.assertEqual(diffs, {})

    def test_get_diffs_new_resource(self):
        project_data = deepcopy(PROJECT_DATA)
        # Remove a topic so it seems there's a new one
        project_data["resources"]["topics"].pop("TOPIC-Topic 1")
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        diffs = project.get_diffs()

        topic_path = os.path.join("topics", "topic_1.yaml")
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
        diffs = project.get_diffs()

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
        diffs = project.get_diffs()

        func_path = os.path.join("functions", "test_function.py")
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
        diffs = project.get_diffs()

        topic_path = os.path.join("topics", "topic_1.yaml")
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
        requested_file = os.path.join(TEST_DIR, "topics", "topic_1.yaml")
        diffs = project.get_diffs(file_paths=[requested_file])

        # Topic diff
        topic_path = os.path.join("topics", "topic_1.yaml")
        self.assertIn(topic_path, diffs)
        diff = diffs[topic_path]
        self.assertIn("--- original", diff)
        self.assertIn("+++ updated", diff)

        # No diff for function
        func_path = os.path.join(TEST_DIR, "functions", "extra_function.py")
        self.assertNotIn(func_path, diffs)

    def test_get_diffs_no_diff_for_reordered_extracted_entities(self):
        """Reordering extracted_entities should not produce a diff."""
        project_data = deepcopy(PROJECT_DATA)
        # Reverse the extracted_entities order so it differs from local YAML
        step = project_data["resources"]["flow_steps"][
            "FLOW_CONFIG-test_flow_with_punctuation_welcome_step"
        ]
        step["extracted_entities"] = list(reversed(step["extracted_entities"]))
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)
        diffs = project.get_diffs()

        step_path = os.path.join(
            "flows", "test_flow_with_punctuation!", "steps", "welcome_step.yaml"
        )
        self.assertNotIn(step_path, diffs)

    def test_get_diffs_raises_when_single_file_resource_has_conflict(self):
        """A merge conflict in a function .py file makes get_diffs raise."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        func_path = os.path.join(TEST_DIR, "functions", "test_function.py")

        conflicted_code = (
            "from _gen import *  # <AUTO GENERATED>\n\n"
            "def test_function(conv: Conversation):\n"
            "<<<<<<<\n"
            '    return "ours"\n'
            "=======\n"
            '    return "theirs"\n'
            ">>>>>>>\n"
        )

        with mock_read_from_file({func_path: conflicted_code}):
            with self.assertRaises(resource_utils.MergeConflictError) as ctx:
                project.get_diffs()

        self.assertIn(func_path, str(ctx.exception))

    def test_get_diffs_raises_when_multi_resource_yaml_has_conflict(self):
        """A conflict in a multi-resource YAML file makes get_diffs raise.

        For multi-resource YAML files the guard fires during discovery
        (discover_resources -> _get_top_level_data), before get_diffs reaches its
        own conflict-collecting loops, so the error is raised with the true on-disk
        .yaml path rather than a synthetic sub-resource path.
        """
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        entities_path = os.path.join(TEST_DIR, "config", "entities.yaml")
        # The multi-resource file is cached by mtime; clear it so the mock is read.
        Entity._file_cache.clear()

        conflicted_entities = (
            "entities:\n"
            "<<<<<<<\n"
            "  - name: customer_name\n"
            "    entity_type: name_config\n"
            "=======\n"
            "  - name: caller_name\n"
            "    entity_type: name_config\n"
            ">>>>>>>\n"
        )

        with mock_read_from_file({entities_path: conflicted_entities}):
            with self.assertRaises(resource_utils.MergeConflictError) as ctx:
                project.get_diffs()

        # The reported path is the true .yaml file, not a synthetic sub-resource path.
        self.assertIn(entities_path, str(ctx.exception))

    def test_get_diffs_aggregates_conflicts_from_multiple_files(self):
        """When two single-file resources conflict, the raised error lists both paths."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        func_path = os.path.join(TEST_DIR, "functions", "test_function.py")
        other_func_path = os.path.join(TEST_DIR, "functions", "validate_email.py")

        conflicted_code = (
            "from _gen import *  # <AUTO GENERATED>\n\n"
            "def test_function(conv: Conversation):\n"
            "<<<<<<<\n"
            '    return "ours"\n'
            "=======\n"
            '    return "theirs"\n'
            ">>>>>>>\n"
        )
        other_conflicted_code = (
            "from _gen import *  # <AUTO GENERATED>\n\n"
            "def validate_email(conv: Conversation):\n"
            "<<<<<<<\n"
            "    return True\n"
            "=======\n"
            "    return False\n"
            ">>>>>>>\n"
        )

        with mock_read_from_file(
            {func_path: conflicted_code, other_func_path: other_conflicted_code}
        ):
            with self.assertRaises(resource_utils.MergeConflictError) as ctx:
                project.get_diffs()

        message = str(ctx.exception)
        self.assertIn(func_path, message)
        self.assertIn(other_func_path, message)


class CleanResourcesBeforePushTest(unittest.TestCase):
    """Tests for the _clean_resources_before_push method"""

    def setUp(self):
        # Mock the api_handler property: accessing it saves the project config as a
        # side effect, which would write _gen/.agent_studio_config into the fixture
        self.mock_api_handler = patch.object(
            AgentStudioProject, "api_handler", new_callable=MagicMock
        ).start()
        self.project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

    def tearDown(self):
        patch.stopall()

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
        dummy_id = "flow-123_step-1_temp"
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
            resource_id="flow-123_step-1",
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
            resource_id="flow-123_step-2",
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

        self.project.resources.setdefault(FlowStep, {})["flow-123_step-1"] = old_start_step
        self.project.resources.setdefault(FlowConfig, {})["flow-123"] = flow_config

        new_resources = {FlowStep: {"flow-123_step-2": new_start_step}}
        updated_resources = {FlowConfig: {"flow-123": updated_flow_config}}
        deleted_resources = {FlowStep: {"flow-123_step-1": old_start_step}}

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
        self.assertNotIn("flow-123_step-1", cleaned_deleted.get(FlowStep, {}))
        self.assertIn(FlowStep, post_push_deleted)
        self.assertIn("flow-123_step-1", post_push_deleted[FlowStep])

        # New step in new, flow config in updated
        self.assertIn("flow-123_step-2", cleaned_new[FlowStep])
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
            resource_id="flow-123_step-abc123",
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
            resource_id="flow-123_step-1",
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

        self.project.resources.setdefault(FlowStep, {})["flow-123_step-abc123"] = old_start_step
        self.project.resources.setdefault(FlowConfig, {})["flow-123"] = flow_config

        new_resources = {FlowStep: {"flow-123_step-1": new_start_step}}
        updated_resources = {FlowConfig: {"flow-123": updated_flow_config}}
        deleted_resources = {FlowStep: {"flow-123_step-abc123": old_start_step}}

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
        dummy_id = "flow-123_step-abc123_temp"
        self.assertIn(dummy_id, pre_push_new[FlowStep])
        dummy = pre_push_new[FlowStep][dummy_id]
        self.assertEqual(dummy.step_id, "step-abc123_temp")

        self.assertIn(FlowConfig, pre_push_updated)
        self.assertEqual(pre_push_updated[FlowConfig]["flow-123"].start_step, "step-abc123_temp")

        # Post-push: delete dummy (not old step - old stays in main push deleted)
        self.assertIn(FlowStep, post_push_deleted)
        self.assertIn(dummy_id, post_push_deleted[FlowStep])

        # Main push: old in deleted, new in new, flow config in updated
        self.assertIn("flow-123_step-abc123", cleaned_deleted[FlowStep])
        self.assertIn("flow-123_step-1", cleaned_new[FlowStep])
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
            resource_id="flow-123_func_step",
            step_id="func_step",
            name="Func Start",
            flow_id="flow-123",
            flow_name="Test Flow",
            code="def handler(conv): pass",
            position={"x": 0.0, "y": 0.0},
            function_id="FUNC-123",
        )
        new_flow_step = FlowStep(
            resource_id="flow-123_step-2",
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

        self.project.resources.setdefault(FunctionStep, {})["flow-123_func_step"] = (
            old_function_step
        )
        self.project.resources.setdefault(FlowConfig, {})["flow-123"] = flow_config

        new_resources = {FlowStep: {"flow-123_step-2": new_flow_step}}
        updated_resources = {FlowConfig: {"flow-123": updated_flow_config}}
        deleted_resources = {FunctionStep: {"flow-123_func_step": old_function_step}}

        push_changes = self.project._clean_resources_before_push(
            {},
            new_resources,
            updated_resources,
            deleted_resources,
        )
        cleaned_deleted = push_changes.main.deleted
        post_push_deleted = push_changes.post.deleted

        # Old FunctionStep should be in post-push deleted
        self.assertNotIn("flow-123_func_step", cleaned_deleted.get(FunctionStep, {}))
        self.assertIn(FunctionStep, post_push_deleted)
        self.assertIn("flow-123_func_step", post_push_deleted[FunctionStep])

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
            resource_id="flow-123_func_step_old",
            step_id="func_step_old",
            name="Func Start",
            flow_id="flow-123",
            flow_name="Test Flow",
            code="def handler(conv): pass",
            position={"x": 0.0, "y": 0.0},
            function_id="FUNC-123",
        )
        new_function_step = FunctionStep(
            resource_id="flow-123_func_step",
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

        self.project.resources.setdefault(FunctionStep, {})["flow-123_func_step_old"] = (
            old_function_step
        )
        self.project.resources.setdefault(FlowConfig, {})["flow-123"] = flow_config

        new_resources = {FunctionStep: {"flow-123_func_step": new_function_step}}
        updated_resources = {FlowConfig: {"flow-123": updated_flow_config}}
        deleted_resources = {FunctionStep: {"flow-123_func_step_old": old_function_step}}

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
        self.assertIn("flow-123_func_step_old_temp", pre_push_new[FlowStep])
        self.assertIn(FlowConfig, pre_push_updated)

        # Post-push: delete dummy
        self.assertIn(FlowStep, post_push_deleted)
        self.assertIn("flow-123_func_step_old_temp", post_push_deleted[FlowStep])

        # Main push: old in deleted, new in new
        self.assertIn("flow-123_func_step_old", cleaned_deleted[FunctionStep])
        self.assertIn("flow-123_func_step", cleaned_new[FunctionStep])

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
            resource_id="flow-new-func-start_entry_func",
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
            FunctionStep: {"flow-new-func-start_entry_func": function_start_step},
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
        self.assertIn("flow-new-func-start_entry_func_start_step_temp", post_deleted[FlowStep])

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

    def test_clean_resources_before_push_does_not_delete_condition_when_parent_step_deleted(self):
        """When a FlowStep is deleted, its conditions should not be in deleted_resources."""
        condition = Condition(
            resource_id="CONDITION-cond-1",
            name="cond-1",
            condition_type="step_condition",
            step_id="step-1",
            flow_id="flow-123",
            child_step="step-2",
        )
        flow_step = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Step 1",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.ADVANCED_STEP,
            prompt="Hello",
            conditions=[condition],
        )

        deleted_resources = {
            FlowStep: {"flow-123_step-1": flow_step},
            Condition: {"CONDITION-cond-1": condition},
        }

        push_changes = self.project._clean_resources_before_push(
            {},
            {},
            {},
            deleted_resources,
        )
        cleaned_deleted = push_changes.main.deleted

        # The step should still be deleted
        self.assertIn("flow-123_step-1", cleaned_deleted.get(FlowStep, {}))
        # But the condition belonging to that step should NOT be deleted
        self.assertNotIn("CONDITION-cond-1", cleaned_deleted.get(Condition, {}))

    def test_clean_resources_before_push_condition_update_becomes_create_when_original_target_step_deleted(
        self,
    ):
        """When a condition is updated but its original child_step is being deleted,
        move it from updated to new (the platform auto-deletes the condition on step delete,
        so an update would fail)."""
        original_condition = Condition(
            resource_id="CONDITION-cond-1",
            name="cond-1",
            condition_type="step_condition",
            step_id="step-1",
            flow_id="flow-123",
            child_step="step-to-delete",
        )
        original_flow_step = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Step 1",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.ADVANCED_STEP,
            prompt="Hello",
            conditions=[original_condition],
        )
        step_to_delete = FlowStep(
            resource_id="flow-123_step-to-delete",
            step_id="step-to-delete",
            name="Step To Delete",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.ADVANCED_STEP,
            prompt="Goodbye",
        )
        updated_condition = Condition(
            resource_id="CONDITION-cond-1",
            name="cond-1",
            condition_type="step_condition",
            step_id="step-1",
            flow_id="flow-123",
            child_step="step-new-target",
        )

        self.project.resources.setdefault(FlowStep, {})["flow-123_step-1"] = original_flow_step

        push_changes = self.project._clean_resources_before_push(
            {},
            {},
            {Condition: {"CONDITION-cond-1": updated_condition}},
            {FlowStep: {"flow-123_step-to-delete": step_to_delete}},
        )
        cleaned_new = push_changes.main.new
        cleaned_updated = push_changes.main.updated

        # Condition should be promoted to a create
        self.assertIn("CONDITION-cond-1", cleaned_new.get(Condition, {}))
        # And removed from updated
        self.assertNotIn("CONDITION-cond-1", cleaned_updated.get(Condition, {}))

    def test_clean_resources_before_push_webchat_enables_channel_and_moves_to_updates(self):
        """New webchat configs should enable the channel and be moved to pre-push updates."""
        greeting = ChatGreeting(
            resource_id="chat-greeting-1",
            name="greeting",
            welcome_message="Hello",
            language_code="en-GB",
        )
        safety = ChatSafetyFilters(
            resource_id="chat-safety-1",
            name="safety_filters",
            enabled=True,
            categories={
                "violence": {"enabled": True, "precision": "MEDIUM"},
                "hate": {"enabled": True, "precision": "MEDIUM"},
                "sexual": {"enabled": True, "precision": "MEDIUM"},
                "self_harm": {"enabled": True, "precision": "MEDIUM"},
            },
        )
        style = ChatStylePrompt(
            resource_id="chat-style-1",
            name="style_prompt",
            prompt="Be helpful",
        )
        new_resources = {
            ChatGreeting: {"chat-greeting-1": greeting},
            ChatSafetyFilters: {"chat-safety-1": safety},
            ChatStylePrompt: {"chat-style-1": style},
        }

        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            push_changes = self.project._clean_resources_before_push({}, new_resources, {}, {})
            mock_api.queue_command.assert_called_once()

        self.assertNotIn(ChatGreeting, push_changes.main.new)
        self.assertNotIn(ChatSafetyFilters, push_changes.main.new)
        self.assertNotIn(ChatStylePrompt, push_changes.main.new)
        self.assertIn(ChatGreeting, push_changes.pre.updated)
        self.assertIn(ChatSafetyFilters, push_changes.pre.updated)
        self.assertIn(ChatStylePrompt, push_changes.pre.updated)

    def test_new_variant_excludes_deleted_attribute_ids(self):
        """New variants should not reference attributes that are being deleted."""
        attr_keep = VariantAttribute(
            resource_id="VARIANT_ATTRIBUTES-keep",
            name="greeting_name",
            mappings={"v1": "Hello"},
        )
        attr_delete = VariantAttribute(
            resource_id="VARIANT_ATTRIBUTES-delete",
            name="old_attribute",
            mappings={"v1": "old_value"},
        )
        self.project.resources[VariantAttribute] = {
            "VARIANT_ATTRIBUTES-keep": attr_keep,
            "VARIANT_ATTRIBUTES-delete": attr_delete,
        }

        new_variant = Variant(
            resource_id="VARIANTS-new",
            name="New Variant",
            is_default=False,
        )

        new_resources = {Variant: {"VARIANTS-new": new_variant}}
        deleted_resources = {VariantAttribute: {"VARIANT_ATTRIBUTES-delete": attr_delete}}

        self.project._clean_resources_before_push(
            {},
            new_resources,
            {},
            deleted_resources,
        )

        self.assertEqual(new_variant.attribute_ids, ["VARIANT_ATTRIBUTES-keep"])


class PushProjectTest(unittest.TestCase):
    """Tests for the push_project method"""

    def setUp(self):
        """Set up common mocks for push_project tests"""
        self.mock_pull = patch.object(AgentStudioProject, "pull_project").start()
        self.mock_api_handler = patch.object(
            AgentStudioProject, "api_handler", new_callable=MagicMock
        ).start()
        self.mock_save_config = patch.object(AgentStudioProject, "save_config").start()
        self.mock_pull.return_value = ([], {})
        self.mock_api_handler.queue_resources = MagicMock(return_value=[])
        self.mock_api_handler.send_queued_commands = MagicMock(return_value=True)
        self.mock_api_handler.clear_command_queue = MagicMock()
        self.mock_load_project = patch.object(AgentStudioProject, "load_project").start()

    def tearDown(self):
        """Clean up patches"""
        patch.stopall()

    def test_push_project_no_changes(self):
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

        success, message, commands = project.push_project(force=True)

        self.assertFalse(success)
        self.assertEqual(message, "No changes detected")
        self.mock_api_handler.queue_resources.assert_not_called()

    def test_push_project_merge_conflict(self):
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        self.mock_pull.return_value = (["functions/test_function.py"], {})

        success, message, commands = project.push_project(force=False)

        self.assertFalse(success)
        self.assertIn("Merge conflicts detected", message)
        self.assertIn("test_function.py", message)

    def test_push_project_new_resources(self):
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["topics"].pop("TOPIC-Topic 1")
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, commands = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.queue_resources.assert_called_once()
        call_args = self.mock_api_handler.queue_resources.call_args
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

        success, message, commands = project.push_project(force=True, skip_validation=True)

        self.assertTrue(success, f"Push failed: {message}")
        self.mock_api_handler.queue_resources.assert_called_once()
        call_args = self.mock_api_handler.queue_resources.call_args
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

        success, message, commands = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.queue_resources.assert_called_once()
        call_args = self.mock_api_handler.queue_resources.call_args
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
            success, message, commands = project.push_project(force=True, skip_validation=True)

        self.assertTrue(success, f"Push failed: {message}")
        self.mock_api_handler.queue_resources.assert_called_once()
        call_args = self.mock_api_handler.queue_resources.call_args
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

        success, message, commands = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.queue_resources.assert_called_once()
        call_args = self.mock_api_handler.queue_resources.call_args
        updated_resources = call_args.kwargs["updated_resources"]
        self.assertIn(Function, updated_resources)
        self.assertIn("FUNCTION-test_function", updated_resources[Function])

    def test_push_project_modified_sub_resources_dtmf(self):
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["flow_steps"]["FLOW_CONFIG-test_flow_start_step"]["dtmf_config"][
            "is_enabled"
        ] = True
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, commands = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.queue_resources.assert_called_once()
        call_args = self.mock_api_handler.queue_resources.call_args
        updated_resources = call_args.kwargs["updated_resources"]
        self.assertIn(DTMFConfig, updated_resources)

    def test_push_project_new_sub_resources_condition(self):
        project_data = deepcopy(PROJECT_DATA)
        # Delete condition in project_data to mimic new condition locally
        project_data["resources"]["flow_steps"]["FLOW_CONFIG-test_flow_collect_name"][
            "conditions"
        ] = []

        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, commands = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.queue_resources.assert_called_once()
        call_args = self.mock_api_handler.queue_resources.call_args
        new_resources = call_args.kwargs["new_resources"]
        self.assertIn(Condition, new_resources)
        # Deleted 2 conditions, so check that 2 new conditions are pushed
        self.assertEqual(len(new_resources[Condition]), 2)

    def test_push_project_deleted_sub_resource_condition(self):
        project_data = deepcopy(PROJECT_DATA)
        # Mimic deleting a condition locally by adding to project data
        project_data["resources"]["flow_steps"]["FLOW_CONFIG-test_flow_collect_name"][
            "conditions"
        ].append(
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

        success, message, commands = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.queue_resources.assert_called_once()
        call_args = self.mock_api_handler.queue_resources.call_args
        deleted_resources = call_args.kwargs["deleted_resources"]
        self.assertIn(Condition, deleted_resources)

    def test_push_project_updated_sub_resource_asr_biasing(self):
        """Test pushing an updated ASRBiasing sub-resource"""
        project_data = deepcopy(PROJECT_DATA)
        # Modify ASR biasing in project_data
        project_data["resources"]["flow_steps"]["FLOW_CONFIG-test_flow_start_step"]["asr_biasing"][
            "custom_keywords"
        ] = ["NewKeyword1", "NewKeyword2"]

        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, commands = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.queue_resources.assert_called_once()
        call_args = self.mock_api_handler.queue_resources.call_args
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
        project_data["resources"]["flow_steps"]["FLOW_CONFIG-test_flow_start_step"]["asr_biasing"][
            "is_enabled"
        ] = False
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, commands = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.queue_resources.assert_called_once()
        call_args = self.mock_api_handler.queue_resources.call_args
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

        success, message, commands = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.queue_resources.assert_called_once()
        call_args = self.mock_api_handler.queue_resources.call_args
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

        success, message, commands = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.queue_resources.assert_called_once()
        call_args = self.mock_api_handler.queue_resources.call_args
        deleted_resources = call_args.kwargs["deleted_resources"]
        self.assertIn(KeyphraseBoosting, deleted_resources)
        self.assertIn("KEYPHRASE_BOOSTING-extra", deleted_resources[KeyphraseBoosting])

    def test_push_project_modified_keyphrase_boosting(self):
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["keyphrase_boosting"]["KEYPHRASE_BOOSTING-polyai"]["level"] = (
            "default"
        )
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, commands = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.queue_resources.assert_called_once()
        call_args = self.mock_api_handler.queue_resources.call_args
        updated_resources = call_args.kwargs["updated_resources"]
        self.assertIn(KeyphraseBoosting, updated_resources)
        self.assertIn("KEYPHRASE_BOOSTING-polyai", updated_resources[KeyphraseBoosting])

    def test_push_project_new_transcript_correction(self):
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["transcript_corrections"].pop(
            "TRANSCRIPT_CORRECTIONS-email_domain"
        )
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, commands = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.queue_resources.assert_called_once()
        call_args = self.mock_api_handler.queue_resources.call_args
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

        success, message, commands = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.queue_resources.assert_called_once()
        call_args = self.mock_api_handler.queue_resources.call_args
        deleted_resources = call_args.kwargs["deleted_resources"]
        self.assertIn(TranscriptCorrection, deleted_resources)
        self.assertIn("TRANSCRIPT_CORRECTIONS-extra", deleted_resources[TranscriptCorrection])

    def test_push_project_modified_asr_settings(self):
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["asr_settings"]["asr_settings"]["barge_in"] = True
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, commands = project.push_project(force=True)

        self.assertTrue(success)
        self.mock_api_handler.queue_resources.assert_called_once()
        call_args = self.mock_api_handler.queue_resources.call_args
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
            success, message, commands = project.push_project(force=True, skip_validation=False)

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
            success, message, commands = project.push_project(force=True, skip_validation=True)

        self.assertTrue(success)

    def test_push_project_dry_run(self):
        project_data = deepcopy(PROJECT_DATA)
        project_data["resources"]["topics"].pop("TOPIC-Topic 1")
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        success, message, commands = project.push_project(force=True, dry_run=True)

        self.assertTrue(success)
        self.assertIn("Dry run completed", message)
        self.mock_api_handler.queue_resources.assert_called_once()
        self.mock_api_handler.send_queued_commands.assert_not_called()
        self.mock_api_handler.clear_command_queue.assert_called_once()


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
                    TEST_DIR, "topics", "topic_1.yaml"
                ): 'name: Topic 1\ncontent: Topic 1 content\nexample_queries:\n- Topic 1 example query\nenabled: true\nactions: "{{fn:FUNCTION-missing_function}}"\n',
                os.path.join(
                    TEST_DIR, "flows", "test_flow", "flow_config.yaml"
                ): "name: test_flow\ndescription: \nstart_step: missing_step\n",
            }
        ):
            errors = project.validate_project()
        self.assertEqual(len(errors), 2)
        error_texts = "\n".join(errors)
        self.assertIn(
            "Invalid references: ['global_functions: FUNCTION-missing_function']", error_texts
        )
        self.assertIn("Start step 'missing_step' not found.", error_texts)


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
        self.mock_api_handler.pull_resources.return_value = (original_resources, {})

        files_with_conflicts, _ = project.pull_project(force=False)
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
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

        with mock_read_from_file(
            {os.path.join(TEST_DIR, "config", "variant_attributes.yaml"): "{}\n"}
        ):
            files_with_conflicts, _ = project.pull_project(force=False)

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
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

        files_with_conflicts, _ = project.pull_project(force=False)
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
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

        files_with_conflicts, _ = project.pull_project(force=False)

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
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

        files_with_conflicts, _ = project.pull_project(force=False)
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
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

        with mock_read_from_file(
            {
                os.path.join(
                    TEST_DIR, "functions", "test_function.py"
                ): 'from _gen import *  # <AUTO GENERATED>\n\n@func_description(\'A test function for global use.\')\ndef test_function(conv: Conversation):\n    """Modified locally."""\n    return "Local change"\n'
            }
        ):
            files_with_conflicts, _ = project.pull_project(force=False)
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
        merged_content = 'from _gen import *  # <AUTO GENERATED>\n\n\n@func_description(\'A test function for global use.\')\ndef test_function(conv: Conversation):\n<<<<<<<\n    """Modified locally."""\n    return "Local change"\n=======\n    """Modified remotely."""\n    return "Remote change"\n>>>>>>>\n'
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
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

        # Mock local file with different changes
        flow_config_path = os.path.join(TEST_DIR, "flows", "test_flow", "flow_config.yaml")
        with mock_read_from_file(
            {
                flow_config_path: "name: test_flow\ndescription: Modified locally - different description\nstart_step: start_step\n"
            }
        ):
            files_with_conflicts, _ = project.pull_project(force=False)
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

    def test_pull_project_local_formatting_difference_no_false_conflict(self):
        """Cosmetic formatting differences in the local file should not cause merge conflicts.

        The local file has the same semantic content as the original but with trailing
        whitespace in the description.  The normalisation step (read_local_resource +
        to_pretty) should produce the same string as the canonical original, so when
        the remote modifies the description the merge should apply cleanly.
        """
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        original_resources = deepcopy(project.resources)

        # Remote modifies the description
        incoming_resources = deepcopy(original_resources)
        flow_config_id = "FLOW_CONFIG-test_flow"
        modified_flow_config = deepcopy(incoming_resources[FlowConfig][flow_config_id])
        modified_flow_config.description = "Modified remotely"
        incoming_resources[FlowConfig][flow_config_id] = modified_flow_config
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

        flow_config_path = os.path.join(TEST_DIR, "flows", "test_flow", "flow_config.yaml")
        # Local file: same semantic content as original but with trailing whitespace
        local_with_cosmetic_diff = (
            "name: test_flow\n"
            "description: Test flow with advanced step as start   \n"
            "start_step: start_step\n"
        )

        with mock_read_from_file({flow_config_path: local_with_cosmetic_diff}):
            files_with_conflicts, _ = project.pull_project(force=False)

        self.assertEqual(files_with_conflicts, [])
        flow_config_calls = [
            call
            for call in self.mock_save_to_file.call_args_list
            if len(call[0]) >= 2 and call[0][1] == flow_config_path
        ]
        saved_content = flow_config_calls[-1][0][0] if flow_config_calls else ""
        self.assertNotIn("<<<<<<<", saved_content)
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
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

        with mock_read_from_file(
            {
                os.path.join(
                    TEST_DIR, "functions", "test_function.py"
                ): 'from _gen import *  # <AUTO GENERATED>\n\ndef added_extra_function():\n    pass\n\n@func_description(\'A test function for global use.\')\ndef test_function(conv: Conversation):\n    """A test function for global use."""\n    return "Hello from global function"\n'
            }
        ):
            files_with_conflicts, _ = project.pull_project(force=False)
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
        merged_content = 'from _gen import *  # <AUTO GENERATED>\n\n\ndef added_extra_function():\n    pass\n\n@func_description(\'A test function for global use.\')\ndef test_function(conv: Conversation):\n    """Modified remotely."""\n    return "Remote change"\n'
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
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

        with mock_read_from_file(
            {
                os.path.join(
                    TEST_DIR, "functions", "test_function.py"
                ): 'from _gen import *  # <AUTO GENERATED>\n\n@func_description(\'A test function for global use.\')\ndef test_function(conv: Conversation):\n    """Modified locally."""\n    return "Local change"\n'
            }
        ):
            files_with_conflicts, _ = project.pull_project(force=True)

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

        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})
        files_with_conflicts, _ = project.pull_project(force=False, format=True)
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

        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})
        files_with_conflicts, _ = project.pull_project(force=False)
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

        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})
        files_with_conflicts, _ = project.pull_project(force=False)
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

        self.mock_api_handler.pull_resources.return_value = (original_resources, {})

        files_with_conflicts, _ = project.pull_project(force=False)

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
        original_resources = deepcopy(project.resources)
        self.mock_api_handler.pull_resources.return_value = (original_resources, {})

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
            files_with_conflicts, _ = project.pull_project(force=False)

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
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

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
            files_with_conflicts, _ = project.pull_project(force=False)
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
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

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
            files_with_conflicts, _ = project.pull_project(force=False)
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
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

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
            "  - keyphrase: PolyAI\n"
            "    level: default\n"
            "  - keyphrase: reservation\n"
            "    level: boosted\n"
            "  - keyphrase: check-in\n"
            "    level: default\n"
        )

        MultiResourceYamlResource._file_cache.clear()
        with patch(
            "poly.resources.resource.Resource.read_from_file",
            side_effect=self._make_kp_read_mock(original_kp_content, local_kp_content),
        ):
            files_with_conflicts, _ = project.pull_project(force=False)
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
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

        kp_path = os.path.join(TEST_DIR, "voice", "speech_recognition", "keyphrase_boosting.yaml")

        MultiResourceYamlResource._file_cache.clear()
        files_with_conflicts, _ = project.pull_project(force=True)
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

    def test_pull_project_on_save_callback(self):
        """on_save should be called during pull with correct final progress"""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        incoming_resources = deepcopy(project.resources)
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

        on_save = MagicMock()
        files_with_conflicts, _ = project.pull_project(on_save=on_save)

        self.assertEqual(files_with_conflicts, [])
        self.assertGreater(on_save.call_count, 0)
        last_call = on_save.call_args_list[-1]
        current, total = last_call[0]
        self.assertEqual(current, total)

    def test_pull_project_no_on_save_does_not_error(self):
        """pull_project without on_save should work without errors"""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        incoming_resources = deepcopy(project.resources)
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

        files_with_conflicts, _ = project.pull_project()
        self.assertEqual(files_with_conflicts, [])

    def test_pull_multi_resource_local_normalization_no_false_conflict(self):
        """Local multi-resource files should be normalised through resource classes
        before the three-way merge, so formatting differences don't cause conflicts.

        KeyphraseBoosting lowercases the level field in __init__. If the local file
        has 'level: Boosted' (mixed case), a raw read would differ from the canonical
        'level: boosted', causing a false merge conflict. Reading through the resource
        class normalises this.
        """
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

        incoming_resources = deepcopy(project.resources)
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

        # Local file has mixed-case level values (not yet normalised)
        local_keyphrases_yaml = (
            "keyphrases:\n"
            "- keyphrase: PolyAI\n"
            "  level: Maximum\n"
            "- keyphrase: reservation\n"
            "  level: Boosted\n"
            "- keyphrase: check-in\n"
            "  level: Default\n"
        )
        keyphrases_yaml_path = os.path.join(
            TEST_DIR, "voice", "speech_recognition", "keyphrase_boosting.yaml"
        )

        with mock_read_from_file({keyphrases_yaml_path: local_keyphrases_yaml}):
            files_with_conflicts, _ = project.pull_project(force=False)

        self.assertEqual(files_with_conflicts, [])


class PullProjectFromEnvTest(unittest.TestCase):
    """Tests for pull_project_from_env when targeting deployment environments.

    These tests verify that pull_project_from_env behaves correctly end-to-end.
    """

    def setUp(self):
        self.mock_get_remote = patch.object(
            AgentStudioProject,
            "get_remote_resources_by_name",
        ).start()
        self.mock_api_handler = patch.object(
            AgentStudioProject, "api_handler", new_callable=MagicMock
        ).start()
        self.mock_save_config = patch.object(AgentStudioProject, "save_config").start()
        self.mock_save_imports = patch("poly.utils.save_imports").start()
        self.mock_export_decorators = patch("poly.utils.export_decorators").start()
        self.mock_resource_save = patch.object(Resource, "save").start()
        self.mock_save_to_file = patch.object(Resource, "save_to_file").start()
        self.mock_os_remove = patch("os.remove").start()

    def tearDown(self):
        patch.stopall()

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def test_raises_when_no_active_deployment(self):
        """Empty resource map (e.g. live not yet deployed) raises with a clear message."""
        self.mock_get_remote.return_value = {}
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

        with self.assertRaises(ValueError) as ctx:
            project.pull_project_from_env(env="live", format=False)

        self.assertIn("No resources returned from environment 'live'", str(ctx.exception))
        self.mock_get_remote.assert_called_once_with("live")
        self.mock_save_config.assert_not_called()

    def test_raises_for_pre_release_when_not_deployed(self):
        """Same guard applies for pre-release, not just live."""
        self.mock_get_remote.return_value = {}
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

        with self.assertRaises(ValueError) as ctx:
            project.pull_project_from_env(env="pre-release")

        self.assertIn("No resources returned from environment 'pre-release'", str(ctx.exception))

    # ------------------------------------------------------------------
    # Correct env string forwarded
    # ------------------------------------------------------------------

    def test_calls_get_remote_with_correct_env(self):
        """get_remote_resources_by_name is invoked with the exact env string passed in."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        self.mock_get_remote.return_value = deepcopy(project.resources)

        project.pull_project_from_env(env="pre-release")

        self.mock_get_remote.assert_called_once_with("pre-release")

    # ------------------------------------------------------------------
    # Resource state after a successful pull
    # ------------------------------------------------------------------

    def test_no_changes_produces_no_conflicts(self):
        """Pulling when the deployment matches local resources produces no conflicts."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        original_resources = deepcopy(project.resources)
        incoming_resources = deepcopy(project.resources)
        self.mock_get_remote.return_value = incoming_resources

        files_with_conflicts = project.pull_project_from_env(env="live")

        self.assertEqual(files_with_conflicts, [])
        # Resources in memory are NOT updated — env pull only writes files
        self.assertEqual(project.resources, original_resources)
        self.mock_save_config.assert_not_called()

    def test_remote_modification_applied_to_disk(self):
        """A resource modified in the deployment snapshot is written to disk."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        original_resources = deepcopy(project.resources)
        incoming_resources = deepcopy(project.resources)
        func_id = "FUNCTION-test_function"
        modified_func = deepcopy(incoming_resources[Function][func_id])
        modified_func.code = 'def test_function(conv: Conversation):\n    """Modified in live."""\n    return "Live"\n'
        incoming_resources[Function][func_id] = modified_func
        self.mock_get_remote.return_value = incoming_resources

        files_with_conflicts = project.pull_project_from_env(env="live")

        self.assertEqual(files_with_conflicts, [])
        # In-memory resources unchanged; file was written to disk
        self.assertEqual(project.resources, original_resources)
        self.assertTrue(self.mock_save_to_file.called or self.mock_resource_save.called)

    def test_new_remote_resource_written_locally(self):
        """A resource present in the deployment but not locally is written to disk."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        incoming_resources = deepcopy(project.resources)
        new_topic = Topic(
            resource_id="TOPIC-live_only_topic",
            name="live_only_topic",
            actions="Use {{fn:test_function}}",
            content="Topic that only exists in live.",
            example_queries=["live query"],
        )
        incoming_resources.setdefault(Topic, {})["TOPIC-live_only_topic"] = new_topic
        self.mock_get_remote.return_value = incoming_resources

        files_with_conflicts = project.pull_project_from_env(env="live")

        self.assertEqual(files_with_conflicts, [])
        # In-memory resources unchanged; new resource was written to disk only
        self.assertNotIn("TOPIC-live_only_topic", project.resources.get(Topic, {}))
        self.assertTrue(self.mock_resource_save.called)

    # ------------------------------------------------------------------
    # Force-overwrite semantics (always on for pull_project_from_env)
    # ------------------------------------------------------------------

    def test_local_changes_overwritten_without_conflicts(self):
        """Local modifications are silently overwritten — force is always True."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        original_resources = deepcopy(project.resources)
        incoming_resources = deepcopy(project.resources)
        func_id = "FUNCTION-test_function"
        incoming_resources[Function][
            func_id
        ].code = 'def test_function(conv: Conversation):\n    return "From live"\n'
        self.mock_get_remote.return_value = incoming_resources

        files_with_conflicts = project.pull_project_from_env(env="pre-release")

        self.assertEqual(files_with_conflicts, [])
        # In-memory resources unchanged; file overwritten on disk
        self.assertEqual(project.resources, original_resources)
        self.assertTrue(self.mock_resource_save.called)

    def test_locally_added_resource_deleted_when_absent_from_deployment(self):
        """A locally-added resource absent from the deployment is deleted."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        incoming_resources = deepcopy(project.resources)
        if Topic in incoming_resources and "TOPIC-Topic 1" in incoming_resources[Topic]:
            del incoming_resources[Topic]["TOPIC-Topic 1"]
        self.mock_get_remote.return_value = incoming_resources

        files_with_conflicts = project.pull_project_from_env(env="live")

        self.assertEqual(files_with_conflicts, [])
        self.mock_os_remove.assert_called()
        # In-memory resources unchanged; deletion only affects disk
        self.assertIn("TOPIC-Topic 1", project.resources.get(Topic, {}))

    # ------------------------------------------------------------------
    # Side-effects: config + imports saved
    # ------------------------------------------------------------------

    def test_save_config_not_called_and_imports_saved_on_success(self):
        """save_config must NOT be called (env changes are local); save_imports is called."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        self.mock_get_remote.return_value = deepcopy(project.resources)

        project.pull_project_from_env(env="live")

        self.mock_save_config.assert_not_called()
        self.mock_save_imports.assert_called_once()

    def test_save_config_not_called_when_no_deployment(self):
        """save_config must not be called if the deployment lookup fails."""
        self.mock_get_remote.return_value = {}
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

        with self.assertRaises(ValueError):
            project.pull_project_from_env(env="live")

        self.mock_save_config.assert_not_called()


class GetDeploymentsTest(unittest.TestCase):
    """Tests for AgentStudioProject.get_deployments."""

    def setUp(self):
        self.mock_api_handler = patch.object(
            AgentStudioProject, "api_handler", new_callable=MagicMock
        ).start()
        self.mock_api_handler.get_active_deployments.return_value = {
            "sandbox": {"version": "abc123456xyz", "deployment_id": "dep-1"},
            "live": {"version": "def789012xyz", "deployment_id": "dep-2"},
        }
        self.mock_api_handler.get_deployments.return_value = [
            {"id": "dep-1", "version_hash": "abc123456xyz"},
            {"id": "dep-2", "version_hash": "def789012xyz"},
        ]

    def tearDown(self):
        patch.stopall()

    def test_raises_on_invalid_client_env(self):
        """get_deployments raises ValueError for an unrecognised client_env."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

        with self.assertRaises(ValueError) as ctx:
            project.get_deployments(client_env="production")

        self.assertIn("Invalid client environment", str(ctx.exception))

    def test_returns_deployments_and_active_hashes(self):
        """get_deployments returns the deployment list and active env hashes."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

        deployments, active_hashes = project.get_deployments(client_env="sandbox")

        self.assertEqual(len(deployments), 2)
        self.assertEqual(active_hashes["sandbox"], "abc123456xyz")
        self.assertEqual(active_hashes["live"], "def789012xyz")

    def test_passes_client_env_to_api(self):
        """get_deployments forwards client_env to the API handler."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

        project.get_deployments(client_env="live")

        self.mock_api_handler.get_deployments.assert_called_once()
        call_kwargs = self.mock_api_handler.get_deployments.call_args[1]
        self.assertEqual(call_kwargs["client_env"], "live")

    def test_accepts_all_valid_environments(self):
        """get_deployments accepts sandbox, pre-release, and live without raising."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

        for env in ("sandbox", "pre-release", "live"):
            with self.subTest(env=env):
                project.get_deployments(client_env=env)  # should not raise


class RevertChangesTest(unittest.TestCase):
    """Tests for AgentStudioProject.revert_changes."""

    def setUp(self):
        patch.object(Resource, "save_to_file").start()

    def tearDown(self):
        patch.stopall()

    def test_revert_all_returns_all_resource_paths(self):
        """revert_changes with no files reverts all resources and returns their paths."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        expected_count = len(project.all_resources)

        reverted = project.revert_changes()

        self.assertEqual(len(reverted), expected_count)
        for path in reverted:
            self.assertIsInstance(path, str)

    def test_revert_specific_file_only_reverts_that_file(self):
        """revert_changes with a specific file only reverts that file."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        target = project.all_resources[0].get_path(project.root_path)

        reverted = project.revert_changes(file_paths=[target])

        self.assertEqual(reverted, [target])

    def test_revert_unknown_file_reverts_nothing(self):
        """revert_changes with a path that matches no resource returns an empty list."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

        reverted = project.revert_changes(file_paths=["/nonexistent/path/file.yaml"])

        self.assertEqual(reverted, [])


class GetRemoteResourcesByNameLocalTest(unittest.TestCase):
    """Tests for the 'local' resolution mode of get_remote_resources_by_name."""

    def setUp(self):
        self.mock_api_handler = patch.object(
            AgentStudioProject, "api_handler", new_callable=MagicMock
        ).start()
        self.mock_api_handler.get_deployments.return_value = [
            {"id": "dep-1", "version_hash": "abc123456xyz"},
        ]
        self.mock_api_handler.get_active_deployments.return_value = {}

    def tearDown(self):
        patch.stopall()

    def test_local_returns_local_resources(self):
        """'local' should resolve to the current local filesystem state."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

        result = project.get_remote_resources_by_name("local")

        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)

    def test_local_resources_match_project_resources(self):
        """Resources returned for 'local' should have the same resource types as project.resources."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

        result = project.get_remote_resources_by_name("local")

        self.assertEqual(set(result.keys()), set(project.resources.keys()))

    def test_hash_lookup_tolerates_none_version_hash(self):
        """A deployment record with version_hash=None should not raise TypeError during hash lookup."""
        self.mock_api_handler.get_deployments.return_value = [
            {"id": "dep-1", "version_hash": None},
            {"id": "dep-2", "version_hash": "abc123456xyz"},
        ]
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

        # Should not raise — the None entry is skipped, abc123456 is found and used
        project.get_remote_resources_by_name("abc123456")


class DocsTest(unittest.TestCase):
    """Tests for the docs module"""

    def test_load_docs(self):
        """Test loading a docs file"""
        AgentStudioProject.load_docs("docs")


class GetUpdatedSubresourcesTest(unittest.TestCase):
    """A new resource's update-only sub-resources (e.g. TestCase assertions/tags)
    must be forwarded on create, not just `new` ones."""

    @staticmethod
    def _new_test_case() -> TestCase:
        rid = "TEST-greeting_flow"
        return TestCase(
            resource_id=rid,
            name="Greeting flow test",
            scenario="Ask for help with booking.",
            channel="chat.polyai",
            language="en-GB",
            assertions=TestCaseAssertion(
                resource_id=rid,
                name="assertions",
                prompts=["The agent offers to help with booking"],
                function_calls=[],
            ),
            tags=TestCaseTags(resource_id=rid, name="tags", tags=["booking"]),
        )

    def test_new_test_case_emits_assertions_and_tags(self):
        test_case = self._new_test_case()

        change_set = AgentStudioProject._get_updated_subresources(
            new_resources={TestCase: {test_case.resource_id: test_case}},
            updated_resources={},
            original_resources={},
        )

        # The assertions/tags of a brand-new case must be emitted as updates
        # (set_test_case_assertions / set_test_case_tags), not silently dropped.
        self.assertIn(TestCaseAssertion, change_set.updated)
        self.assertIn(test_case.resource_id, change_set.updated[TestCaseAssertion])
        self.assertEqual(
            change_set.updated[TestCaseAssertion][test_case.resource_id].prompts,
            ["The agent offers to help with booking"],
        )
        self.assertIn(TestCaseTags, change_set.updated)
        self.assertEqual(
            change_set.updated[TestCaseTags][test_case.resource_id].tags,
            ["booking"],
        )


class ResolveTestsTest(unittest.TestCase):
    """Tests for AgentStudioProject.resolve_tests."""

    def setUp(self):
        self.project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

    def test_default_returns_all_tests(self):
        """No filters returns all test cases."""
        result = self.project.resolve_tests()
        self.assertEqual(len(result), 2)
        names = {t.name for t in result}
        self.assertEqual(names, {"Greeting flow test", "Webchat smoke test"})

    def test_filter_by_single_tag(self):
        """Filtering by a tag only present on one test returns that test."""
        result = self.project.resolve_tests(tags=["booking"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "Greeting flow test")

    def test_filter_by_shared_tag(self):
        """Filtering by a tag shared across tests returns all matching tests."""
        result = self.project.resolve_tests(tags=["smoke"])
        self.assertEqual(len(result), 2)

    def test_filter_by_multiple_tags_is_or(self):
        """Passing multiple tags matches tests that have any of them."""
        result = self.project.resolve_tests(tags=["booking", "smoke"])
        self.assertEqual(len(result), 2)

    def test_filter_by_file_path(self):
        """Filtering by file_path matches the test with that path."""
        target = self.project.resolve_tests()[0]
        result = self.project.resolve_tests(files=[target.file_path])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].resource_id, target.resource_id)

    def test_unmatched_tag_raises(self):
        """A tag that matches nothing raises ValueError."""
        with self.assertRaises(ValueError, msg="No tests found"):
            self.project.resolve_tests(tags=["nonexistent"])

    def test_unmatched_file_raises(self):
        """A file path that matches nothing raises ValueError."""
        with self.assertRaises(ValueError, msg="No tests found"):
            self.project.resolve_tests(files=["no_such_test.yaml"])


class FetchProjectTest(unittest.TestCase):
    """Tests for the fetch_project method."""

    def setUp(self):
        """Set up common mocks — only api_handler and save_config, no file I/O mocks."""
        self.mock_api_handler = patch.object(
            AgentStudioProject, "api_handler", new_callable=MagicMock
        ).start()
        self.mock_save_config = patch.object(AgentStudioProject, "save_config").start()

    def tearDown(self):
        patch.stopall()

    def test_fetch_without_branch_updates_resources_and_returns_them(self):
        """fetch_project() without a branch fetches remote state and returns projection."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        expected_resources = deepcopy(project.resources)
        expected_projection = {"some": "projection"}
        self.mock_api_handler.pull_resources.return_value = (
            expected_resources,
            expected_projection,
        )
        self.mock_api_handler.branch_id = "remote-branch-id"

        projection = project.fetch_project()

        self.assertEqual(projection, expected_projection)
        self.assertEqual(project.resources, expected_resources)
        self.assertEqual(project._not_loaded_resources, [])
        self.mock_api_handler.pull_resources.assert_called_once_with(projection_json=None)

    def test_fetch_without_branch_updates_branch_id_from_api(self):
        """When no projection_json, branch_id should be updated from api_handler."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        self.mock_api_handler.pull_resources.return_value = (
            deepcopy(project.resources),
            {},
        )
        self.mock_api_handler.branch_id = "api-branch-42"

        project.fetch_project()

        self.assertEqual(project.branch_id, "api-branch-42")

    def test_fetch_with_valid_branch_switches_branch_then_fetches(self):
        """fetch_project(branch_name=...) switches to that branch before pulling."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        self.mock_api_handler.get_branches.return_value = {
            "main": {"branchId": "branch-1"},
            "dev": {"branchId": "branch-2"},
        }
        self.mock_api_handler.pull_resources.return_value = (
            deepcopy(project.resources),
            {},
        )
        self.mock_api_handler.branch_id = "branch-2"

        project.fetch_project(branch_name="dev")

        self.mock_api_handler.get_branches.assert_called_once()
        self.mock_api_handler.switch_branch.assert_called_once_with("branch-2")
        self.assertEqual(project.branch_id, "branch-2")

    def test_fetch_with_nonexistent_branch_raises_value_error(self):
        """fetch_project raises ValueError when the branch does not exist."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        self.mock_api_handler.get_branches.return_value = {"main": {"branchId": "branch-1"}}

        with self.assertRaises(ValueError, msg="Branch 'no-such-branch' does not exist."):
            project.fetch_project(branch_name="no-such-branch")

        self.mock_api_handler.pull_resources.assert_not_called()

    def test_fetch_with_projection_json_does_not_update_branch_id_from_api(self):
        """When projection_json is provided, branch_id should NOT be overwritten from API."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        original_branch_id = project.branch_id
        self.mock_api_handler.pull_resources.return_value = (
            deepcopy(project.resources),
            {"cached": True},
        )
        self.mock_api_handler.branch_id = "should-not-be-used"

        project.fetch_project(projection_json={"cached": "projection"})

        self.assertEqual(project.branch_id, original_branch_id)
        self.mock_api_handler.pull_resources.assert_called_once_with(
            projection_json={"cached": "projection"}
        )

    def test_fetch_calls_save_config(self):
        """fetch_project always calls save_config to persist the status file."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        self.mock_api_handler.pull_resources.return_value = (
            deepcopy(project.resources),
            {},
        )
        self.mock_api_handler.branch_id = "b"

        project.fetch_project()

        self.mock_save_config.assert_called_once()

    def test_fetch_does_not_write_resource_files(self):
        """fetch_project must not call Resource.save() — it only updates in-memory state."""
        mock_resource_save = patch.object(Resource, "save").start()
        mock_save_to_file = patch.object(Resource, "save_to_file").start()

        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        self.mock_api_handler.pull_resources.return_value = (
            deepcopy(project.resources),
            {},
        )
        self.mock_api_handler.branch_id = "b"

        project.fetch_project()

        mock_resource_save.assert_not_called()
        mock_save_to_file.assert_not_called()

    def test_fetch_updates_file_structure_info(self):
        """fetch_project should recompute file_structure_info from the new resources."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        new_resources = deepcopy(project.resources)
        self.mock_api_handler.pull_resources.return_value = (new_resources, {})
        self.mock_api_handler.branch_id = "b"

        project.fetch_project()

        expected_info = project.compute_file_structure_info(new_resources)
        self.assertEqual(project.file_structure_info, expected_info)

    def test_fetch_with_branch_sets_branch_id_before_api_override(self):
        """When both branch_name and no projection_json, branch_id ends up as api value."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        self.mock_api_handler.get_branches.return_value = {"staging": {"branchId": "staging-id"}}
        self.mock_api_handler.pull_resources.return_value = (
            deepcopy(project.resources),
            {},
        )
        # After pull, the api_handler.branch_id may differ from the branch dict value
        self.mock_api_handler.branch_id = "staging-id"

        project.fetch_project(branch_name="staging")

        # Since projection_json is None, branch_id is set from api_handler.branch_id
        self.assertEqual(project.branch_id, "staging-id")


class UpdatePulledResourcesDeleteAbsentTypesTest(unittest.TestCase):
    """Tests that _update_pulled_resources and _update_multi_resource_yaml_resources
    delete local resources when their entire resource type is absent from incoming."""

    def setUp(self):
        self.mock_api_handler = patch.object(
            AgentStudioProject, "api_handler", new_callable=MagicMock
        ).start()
        self.mock_save_config = patch.object(AgentStudioProject, "save_config").start()
        self.mock_save_imports = patch("poly.utils.save_imports").start()
        self.mock_export_decorators = patch("poly.utils.export_decorators").start()
        self.mock_resource_save = patch.object(Resource, "save").start()
        self.mock_save_to_file = patch.object(Resource, "save_to_file").start()
        self.mock_os_remove = patch("os.remove").start()

    def tearDown(self):
        patch.stopall()

    def test_absent_non_multi_resource_type_deleted_on_pull(self):
        """When incoming_resources omits an entire non-multi resource type (e.g. Topic),
        all local files for that type should be deleted."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        incoming_resources = deepcopy(project.resources)

        # Record the topic paths that exist locally before removal
        topic_paths = [res.get_path(TEST_DIR) for res in incoming_resources[Topic].values()]
        self.assertGreater(len(topic_paths), 0)

        # Remove Topics entirely from incoming — simulates remote having deleted all topics
        del incoming_resources[Topic]
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

        files_with_conflicts, _ = project.pull_project(force=False)

        self.assertEqual(files_with_conflicts, [])
        # Verify delete_resource was called (via os.remove) for each topic file
        removed_paths = [call[0][0] for call in self.mock_os_remove.call_args_list]
        for path in topic_paths:
            self.assertIn(
                path,
                removed_paths,
                f"Expected {path} to be deleted when Topic type is absent from incoming",
            )

    def test_absent_multi_resource_type_deleted_on_pull(self):
        """When incoming_resources omits an entire MultiResourceYamlResource type
        (e.g. Entity), delete_resource should be called for each local resource
        of that type."""
        project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        incoming_resources = deepcopy(project.resources)

        # Record entity paths before removal
        entity_paths = {res.get_path(TEST_DIR) for res in incoming_resources[Entity].values()}
        self.assertGreater(len(entity_paths), 0)

        # Remove Entities entirely from incoming — simulates remote having deleted all entities
        del incoming_resources[Entity]
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

        MultiResourceYamlResource._file_cache.clear()
        with patch.object(Entity, "delete_resource") as mock_delete:
            files_with_conflicts, _ = project.pull_project(force=False)
        MultiResourceYamlResource._file_cache.clear()

        self.assertEqual(files_with_conflicts, [])
        # Verify delete_resource was called for each entity
        deleted_paths = {call[0][0] for call in mock_delete.call_args_list}
        self.assertEqual(
            deleted_paths,
            entity_paths,
            "delete_resource should be called for every entity when Entity type is absent",
        )

    def test_not_loaded_resource_type_not_deleted_on_pull(self):
        """When a resource type is in _not_loaded_resources, it should NOT be deleted
        even if absent from incoming_resources. This prevents spurious deletions of
        types that were never loaded from the local status file."""
        # Load project without variant_attributes — simulates an older project format
        project_data = deepcopy(PROJECT_DATA)
        del project_data["resources"]["variant_attributes"]
        del project_data["resources"]["variants"]
        project = AgentStudioProject.from_dict(project_data, TEST_DIR)

        # Verify VariantAttribute is in _not_loaded_resources
        self.assertIn(VariantAttribute, project._not_loaded_resources)

        # Incoming also doesn't have VariantAttribute — but since it's "not loaded",
        # we should NOT delete local files for it
        incoming_resources = deepcopy(project.resources)
        self.mock_api_handler.pull_resources.return_value = (incoming_resources, {})

        files_with_conflicts, _ = project.pull_project(force=False)

        self.assertEqual(files_with_conflicts, [])
        # os.remove should NOT have been called for any variant attribute paths
        removed_paths = [call[0][0] for call in self.mock_os_remove.call_args_list]
        variant_attr_paths = [path for path in removed_paths if "variant_attribute" in path]
        self.assertEqual(
            variant_attr_paths,
            [],
            "Should not delete files for resource types in _not_loaded_resources",
        )


class MigrateFlowStepResourceIdsTest(unittest.TestCase):
    """Tests for migrate_flow_step_resource_ids status dict migration."""

    def test_rekeys_flow_steps_from_flow_name_to_flow_id(self):
        """Old-format keys are re-keyed using flow_id."""
        from poly.migration_utils import migrate_flow_step_resource_ids

        status_dict = {
            "resources": {
                "flow_steps": {
                    "SMS Flow_step-1": {
                        "resource_id": "SMS Flow_step-1",
                        "flow_name": "SMS Flow",
                        "flow_id": "FLOW-abc",
                    },
                },
                "function_steps": {
                    "SMS Flow_func-1": {
                        "resource_id": "SMS Flow_func-1",
                        "flow_name": "SMS Flow",
                        "flow_id": "FLOW-abc",
                    },
                },
            },
            "file_structure_info": {
                "flows/sms_flow/steps/step_1.yaml": {
                    "resource_id": "SMS Flow_step-1",
                },
                "flows/sms_flow/function_steps/func_1.py": {
                    "resource_id": "SMS Flow_func-1",
                },
            },
        }

        migrate_flow_step_resource_ids(status_dict)

        flow_steps = status_dict["resources"]["flow_steps"]
        self.assertNotIn("SMS Flow_step-1", flow_steps)
        self.assertIn("FLOW-abc_step-1", flow_steps)
        self.assertEqual(flow_steps["FLOW-abc_step-1"]["resource_id"], "FLOW-abc_step-1")

        func_steps = status_dict["resources"]["function_steps"]
        self.assertNotIn("SMS Flow_func-1", func_steps)
        self.assertIn("FLOW-abc_func-1", func_steps)
        self.assertEqual(func_steps["FLOW-abc_func-1"]["resource_id"], "FLOW-abc_func-1")

        fsi = status_dict["file_structure_info"]
        self.assertEqual(fsi["flows/sms_flow/steps/step_1.yaml"]["resource_id"], "FLOW-abc_step-1")
        self.assertEqual(
            fsi["flows/sms_flow/function_steps/func_1.py"]["resource_id"], "FLOW-abc_func-1"
        )

    def test_already_migrated_entries_are_unchanged(self):
        """Entries whose key doesn't start with flow_name_ are left as-is."""
        from poly.migration_utils import migrate_flow_step_resource_ids

        status_dict = {
            "resources": {
                "flow_steps": {
                    "FLOW-abc_step-1": {
                        "resource_id": "FLOW-abc_step-1",
                        "flow_name": "SMS Flow",
                        "flow_id": "FLOW-abc",
                    },
                },
            },
            "file_structure_info": {},
        }

        migrate_flow_step_resource_ids(status_dict)

        flow_steps = status_dict["resources"]["flow_steps"]
        self.assertIn("FLOW-abc_step-1", flow_steps)
        self.assertEqual(flow_steps["FLOW-abc_step-1"]["resource_id"], "FLOW-abc_step-1")


class SyncBranchProject(unittest.TestCase):
    """Tests for AgentStudioProject.sync_branch."""

    def setUp(self):
        self.project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

    def _make_branches(self, *branch_ids):
        """Build a branches dict with the given branch IDs."""
        return {bid: {"branchId": bid, "name": f"name-{bid}"} for bid in branch_ids}

    def test_branch_not_found_raises(self):
        """A branch_id not present in any branch metadata raises ValueError."""
        self.project.branch_id = "nonexistent-branch"
        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            mock_api.get_branches.return_value = self._make_branches("main", "branch-1")

            with self.assertRaises(ValueError) as ctx:
                self.project.sync_branch()

        self.assertIn("nonexistent-branch", str(ctx.exception))
        self.assertIn("does not exist", str(ctx.exception))

    def test_main_branch_raises(self):
        """Syncing the main branch raises ValueError."""
        self.project.branch_id = "main"
        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            mock_api.get_branches.return_value = self._make_branches("main")

            with self.assertRaises(ValueError) as ctx:
                self.project.sync_branch()

        self.assertIn("main", str(ctx.exception))
        self.assertIn("not supported", str(ctx.exception))

    def test_uncommitted_changes_raises(self):
        """Uncommitted changes (non-empty get_diffs) raises ValueError listing the diffs."""
        self.project.branch_id = "branch-1"
        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            mock_api.get_branches.return_value = self._make_branches("main", "branch-1")
            with patch.object(self.project, "get_diffs", return_value={"topic/foo": "modified"}):
                with self.assertRaises(ValueError) as ctx:
                    self.project.sync_branch()

        self.assertIn("uncommitted changes", str(ctx.exception))
        self.assertIn("topic/foo", str(ctx.exception))

    def test_invalid_resolution_missing_path(self):
        """A resolution dict missing 'path' raises ValueError."""
        self.project.branch_id = "branch-1"
        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            mock_api.get_branches.return_value = self._make_branches("main", "branch-1")
            with patch.object(self.project, "get_diffs", return_value=None):
                with self.assertRaises(ValueError) as ctx:
                    self.project.sync_branch(conflict_resolutions=[{"strategy": "ours"}])

        self.assertIn("path", str(ctx.exception))
        self.assertIn("strategy", str(ctx.exception))

    def test_invalid_resolution_missing_strategy(self):
        """A resolution dict missing 'strategy' raises ValueError."""
        self.project.branch_id = "branch-1"
        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            mock_api.get_branches.return_value = self._make_branches("main", "branch-1")
            with patch.object(self.project, "get_diffs", return_value=None):
                with self.assertRaises(ValueError) as ctx:
                    self.project.sync_branch(conflict_resolutions=[{"path": ["users", "name"]}])

        self.assertIn("path", str(ctx.exception))
        self.assertIn("strategy", str(ctx.exception))

    def test_invalid_resolution_bad_strategy(self):
        """A strategy not in {ours, theirs, base} raises ValueError."""
        self.project.branch_id = "branch-1"
        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            mock_api.get_branches.return_value = self._make_branches("main", "branch-1")
            with patch.object(self.project, "get_diffs", return_value=None):
                with self.assertRaises(ValueError) as ctx:
                    self.project.sync_branch(
                        conflict_resolutions=[{"path": ["users", "name"], "strategy": "invalid"}]
                    )

        self.assertIn("Invalid conflict resolution strategy", str(ctx.exception))
        self.assertIn("invalid", str(ctx.exception))

    def test_successful_sync_pulls_and_returns_true(self):
        """On success, pull_project(force=True) is called and (True, [], []) is returned."""
        self.project.branch_id = "branch-1"
        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            mock_api.get_branches.return_value = self._make_branches("main", "branch-1")
            mock_api.sync_branch.return_value = (True, [], [])
            with patch.object(self.project, "get_diffs", return_value=None):
                with patch.object(self.project, "pull_project") as mock_pull:
                    result = self.project.sync_branch()

        self.assertEqual(result, (True, [], []))
        mock_pull.assert_called_once_with(force=True)
        mock_api.sync_branch.assert_called_once_with(conflict_resolutions=None)

    def test_sync_with_conflicts_returns_false(self):
        """When the API reports conflicts, returns (False, conflicts, errors) without pulling."""
        self.project.branch_id = "branch-1"
        conflicts = [{"path": "topic/foo", "type": "content"}]
        errors = [{"message": "merge error"}]
        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            mock_api.get_branches.return_value = self._make_branches("main", "branch-1")
            mock_api.sync_branch.return_value = (False, conflicts, errors)
            with patch.object(self.project, "get_diffs", return_value=None):
                with patch.object(self.project, "pull_project") as mock_pull:
                    result = self.project.sync_branch()

        self.assertEqual(result, (False, conflicts, errors))
        mock_pull.assert_not_called()

    def test_none_resolutions_accepted(self):
        """Passing None for conflict_resolutions skips validation and works."""
        self.project.branch_id = "branch-1"
        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            mock_api.get_branches.return_value = self._make_branches("main", "branch-1")
            mock_api.sync_branch.return_value = (True, [], [])
            with patch.object(self.project, "get_diffs", return_value=None):
                with patch.object(self.project, "pull_project"):
                    result = self.project.sync_branch(conflict_resolutions=None)

        self.assertEqual(result, (True, [], []))
        mock_api.sync_branch.assert_called_once_with(conflict_resolutions=None)


class GetBranchHistoryProject(unittest.TestCase):
    """Tests for AgentStudioProject.get_branch_history."""

    def setUp(self):
        self.project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

    def test_delegates_to_api_handler(self):
        """get_branch_history passes through to the api_handler and returns its result."""
        expected = [{"commit_id": "c1"}, {"commit_id": "c2"}]
        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            mock_api.get_branch_history.return_value = expected

            result = self.project.get_branch_history("branch-1")

        self.assertEqual(result, expected)
        mock_api.get_branch_history.assert_called_once_with("branch-1")


class RenameBranchProject(unittest.TestCase):
    """Tests for AgentStudioProject.rename_branch."""

    def setUp(self):
        self.project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

    def test_empty_name_raises_value_error(self):
        """An empty branch name raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.project.rename_branch("")

        self.assertIn("New branch name must be provided", str(ctx.exception))

    def test_none_name_raises_value_error(self):
        """A None branch name raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.project.rename_branch(None)

        self.assertIn("New branch name must be provided", str(ctx.exception))

    def test_main_branch_raises_value_error(self):
        """Renaming the main branch raises ValueError."""
        self.project.branch_id = "main"

        with self.assertRaises(ValueError) as ctx:
            self.project.rename_branch("new-name")

        self.assertIn("main", str(ctx.exception))

    def test_duplicate_name_raises_value_error(self):
        """A name that already exists raises ValueError."""
        self.project.branch_id = "branch-1"
        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            mock_api.get_branches.return_value = {"new-name": "branch-id-123"}

            with self.assertRaises(ValueError) as ctx:
                self.project.rename_branch("new-name")

        self.assertIn("already exists", str(ctx.exception))

    def test_successful_rename_returns_true(self):
        """A valid rename delegates to api_handler and returns its result."""
        self.project.branch_id = "branch-1"
        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            mock_api.get_branches.return_value = {"other-branch": "id-456"}
            mock_api.rename_branch.return_value = True

            result = self.project.rename_branch("new-name")

        self.assertTrue(result)
        mock_api.rename_branch.assert_called_once_with(new_branch_name="new-name")


class ListArchivedBranchesProject(unittest.TestCase):
    """Tests for AgentStudioProject.list_archived_branches."""

    def setUp(self):
        self.project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

    def test_delegates_to_api_handler(self):
        """list_archived_branches passes through to the api_handler."""
        expected = [{"branchId": "b-1", "name": "old", "archivedAt": "2026-07-01"}]
        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            mock_api.list_archived_branches.return_value = expected

            result = self.project.list_archived_branches()

        self.assertEqual(result, expected)
        mock_api.list_archived_branches.assert_called_once()


class RestoreBranchProject(unittest.TestCase):
    """Tests for AgentStudioProject.restore_branch."""

    def setUp(self):
        self.project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)

    def test_empty_branch_id_raises_value_error(self):
        """An empty branch id raises ValueError before any API call."""
        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            with self.assertRaises(ValueError) as ctx:
                self.project.restore_branch("")

        self.assertIn("Branch id must be provided", str(ctx.exception))
        mock_api.restore_branch.assert_not_called()

    def test_restore_delegates_the_branch_id_to_the_api(self):
        """A branch id present in the archive is restored."""
        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            mock_api.list_archived_branches.return_value = [
                {"branchId": "BRANCH-1", "name": "old-branch"},
            ]
            mock_api.restore_branch.return_value = True

            result = self.project.restore_branch("BRANCH-1")

        self.assertTrue(result)
        mock_api.restore_branch.assert_called_once_with("BRANCH-1")

    def test_branch_id_not_in_archive_raises_value_error(self):
        """An id that is not archived is refused before any restore is attempted."""
        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            mock_api.list_archived_branches.return_value = [
                {"branchId": "BRANCH-1", "name": "old-branch"},
            ]

            with self.assertRaises(ValueError) as ctx:
                self.project.restore_branch("BRANCH-NOPE")

        self.assertIn("not found in archive", str(ctx.exception))
        mock_api.restore_branch.assert_not_called()

    def test_matching_is_by_id_not_name(self):
        """A branch name is not accepted, even when it is unique in the archive."""
        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            mock_api.list_archived_branches.return_value = [
                {"branchId": "BRANCH-1", "name": "old-branch"},
            ]

            with self.assertRaises(ValueError):
                self.project.restore_branch("old-branch")

        mock_api.restore_branch.assert_not_called()

    def test_api_failure_is_returned_to_the_caller(self):
        """A False from the API layer is passed through rather than raised."""
        with patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock) as mock_api:
            mock_api.list_archived_branches.return_value = [
                {"branchId": "BRANCH-1", "name": "old-branch"},
            ]
            mock_api.restore_branch.return_value = False

            self.assertFalse(self.project.restore_branch("BRANCH-1"))


class DiffBranchTest(unittest.TestCase):
    """Tests for the diff_branch method."""

    def setUp(self):
        self.project = AgentStudioProject.from_dict(deepcopy(PROJECT_DATA), TEST_DIR)
        self.mock_api = MagicMock()
        self.mock_api.branch_id = "main"
        self.project._api_handler = self.mock_api
        self.save_config_patcher = patch.object(AgentStudioProject, "save_config")
        self.save_config_patcher.start()

    def tearDown(self):
        self.save_config_patcher.stop()

    def _make_branches(self, entries):
        """Build a branches dict from a list of (name, branchId, extras) tuples."""
        branches = {}
        for name, branch_id, extras in entries:
            meta = {"branchId": branch_id}
            meta.update(extras)
            branches[name] = meta
        return branches

    def _make_topic(self, resource_id, name, content):
        """Create a Topic with all required fields."""
        return Topic(
            resource_id=resource_id,
            name=name,
            actions="",
            content=content,
            example_queries=[],
        )

    def test_on_main_with_no_branch_name_raises_value_error(self):
        """Calling diff_branch() while on main without specifying a branch raises ValueError."""
        self.project.branch_id = "main"
        self.mock_api.get_branches.return_value = self._make_branches([("main", "main", {})])

        with self.assertRaises(ValueError) as ctx:
            self.project.diff_branch()
        self.assertIn("Cannot diff main branch", str(ctx.exception))

    def test_named_branch_not_found_raises_value_error(self):
        """Specifying a branch name that doesn't exist raises ValueError."""
        self.mock_api.get_branches.return_value = self._make_branches(
            [("main", "main", {}), ("feature-a", "branch-a-id", {})]
        )

        with self.assertRaises(ValueError) as ctx:
            self.project.diff_branch(branch_name="nonexistent")
        self.assertIn("does not exist", str(ctx.exception))

    def test_happy_path_returns_diffs(self):
        """diff_branch returns diffs between fork-point parent and current branch state."""
        self.mock_api.get_branches.return_value = self._make_branches(
            [
                ("main", "main", {}),
                (
                    "feature-x",
                    "branch-x-id",
                    {"parentBranchId": "main", "parentSequence": "42"},
                ),
            ]
        )

        parent_topic = self._make_topic("TOPIC-1", "Greetings", "Hello original")
        branch_topic = self._make_topic("TOPIC-1", "Greetings", "Hello updated")
        parent_resources = {Topic: {"TOPIC-1": parent_topic}}
        branch_resources = {Topic: {"TOPIC-1": branch_topic}}

        self.mock_api.pull_branch_resources.side_effect = [
            parent_resources,
            branch_resources,
        ]

        diffs = self.project.diff_branch(branch_name="feature-x")

        self.assertIsNotNone(diffs)
        self.assertEqual(len(diffs), 1)
        topic_path = os.path.join("topics", "greetings.yaml")
        self.assertIn(topic_path, diffs)
        self.assertIn("-content: Hello original", diffs[topic_path])
        self.assertIn("+content: Hello updated", diffs[topic_path])

        # Verify pull_branch_resources called with correct args
        calls = self.mock_api.pull_branch_resources.call_args_list
        self.assertEqual(calls[0].args, ("main", 42))
        self.assertEqual(calls[1].args, ("branch-x-id",))

    def test_no_changes_returns_none(self):
        """When parent and branch have identical resources, diff_branch returns None."""
        self.mock_api.get_branches.return_value = self._make_branches(
            [
                ("main", "main", {}),
                (
                    "feature-y",
                    "branch-y-id",
                    {"parentBranchId": "main", "parentSequence": "10"},
                ),
            ]
        )

        topic = self._make_topic("TOPIC-1", "Hours", "9am-5pm")
        identical_resources = {Topic: {"TOPIC-1": topic}}

        self.mock_api.pull_branch_resources.side_effect = [
            identical_resources,
            deepcopy(identical_resources),
        ]

        result = self.project.diff_branch(branch_name="feature-y")
        self.assertIsNone(result)

    def test_null_parent_sequence_falls_back_to_latest(self):
        """When parentSequence is null, pull_branch_resources is called with at_sequence=None."""
        self.mock_api.get_branches.return_value = self._make_branches(
            [
                ("main", "main", {}),
                (
                    "feature-z",
                    "branch-z-id",
                    {"parentBranchId": "main", "parentSequence": None},
                ),
            ]
        )

        topic = self._make_topic("TOPIC-1", "Hours", "9am-5pm")
        self.mock_api.pull_branch_resources.side_effect = [
            {Topic: {"TOPIC-1": topic}},
            {Topic: {"TOPIC-1": deepcopy(topic)}},
        ]

        self.project.diff_branch(branch_name="feature-z")

        # Parent projection should be fetched with at_sequence=None (latest)
        parent_call = self.mock_api.pull_branch_resources.call_args_list[0]
        self.assertEqual(parent_call.args[0], "main")
        self.assertIsNone(parent_call.args[1])

    def test_file_path_filtering(self):
        """Only diffs matching the provided file_paths are returned."""
        self.mock_api.get_branches.return_value = self._make_branches(
            [
                ("main", "main", {}),
                (
                    "feature-f",
                    "branch-f-id",
                    {"parentBranchId": "main", "parentSequence": "5"},
                ),
            ]
        )

        topic_a = self._make_topic("TOPIC-A", "Topic A", "old A")
        topic_b = self._make_topic("TOPIC-B", "Topic B", "old B")
        parent_resources = {
            Topic: {"TOPIC-A": topic_a, "TOPIC-B": topic_b},
        }

        topic_a_new = self._make_topic("TOPIC-A", "Topic A", "new A")
        topic_b_new = self._make_topic("TOPIC-B", "Topic B", "new B")
        branch_resources = {
            Topic: {"TOPIC-A": topic_a_new, "TOPIC-B": topic_b_new},
        }

        self.mock_api.pull_branch_resources.side_effect = [
            parent_resources,
            branch_resources,
        ]

        topic_a_path = os.path.join("topics", "topic_a.yaml")
        diffs = self.project.diff_branch(branch_name="feature-f", file_paths=[topic_a_path])

        self.assertIsNotNone(diffs)
        self.assertIn(topic_a_path, diffs)
        topic_b_path = os.path.join("topics", "topic_b.yaml")
        self.assertNotIn(topic_b_path, diffs)

    def test_file_path_filtering_no_matches_returns_none(self):
        """When file_paths filter excludes all diffs, returns None."""
        self.mock_api.get_branches.return_value = self._make_branches(
            [
                ("main", "main", {}),
                (
                    "feature-g",
                    "branch-g-id",
                    {"parentBranchId": "main", "parentSequence": "5"},
                ),
            ]
        )

        topic = self._make_topic("TOPIC-1", "Hours", "old")
        topic_new = self._make_topic("TOPIC-1", "Hours", "new")

        self.mock_api.pull_branch_resources.side_effect = [
            {Topic: {"TOPIC-1": topic}},
            {Topic: {"TOPIC-1": topic_new}},
        ]

        result = self.project.diff_branch(
            branch_name="feature-g",
            file_paths=["nonexistent/file.yaml"],
        )
        self.assertIsNone(result)

    def test_current_branch_used_when_no_name_specified(self):
        """When no branch_name given, uses the current branch."""
        self.project.branch_id = "branch-cur-id"
        self.mock_api.branch_id = "branch-cur-id"
        self.mock_api.get_branches.return_value = self._make_branches(
            [
                ("main", "main", {}),
                (
                    "current-branch",
                    "branch-cur-id",
                    {"parentBranchId": "main", "parentSequence": "7"},
                ),
            ]
        )

        topic = self._make_topic("TOPIC-1", "FAQ", "same")
        self.mock_api.pull_branch_resources.side_effect = [
            {Topic: {"TOPIC-1": topic}},
            {Topic: {"TOPIC-1": deepcopy(topic)}},
        ]

        result = self.project.diff_branch()
        self.assertIsNone(result)

        # Should have used the current branch's metadata
        branch_call = self.mock_api.pull_branch_resources.call_args_list[1]
        self.assertEqual(branch_call.args, ("branch-cur-id",))


class GetBranchesReturnTypeTest(unittest.TestCase):
    """Tests for the updated get_branches return type (dict of metadata dicts)."""

    def setUp(self):
        self.project = AgentStudioProject.from_dict(deepcopy(PROJECT_DATA), TEST_DIR)
        self.mock_api = MagicMock()
        self.project._api_handler = self.mock_api
        self.save_config_patcher = patch.object(AgentStudioProject, "save_config")
        self.save_config_patcher.start()

    def tearDown(self):
        self.save_config_patcher.stop()

    def test_returns_current_branch_name_and_metadata_dict(self):
        """get_branches returns (current_name, {name: metadata_dict})."""
        self.project.branch_id = "branch-abc"
        self.mock_api.branch_id = "branch-abc"
        self.mock_api.get_branches.return_value = {
            "main": {"branchId": "main"},
            "my-feature": {"branchId": "branch-abc", "parentBranchId": "main"},
        }

        current_name, branches = self.project.get_branches()

        self.assertEqual(current_name, "my-feature")
        self.assertIn("main", branches)
        self.assertIn("my-feature", branches)
        self.assertEqual(branches["my-feature"]["branchId"], "branch-abc")
        self.assertEqual(branches["my-feature"]["parentBranchId"], "main")

    def test_returns_none_when_local_branch_not_found(self):
        """When the local branch_id doesn't match any remote branch, current_name is None."""
        self.project.branch_id = "deleted-branch-id"
        self.mock_api.get_branches.return_value = {
            "main": {"branchId": "main"},
        }

        current_name, branches = self.project.get_branches()

        self.assertIsNone(current_name)
        self.assertEqual(len(branches), 1)


class BranchTaggingTest(unittest.TestCase):
    """Tests for AgentStudioProject.tag_branch and untag_branch."""

    BRANCHES = {
        "main": {"branchId": "main"},
        "feature-a": {"branchId": "branch-a", "parentBranchId": "main"},
    }

    def setUp(self):
        self.project = AgentStudioProject.from_dict(deepcopy(PROJECT_DATA), TEST_DIR)
        self.mock_api = MagicMock()
        self.mock_api.get_branches.return_value = deepcopy(self.BRANCHES)
        self.mock_api.tag_branch.return_value = True
        self.mock_api.untag_branch.return_value = True
        self.project._api_handler = self.mock_api
        self.save_config_patcher = patch.object(AgentStudioProject, "save_config")
        self.save_config_patcher.start()
        self._set_current_branch("branch-a")

    def tearDown(self):
        self.save_config_patcher.stop()

    def _set_current_branch(self, branch_id: str) -> None:
        """Put the project and its API handler on the given branch.

        The ``api_handler`` property re-reads ``branch_id`` from the handler on
        every access, so both sides have to agree.
        """
        self.project.branch_id = branch_id
        self.mock_api.branch_id = branch_id

    def test_tags_current_branch_by_default(self):
        """With no branch name the current branch's id is tagged."""
        self.assertTrue(self.project.tag_branch())

        self.mock_api.tag_branch.assert_called_once_with("branch-a")

    def test_untags_current_branch_by_default(self):
        """With no branch name the current branch's id is untagged."""
        self.assertTrue(self.project.untag_branch())

        self.mock_api.untag_branch.assert_called_once_with("branch-a")

    def test_named_branch_is_resolved_to_its_id(self):
        """An explicit branch name is resolved to the branch id before the API call."""
        self._set_current_branch("main")

        self.project.tag_branch("feature-a")

        self.mock_api.tag_branch.assert_called_once_with("branch-a")

    def test_rejects_unknown_branch_name(self):
        """A name that is not in the branch list is refused before any API call."""
        for method in (self.project.tag_branch, self.project.untag_branch):
            with self.subTest(method=method.__name__):
                with self.assertRaises(ValueError) as ctx:
                    method("no-such-branch")

                self.assertIn("no-such-branch", str(ctx.exception))

        self.mock_api.tag_branch.assert_not_called()
        self.mock_api.untag_branch.assert_not_called()

    def test_rejects_current_branch_missing_from_branch_list(self):
        """A local branch id with no remote counterpart is reported rather than tagged."""
        self._set_current_branch("branch-gone")

        for method in (self.project.tag_branch, self.project.untag_branch):
            with self.subTest(method=method.__name__):
                with self.assertRaises(ValueError) as ctx:
                    method()

                self.assertIn("branch-gone", str(ctx.exception))

    def test_rejects_main_branch(self):
        """Main carries the live deployment, so it can be neither tagged nor untagged."""
        self._set_current_branch("main")

        with self.assertRaises(ValueError) as ctx:
            self.project.tag_branch()
        self.assertIn("Tagging 'main' branch is not supported", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            self.project.untag_branch()
        self.assertIn("Untagging 'main' branch is not supported", str(ctx.exception))

        self.mock_api.tag_branch.assert_not_called()
        self.mock_api.untag_branch.assert_not_called()

    def test_rejects_main_when_named_explicitly(self):
        """Naming main explicitly is refused the same way as being on it."""
        self._set_current_branch("branch-a")

        with self.assertRaises(ValueError):
            self.project.tag_branch("main")

        self.mock_api.tag_branch.assert_not_called()

    def test_api_failure_is_returned_to_the_caller(self):
        """A False from the API layer is passed through, not raised."""
        self.mock_api.tag_branch.return_value = False
        self.mock_api.untag_branch.return_value = False

        self.assertFalse(self.project.tag_branch())
        self.assertFalse(self.project.untag_branch())


class UsingSimplifiedDeploymentsTest(unittest.TestCase):
    """Tests for the AgentStudioProject.using_simplified_deployments property."""

    def setUp(self):
        self.project = AgentStudioProject.from_dict(deepcopy(PROJECT_DATA), TEST_DIR)
        self.mock_api = MagicMock()
        self.mock_api.branch_id = "main"
        self.mock_api.feature_flag_enabled.return_value = True
        self.project._api_handler = self.mock_api
        self.save_config_patcher = patch.object(AgentStudioProject, "save_config")
        self.save_config_patcher.start()

    def tearDown(self):
        self.save_config_patcher.stop()

    def _build_project(self, flag_value: bool) -> AgentStudioProject:
        """Build a fresh project whose flag resolves to the given value.

        A fresh instance is required per value because the property is cached.
        """
        project = AgentStudioProject.from_dict(deepcopy(PROJECT_DATA), TEST_DIR)
        api = MagicMock()
        api.branch_id = "main"
        api.feature_flag_enabled.return_value = flag_value
        project._api_handler = api
        return project

    def test_reads_the_deployment_simplification_flag_for_this_project(self):
        """The flag is looked up by key and scoped to the project's region and id."""
        self.assertTrue(self.project.using_simplified_deployments)

        self.mock_api.feature_flag_enabled.assert_called_once_with(
            key="deployment-simplification",
            region=self.project.region,
            project_id=self.project.project_id,
            default=False,
        )

    def test_defaults_to_disabled_when_the_flag_cannot_be_read(self):
        """`default=False` is passed so an unreachable PostHog gates the new commands off."""
        self.project.using_simplified_deployments

        self.assertFalse(self.mock_api.feature_flag_enabled.call_args.kwargs["default"])

    def test_returns_the_flag_value(self):
        """Whatever the flag resolves to is what the property reports."""
        for value in (True, False):
            with self.subTest(value=value):
                project = self._build_project(value)

                self.assertEqual(project.using_simplified_deployments, value)

    def test_flag_is_evaluated_once_and_cached(self):
        """Repeated reads reuse the cached value instead of re-evaluating the flag."""
        first = self.project.using_simplified_deployments
        second = self.project.using_simplified_deployments

        self.assertEqual(first, second)
        self.mock_api.feature_flag_enabled.assert_called_once()

    def test_does_not_query_deployments_when_flag_is_disabled(self):
        """Deployments are only fetched once the feature flag is confirmed enabled."""
        project = self._build_project(flag_value=False)

        self.assertFalse(project.using_simplified_deployments)
        project.api_handler.get_deployments.assert_not_called()

    def _deployment(self, created_at: str, deleted: bool = False) -> dict:
        """Build a minimal deployment dict for convergence checks."""
        return {"created_at": created_at, "deleted": deleted}

    def _set_deployments(self, api: MagicMock, live: list, sandbox: list) -> None:
        """Stub get_deployments to return a different list per client_env."""
        api.get_deployments.side_effect = (
            lambda *args, **kwargs: live if kwargs["client_env"] == "live" else sandbox
        )

    def test_converges_when_no_deployments_exist_in_either_environment(self):
        """With no deployments anywhere, there's nothing for live to lag behind."""
        self._set_deployments(self.mock_api, live=[], sandbox=[])

        self.assertTrue(self.project.using_simplified_deployments)

    def test_convergence_depends_on_relative_head_timestamps(self):
        """Live is converged once its head is at least as new as sandbox's."""
        earlier, later = "Mon, 01 Jan 2026 10:00:00 GMT", "Mon, 01 Jan 2026 12:00:00 GMT"
        cases = {
            "live newer": ((later, earlier), True),
            "equal": ((later, later), True),
            "live older": ((earlier, later), False),
            "only live has deployments": ((earlier, None), True),
            "only sandbox has deployments": ((None, earlier), False),
        }
        for name, ((live_time, sandbox_time), expected) in cases.items():
            with self.subTest(name):
                live = [self._deployment(live_time)] if live_time else []
                sandbox = [self._deployment(sandbox_time)] if sandbox_time else []
                self._set_deployments(self.mock_api, live=live, sandbox=sandbox)
                self.project.__dict__.pop("using_simplified_deployments", None)

                self.assertEqual(self.project.using_simplified_deployments, expected)

    def test_skips_deleted_deployments_to_find_the_head(self):
        """A deleted deployment at the top of the list is not treated as the head."""
        self._set_deployments(
            self.mock_api,
            live=[
                self._deployment("Mon, 01 Jan 2026 14:00:00 GMT", deleted=True),
                self._deployment("Mon, 01 Jan 2026 10:00:00 GMT"),
            ],
            sandbox=[self._deployment("Mon, 01 Jan 2026 12:00:00 GMT")],
        )

        # The live head (10:00, ignoring the deleted 14:00 entry) is older than sandbox's (12:00).
        self.assertFalse(self.project.using_simplified_deployments)


class DeploymentModePropertyTest(unittest.TestCase):
    """Tests for the AgentStudioProject.deployment_mode property."""

    def setUp(self):
        self.project = AgentStudioProject.from_dict(deepcopy(PROJECT_DATA), TEST_DIR)
        self.mock_api = MagicMock()
        self.mock_api.branch_id = "main"
        self.project._api_handler = self.mock_api
        self.save_config_patcher = patch.object(AgentStudioProject, "save_config")
        self.save_config_patcher.start()

    def tearDown(self):
        self.save_config_patcher.stop()

    def test_reads_mode_from_remote_project_config(self):
        """Each recognised config value maps to the matching enum member."""
        for value, expected in (
            ("simple", DeploymentMode.SIMPLE),
            ("releases", DeploymentMode.RELEASES),
            ("releases_branches", DeploymentMode.RELEASES_BRANCHES),
        ):
            with self.subTest(value=value):
                self.project._deployment_mode = None
                self.mock_api.get_project.return_value = {"config": {"deployment_mode": value}}

                self.assertEqual(self.project.deployment_mode, expected)

    def test_defaults_to_releases_when_config_missing(self):
        """A missing 'config', missing 'deployment_mode', or null config all default to releases."""
        for payload in (
            {"projectId": "test_project"},
            {"config": {"other_setting": True}},
            {"config": None},
        ):
            with self.subTest(payload=payload):
                self.project._deployment_mode = None
                self.mock_api.get_project.return_value = payload

                self.assertEqual(self.project.deployment_mode, DeploymentMode.RELEASES)

    def test_mode_is_fetched_once_and_cached(self):
        """Repeated reads reuse the cached mode instead of re-querying the API."""
        self.mock_api.get_project.return_value = {"config": {"deployment_mode": "simple"}}

        first = self.project.deployment_mode
        second = self.project.deployment_mode

        self.assertEqual(first, second)
        self.mock_api.get_project.assert_called_once()


class CreateBranchDeploymentModeTest(unittest.TestCase):
    """Tests for the deployment-mode guards in AgentStudioProject.create_branch."""

    def setUp(self):
        self.project = AgentStudioProject.from_dict(deepcopy(PROJECT_DATA), TEST_DIR)
        self.mock_api = MagicMock()
        self.mock_api.create_branch.return_value = "new-branch-id"
        self.project._api_handler = self.mock_api
        self.save_config_patcher = patch.object(AgentStudioProject, "save_config")
        self.mock_save_config = self.save_config_patcher.start()
        self._set_current_branch("main")

    def tearDown(self):
        self.save_config_patcher.stop()

    def _set_deployment_mode(self, mode: str) -> None:
        """Make the remote project report the given deployment mode."""
        self.mock_api.get_project.return_value = {"config": {"deployment_mode": mode}}

    def _set_current_branch(self, branch_id: str) -> None:
        """Put the project and its API handler on the given branch."""
        self.project.branch_id = branch_id
        self.mock_api.branch_id = branch_id

    # -- simple mode: at most one branch may exist at a time --

    def test_simple_mode_creates_branch_when_only_main_exists(self):
        """In simple mode a branch can be created while main is the only branch."""
        self._set_deployment_mode("simple")
        self._set_current_branch("main")
        self.mock_api.get_branches.return_value = {"main": {"branchId": "main"}}

        new_branch_id = self.project.create_branch("my-feature")

        self.assertEqual(new_branch_id, "new-branch-id")
        self.mock_api.create_branch.assert_called_once_with("my-feature", "main")
        self.assertEqual(self.project.branch_id, "new-branch-id")
        self.mock_save_config.assert_called()

    def test_simple_mode_rejects_second_branch(self):
        """In simple mode a second branch is refused while another branch exists."""
        self._set_deployment_mode("simple")
        self._set_current_branch("main")
        self.mock_api.get_branches.return_value = {
            "main": {"branchId": "main"},
            "existing": {"branchId": "branch-existing", "parentBranchId": "main"},
        }

        with self.assertRaises(ValueError) as ctx:
            self.project.create_branch("my-feature")

        self.assertIn("simple deployment mode", str(ctx.exception))
        self.mock_api.create_branch.assert_not_called()
        self.assertEqual(self.project.branch_id, "main")

    # -- releases mode: branches may only be created from main --

    def test_releases_mode_creates_branch_from_main(self):
        """In releases mode main is a valid source branch."""
        self._set_deployment_mode("releases")
        self._set_current_branch("main")

        new_branch_id = self.project.create_branch("my-feature")

        self.assertEqual(new_branch_id, "new-branch-id")
        self.mock_api.create_branch.assert_called_once_with("my-feature", "main")
        self.assertEqual(self.project.branch_id, "new-branch-id")

    def test_releases_mode_rejects_non_main_source_branch(self):
        """In releases mode creating a branch from another branch is refused."""
        self._set_deployment_mode("releases")
        self._set_current_branch("branch-feature-a")

        with self.assertRaises(ValueError) as ctx:
            self.project.create_branch("my-feature")

        self.assertIn("releases deployment mode", str(ctx.exception))
        self.mock_api.create_branch.assert_not_called()
        self.assertEqual(self.project.branch_id, "branch-feature-a")

    # -- releases_branches mode: source branch must be a direct child of main --

    def test_releases_branches_mode_creates_branch_from_direct_child_of_main(self):
        """A branch whose parent is main may be used as the source branch."""
        self._set_deployment_mode("releases_branches")
        self._set_current_branch("branch-feature-a")
        self.mock_api.get_branches.return_value = {
            "main": {"branchId": "main"},
            "feature-a": {"branchId": "branch-feature-a", "parentBranchId": "main"},
        }

        new_branch_id = self.project.create_branch("my-feature")

        self.assertEqual(new_branch_id, "new-branch-id")
        self.mock_api.create_branch.assert_called_once_with("my-feature", "branch-feature-a")
        self.assertEqual(self.project.branch_id, "new-branch-id")
        self.mock_save_config.assert_called()

    def test_releases_branches_mode_rejects_grandchild_of_main(self):
        """A branch whose parent is not main is too deep to branch from again."""
        self._set_deployment_mode("releases_branches")
        self._set_current_branch("branch-feature-a-child")
        self.mock_api.get_branches.return_value = {
            "main": {"branchId": "main"},
            "feature-a": {"branchId": "branch-feature-a", "parentBranchId": "main"},
            "feature-a-child": {
                "branchId": "branch-feature-a-child",
                "parentBranchId": "branch-feature-a",
            },
        }

        with self.assertRaises(ValueError) as ctx:
            self.project.create_branch("my-feature")

        self.assertIn("depth", str(ctx.exception))
        self.mock_api.create_branch.assert_not_called()

    def test_releases_branches_mode_rejects_branch_missing_from_remote(self):
        """A local branch that no longer exists remotely cannot be branched from."""
        self._set_deployment_mode("releases_branches")
        self._set_current_branch("branch-deleted")
        self.mock_api.get_branches.return_value = {"main": {"branchId": "main"}}

        with self.assertRaises(ValueError):
            self.project.create_branch("my-feature")

        self.mock_api.create_branch.assert_not_called()

    def test_releases_branches_mode_creates_branch_from_main(self):
        """Main itself may be used as the source branch, even though it has no parent."""
        self._set_deployment_mode("releases_branches")
        self._set_current_branch("main")
        self.mock_api.get_branches.return_value = {"main": {"branchId": "main", "name": "main"}}

        new_branch_id = self.project.create_branch("my-feature")

        self.assertEqual(new_branch_id, "new-branch-id")
        self.mock_api.create_branch.assert_called_once_with("my-feature", "main")
        self.assertEqual(self.project.branch_id, "new-branch-id")
        self.mock_save_config.assert_called()

    # -- source_branch_name: create from a branch other than the current one --

    def test_named_source_branch_overrides_the_current_branch(self):
        """Passing source_branch_name resolves that branch's id and validates against it,
        not against whatever branch the user currently has checked out."""
        self._set_deployment_mode("releases_branches")
        self._set_current_branch("branch-feature-a")
        self.mock_api.get_branches.return_value = {
            "main": {"branchId": "main", "name": "main"},
            "feature-a": {"branchId": "branch-feature-a", "parentBranchId": "main"},
            "feature-b": {"branchId": "branch-feature-b", "parentBranchId": "main"},
        }

        new_branch_id = self.project.create_branch("my-feature", source_branch_name="feature-b")

        self.assertEqual(new_branch_id, "new-branch-id")
        self.mock_api.create_branch.assert_called_once_with("my-feature", "branch-feature-b")
        self.assertEqual(self.project.branch_id, "new-branch-id")

    def test_unknown_source_branch_is_rejected_without_creating(self):
        """Naming a branch that does not exist remotely fails before anything is created."""
        self._set_deployment_mode("releases_branches")
        self._set_current_branch("branch-feature-a")
        self.mock_api.get_branches.return_value = {"main": {"branchId": "main"}}

        with self.assertRaises(ValueError) as ctx:
            self.project.create_branch("my-feature", source_branch_name="no-such-branch")

        self.assertEqual(str(ctx.exception), "Branch 'no-such-branch' does not exist.")
        self.mock_api.create_branch.assert_not_called()
        self.assertEqual(self.project.branch_id, "branch-feature-a")

    def test_deployment_mode_guards_validate_the_named_source_not_the_current_branch(self):
        """The same per-mode guards apply, but keyed off source_branch_name when given."""
        branches = {
            "main": {"branchId": "main", "name": "main"},
            "feature-a": {"branchId": "branch-feature-a", "parentBranchId": "main"},
            "feature-b": {"branchId": "branch-feature-b", "parentBranchId": "main"},
            "feature-b-child": {
                "branchId": "branch-feature-b-child",
                "parentBranchId": "branch-feature-b",
            },
        }
        cases = {
            "releases allows main by name from elsewhere": ("releases", "main", None),
            "releases rejects a named non-main source": (
                "releases",
                "feature-b",
                "releases deployment mode",
            ),
            "releases_branches rejects a named grandchild of main": (
                "releases_branches",
                "feature-b-child",
                "depth",
            ),
        }
        for description, (mode, source_branch_name, expected_error) in cases.items():
            with self.subTest(description):
                self.project._deployment_mode = None  # deployment_mode caches on first access
                self._set_deployment_mode(mode)
                self._set_current_branch("branch-feature-a")
                self.mock_api.get_branches.return_value = branches
                self.mock_api.create_branch.reset_mock()

                if expected_error:
                    with self.assertRaises(ValueError) as ctx:
                        self.project.create_branch(
                            "my-feature", source_branch_name=source_branch_name
                        )
                    self.assertIn(expected_error, str(ctx.exception))
                    self.mock_api.create_branch.assert_not_called()
                else:
                    self.project.create_branch("my-feature", source_branch_name=source_branch_name)
                    self.mock_api.create_branch.assert_called_once_with("my-feature", "main")


class MergeBranchTest(unittest.TestCase):
    """Tests for AgentStudioProject.merge_branch."""

    def setUp(self):
        self.project = AgentStudioProject.from_dict(deepcopy(PROJECT_DATA), TEST_DIR)
        self.mock_api = MagicMock()
        self.mock_api.merge_branch.return_value = (True, [], [])
        self.project._api_handler = self.mock_api
        self.save_config_patcher = patch.object(AgentStudioProject, "save_config")
        self.mock_save_config = self.save_config_patcher.start()
        # merge_branch refuses to run with uncommitted changes; default to a clean tree.
        self.get_diffs_patcher = patch.object(AgentStudioProject, "get_diffs", return_value={})
        self.mock_get_diffs = self.get_diffs_patcher.start()
        # A successful merge switches to the parent branch; assert on the call, don't sync.
        self.switch_branch_patcher = patch.object(
            AgentStudioProject, "switch_branch", return_value=(True, {})
        )
        self.mock_switch_branch = self.switch_branch_patcher.start()

    def tearDown(self):
        patch.stopall()

    def _set_current_branch(self, branch_id: str) -> None:
        """Put the project and its API handler on the given branch."""
        self.project.branch_id = branch_id
        self.mock_api.branch_id = branch_id

    def test_merging_direct_child_of_main_switches_to_main(self):
        """A branch whose parent is main lands the user back on main after merging."""
        self._set_current_branch("branch-feature-a")
        self.mock_api.get_branches.return_value = {
            "main": {"branchId": "main", "name": "main"},
            "feature-a": {
                "branchId": "branch-feature-a",
                "name": "feature-a",
                "parentBranchId": "main",
            },
        }

        result = self.project.merge_branch("ship it")

        self.assertEqual(result, (True, [], []))
        self.mock_api.merge_branch.assert_called_once_with(
            message="ship it", conflict_resolutions=None
        )
        self.mock_switch_branch.assert_called_once_with("main", force=True)

    def test_merging_with_unresolvable_parent_falls_back_to_main(self):
        """If parentBranchId is missing/unresolvable, the merge still succeeds and lands on main."""
        self._set_current_branch("branch-feature-a")
        self.mock_api.get_branches.return_value = {
            "main": {"branchId": "main", "name": "main"},
            "feature-a": {
                "branchId": "branch-feature-a",
                "name": "feature-a",
                # No parentBranchId — simulates a branch created before lineage tracking existed.
            },
        }

        result = self.project.merge_branch("ship it")

        self.assertEqual(result, (True, [], []))
        self.mock_switch_branch.assert_called_once_with("main", force=True)

    def test_merging_grandchild_switches_to_its_parent_branch(self):
        """A branch nested under a release branch lands on that release branch, not main."""
        self._set_current_branch("branch-feature-a")
        self.mock_api.get_branches.return_value = {
            "main": {"branchId": "main", "name": "main"},
            "Release 1": {
                "branchId": "branch-release-1",
                "name": "Release 1",
                "parentBranchId": "main",
            },
            "feature-a": {
                "branchId": "branch-feature-a",
                "name": "feature-a",
                "parentBranchId": "branch-release-1",
            },
        }

        result = self.project.merge_branch("ship it")

        self.assertEqual(result, (True, [], []))
        self.mock_switch_branch.assert_called_once_with("Release 1", force=True)

    def test_failed_merge_returns_conflicts_and_stays_on_branch(self):
        """When the platform reports a failure, conflicts pass through and no switch happens."""
        self._set_current_branch("branch-feature-a")
        self.mock_api.get_branches.return_value = {
            "main": {"branchId": "main", "name": "main"},
            "feature-a": {
                "branchId": "branch-feature-a",
                "name": "feature-a",
                "parentBranchId": "main",
            },
        }
        conflicts = [{"path": ["flows", "f1", "name"], "oursValue": "a", "theirsValue": "b"}]
        errors = [{"path": ["flows", "f1"], "message": "boom"}]
        self.mock_api.merge_branch.return_value = (False, conflicts, errors)

        success, returned_conflicts, returned_errors = self.project.merge_branch("ship it")

        self.assertFalse(success)
        self.assertEqual(returned_conflicts, conflicts)
        self.assertEqual(returned_errors, errors)
        self.mock_switch_branch.assert_not_called()

    def test_merging_from_main_is_rejected(self):
        """Main has nothing to merge into, so merging from it is refused."""
        self._set_current_branch("main")
        self.mock_api.get_branches.return_value = {"main": {"branchId": "main", "name": "main"}}

        with self.assertRaises(ValueError) as ctx:
            self.project.merge_branch("ship it")

        self.assertIn("main", str(ctx.exception))
        self.mock_api.merge_branch.assert_not_called()

    def test_merging_branch_missing_from_remote_is_rejected(self):
        """A local branch that no longer exists remotely cannot be merged."""
        self._set_current_branch("branch-deleted")
        self.mock_api.get_branches.return_value = {"main": {"branchId": "main", "name": "main"}}

        with self.assertRaises(ValueError) as ctx:
            self.project.merge_branch("ship it")

        self.assertIn("branch-deleted", str(ctx.exception))
        self.mock_api.merge_branch.assert_not_called()

    def test_merging_with_uncommitted_changes_is_rejected(self):
        """Local edits must be pushed before merging."""
        self._set_current_branch("branch-feature-a")
        self.mock_api.get_branches.return_value = {
            "main": {"branchId": "main", "name": "main"},
            "feature-a": {
                "branchId": "branch-feature-a",
                "name": "feature-a",
                "parentBranchId": "main",
            },
        }
        self.mock_get_diffs.return_value = {"flows/my_flow.yaml": "some diff"}

        with self.assertRaises(ValueError) as ctx:
            self.project.merge_branch("ship it")

        self.assertIn("uncommitted", str(ctx.exception))
        self.mock_api.merge_branch.assert_not_called()

    def test_conflict_resolution_without_strategy_is_rejected(self):
        """Every conflict resolution must say how the conflict should be resolved."""
        self._set_current_branch("branch-feature-a")
        self.mock_api.get_branches.return_value = {
            "main": {"branchId": "main", "name": "main"},
            "feature-a": {
                "branchId": "branch-feature-a",
                "name": "feature-a",
                "parentBranchId": "main",
            },
        }

        with self.assertRaises(ValueError) as ctx:
            self.project.merge_branch("ship it", conflict_resolutions=[{"path": ["flows", "f1"]}])

        self.assertIn("strategy", str(ctx.exception))
        self.mock_api.merge_branch.assert_not_called()

    def test_conflict_resolution_with_unknown_strategy_is_rejected(self):
        """Only 'ours', 'theirs', and 'base' are valid resolution strategies."""
        self._set_current_branch("branch-feature-a")
        self.mock_api.get_branches.return_value = {
            "main": {"branchId": "main", "name": "main"},
            "feature-a": {
                "branchId": "branch-feature-a",
                "name": "feature-a",
                "parentBranchId": "main",
            },
        }

        with self.assertRaises(ValueError) as ctx:
            self.project.merge_branch(
                "ship it",
                conflict_resolutions=[{"path": ["flows", "f1"], "strategy": "mine"}],
            )

        self.assertIn("mine", str(ctx.exception))
        self.mock_api.merge_branch.assert_not_called()


class RtcPullEnvTest(unittest.TestCase):
    """Tests for AgentStudioProject.rtc_pull_env writing RTC files to disk."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project = AgentStudioProject.from_dict(deepcopy(EMPTY_PROJECT_DATA), self.temp_dir)
        self.env_dir = os.path.join(self.temp_dir, "real_time_configuration", "draft_and_sandbox")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _read_json(self, file_name: str) -> object:
        with open(os.path.join(self.env_dir, file_name), "r", encoding="utf-8") as f:
            return json.load(f)

    def test_pull_env_writes_schema_and_data_returned_by_api(self):
        """Schema and variables from the API are written to schema.json and data.json."""
        config = {
            "schema": {"type": "object", "properties": {"flag": {"type": "boolean"}}},
            "variables": {"flag": True},
            "lastUpdated": "2026-01-01T00:00:00Z",
        }

        with patch.object(AgentStudioProject, "rtc_fetch_config", return_value=config):
            result = self.project.rtc_pull_env("sandbox")

        self.assertEqual(result["environment"], "sandbox")
        self.assertEqual(self._read_json("schema.json"), config["schema"])
        self.assertEqual(self._read_json("data.json"), config["variables"])

    def test_pull_env_writes_empty_dicts_when_api_returns_null(self):
        """A project with no RTC configured writes {} to disk, never literal null.

        The API returns explicit JSON null (not a missing key) for schema/variables when
        RTC has never been configured, and null is not valid content for these files.
        """
        config = {"schema": None, "variables": None, "lastUpdated": "2026-01-01T00:00:00Z"}

        with patch.object(AgentStudioProject, "rtc_fetch_config", return_value=config):
            self.project.rtc_pull_env("sandbox")

        self.assertEqual(self._read_json("schema.json"), {})
        self.assertEqual(self._read_json("data.json"), {})

    def test_pull_env_metadata_records_empty_dicts_when_api_returns_null(self):
        """The stored baseline metadata is {} rather than being left unset on null."""
        config = {"schema": None, "variables": None, "lastUpdated": "2026-01-01T00:00:00Z"}

        with patch.object(AgentStudioProject, "rtc_fetch_config", return_value=config):
            self.project.rtc_pull_env("sandbox")

        self.assertEqual(self.project.rtc_metadata["sandbox"]["base_schema"], {})
        self.assertEqual(self.project.rtc_metadata["sandbox"]["base_data"], {})
        self.assertEqual(
            self.project.rtc_metadata["sandbox"]["last_updated"], "2026-01-01T00:00:00Z"
        )

    def test_pull_env_null_config_round_trips_through_rtc_load_local(self):
        """Files written from a null API response can be read back as empty dicts."""
        config = {"schema": None, "variables": None, "lastUpdated": "2026-01-01T00:00:00Z"}

        with patch.object(AgentStudioProject, "rtc_fetch_config", return_value=config):
            self.project.rtc_pull_env("sandbox")

        loaded = self.project.rtc_load_local("sandbox")

        self.assertEqual(loaded, {"schema": {}, "variables": {}})

    def test_pull_env_schema_only_does_not_write_data_file(self):
        """schema_only writes schema.json and leaves data.json absent."""
        config = {"schema": {"type": "object"}, "variables": {"flag": True}, "lastUpdated": "T1"}

        with patch.object(AgentStudioProject, "rtc_fetch_config", return_value=config):
            result = self.project.rtc_pull_env("sandbox", schema_only=True)

        self.assertNotIn("data_file", result)
        self.assertTrue(os.path.exists(os.path.join(self.env_dir, "schema.json")))
        self.assertFalse(os.path.exists(os.path.join(self.env_dir, "data.json")))


class SyncIdsWithSandboxTest(unittest.TestCase):
    """Tests for sync_ids_with_sandbox adopting sandbox resource ids."""

    LOCAL_FLOW_ID = "FLOW_CONFIG-test_flow"
    SANDBOX_FLOW_ID = "FLOW-sandbox-assigned-id"

    def setUp(self):
        self.project = AgentStudioProject.from_dict(deepcopy(PROJECT_DATA), TEST_DIR)
        self.project.branch_id = "branch-1"
        self.mock_api = MagicMock()
        self.mock_api.branch_id = "branch-1"
        self.mock_api.send_queued_commands.return_value = True
        self.project._api_handler = self.mock_api
        patch.object(AgentStudioProject, "save_config").start()
        self.addCleanup(patch.stopall)

    def _sandbox_resources_with_reassigned_flow_id(self, without_start_step: bool = False):
        """Sandbox resources identical to local, except test_flow has a different flow id.

        Mirrors a flow that was created on main after the branch was cut: the files are the
        same, but the platform assigned the flow a new id, so the sandbox steps carry a
        `{sandbox_flow_id}_{step_id}` composite resource id.

        Args:
            without_start_step: omit the start step from the sandbox, so it looks like a
                step added on this branch with no sandbox counterpart.
        """
        sandbox = deepcopy(self.project.resources)
        for resource_type, resources_by_id in sandbox.items():
            rekeyed = {}
            for resource in resources_by_id.values():
                if isinstance(resource, FlowConfig) and resource.resource_id == self.LOCAL_FLOW_ID:
                    resource.resource_id = self.SANDBOX_FLOW_ID
                elif getattr(resource, "flow_id", None) == self.LOCAL_FLOW_ID:
                    if without_start_step and resource.resource_id.endswith("_start_step"):
                        continue
                    resource.flow_id = self.SANDBOX_FLOW_ID
                    resource.resource_id = resource.resource_id.replace(
                        self.LOCAL_FLOW_ID, self.SANDBOX_FLOW_ID, 1
                    )
                rekeyed[resource.resource_id] = resource
            sandbox[resource_type] = rekeyed
        return sandbox

    def test_start_step_is_bare_step_id_when_sandbox_reassigned_the_flow_id(self):
        """The synced flow config's start_step keeps only the step id, with no flow id prefix.

        start_step is stored as a name locally and resolved back to an id by stripping the
        flow id prefix off the step's composite resource id. If the mapping's flow_id is the
        stale local one while the step id has already moved to the sandbox flow id, nothing
        is stripped and the platform rejects the flow with "Start step ID does not exist".
        """
        sandbox_resources = self._sandbox_resources_with_reassigned_flow_id()

        with patch.object(
            AgentStudioProject, "get_remote_resources_by_name", return_value=sandbox_resources
        ):
            self.assertTrue(self.project.sync_ids_with_sandbox())

        synced_flow = self.project.resources[FlowConfig][self.SANDBOX_FLOW_ID]
        self.assertEqual(synced_flow.start_step, "start_step")

    def test_start_step_is_bare_step_id_when_the_start_step_is_new_on_the_branch(self):
        """A start step with no sandbox counterpart is still re-pointed at the synced flow id.

        A step added on the branch keeps its `{local_flow_id}_{step_id}` id, so if only
        flow_id is translated the prefix and flow_id disagree and the flow id stays welded
        onto start_step exactly as it did in the unfixed case.
        """
        sandbox_resources = self._sandbox_resources_with_reassigned_flow_id(
            without_start_step=True
        )

        with patch.object(
            AgentStudioProject, "get_remote_resources_by_name", return_value=sandbox_resources
        ):
            self.assertTrue(self.project.sync_ids_with_sandbox())

        synced_flow = self.project.resources[FlowConfig][self.SANDBOX_FLOW_ID]
        self.assertEqual(synced_flow.start_step, "start_step")

    def test_branch_only_step_is_rekeyed_onto_the_sandbox_flow_id(self):
        """A step added on the branch adopts the sandbox flow id in its composite id."""
        sandbox_resources = self._sandbox_resources_with_reassigned_flow_id(
            without_start_step=True
        )

        with patch.object(
            AgentStudioProject, "get_remote_resources_by_name", return_value=sandbox_resources
        ):
            self.project.sync_ids_with_sandbox()

        steps = self.project.resources[FlowStep]
        self.assertIn(f"{self.SANDBOX_FLOW_ID}_start_step", steps)
        self.assertNotIn(f"{self.LOCAL_FLOW_ID}_start_step", steps)
        # No step is left straddling the two flow ids.
        self.assertEqual(
            [
                step.resource_id
                for step in steps.values()
                if step.flow_id == self.SANDBOX_FLOW_ID
                and not step.resource_id.startswith(f"{self.SANDBOX_FLOW_ID}_")
            ],
            [],
        )

    def test_two_flows_reassigned_at_once_do_not_contaminate_each_other(self):
        """Each flow's steps are re-keyed onto their own flow's synced id.

        `FLOW_CONFIG-test_flow` is a string prefix of `FLOW_CONFIG-test_flow_with_punctuation`,
        so a rewrite that matched flow ids by substring rather than per-resource could strip
        the wrong prefix and move one flow's steps under the other.
        """
        other_local_id = "FLOW_CONFIG-test_flow_with_punctuation"
        other_sandbox_id = "FLOW-sandbox-other-id"
        renames = {self.LOCAL_FLOW_ID: self.SANDBOX_FLOW_ID, other_local_id: other_sandbox_id}

        sandbox = deepcopy(self.project.resources)
        for resource_type, resources_by_id in sandbox.items():
            rekeyed = {}
            for resource in resources_by_id.values():
                if isinstance(resource, FlowConfig) and resource.resource_id in renames:
                    resource.resource_id = renames[resource.resource_id]
                elif getattr(resource, "flow_id", None) in renames:
                    old_flow_id = resource.flow_id
                    resource.flow_id = renames[old_flow_id]
                    if resource.resource_id.startswith(f"{old_flow_id}_"):
                        resource.resource_id = (
                            f"{resource.flow_id}_"
                            f"{resource.resource_id.removeprefix(f'{old_flow_id}_')}"
                        )
                rekeyed[resource.resource_id] = resource
            sandbox[resource_type] = rekeyed

        with patch.object(
            AgentStudioProject, "get_remote_resources_by_name", return_value=sandbox
        ):
            self.assertTrue(self.project.sync_ids_with_sandbox())

        self.assertEqual(
            self.project.resources[FlowConfig][self.SANDBOX_FLOW_ID].start_step, "start_step"
        )
        self.assertEqual(
            self.project.resources[FlowConfig][other_sandbox_id].start_step, "welcome_step"
        )
        # Every step sits under its own flow's synced id, with a matching composite prefix.
        for step in self.project.resources[FlowStep].values():
            if step.flow_id in renames.values():
                self.assertTrue(
                    step.resource_id.startswith(f"{step.flow_id}_"),
                    f"{step.resource_id} does not sit under its flow {step.flow_id}",
                )

    def test_flow_scoped_function_ids_are_not_rewritten(self):
        """Flow-scoped functions keep their ids: only composite step ids embed the flow id.

        A Function belonging to a flow carries a flow_id but its resource_id
        (`FUNCTION-process_data`) does not embed it. Prepending the synced flow id to such
        an id would corrupt it, so the rewrite must apply only to composite ids.
        """
        sandbox_resources = self._sandbox_resources_with_reassigned_flow_id()
        flow_scoped_function_ids = {
            function.resource_id
            for function in self.project.resources[Function].values()
            if getattr(function, "flow_id", None) == self.LOCAL_FLOW_ID
        }
        self.assertTrue(flow_scoped_function_ids, "fixture must have flow-scoped functions")

        with patch.object(
            AgentStudioProject, "get_remote_resources_by_name", return_value=sandbox_resources
        ):
            self.project.sync_ids_with_sandbox()

        synced_function_ids = set(self.project.resources[Function])
        self.assertTrue(flow_scoped_function_ids <= synced_function_ids)
        self.assertEqual(
            [rid for rid in synced_function_ids if rid.startswith(f"{self.SANDBOX_FLOW_ID}_")],
            [],
        )

    def test_flow_and_steps_adopt_sandbox_ids(self):
        """Both the flow config and its steps are re-keyed onto the sandbox flow id."""
        sandbox_resources = self._sandbox_resources_with_reassigned_flow_id()

        with patch.object(
            AgentStudioProject, "get_remote_resources_by_name", return_value=sandbox_resources
        ):
            self.project.sync_ids_with_sandbox()

        self.assertIn(self.SANDBOX_FLOW_ID, self.project.resources[FlowConfig])
        self.assertNotIn(self.LOCAL_FLOW_ID, self.project.resources[FlowConfig])

        start_step = self.project.resources[FlowStep][f"{self.SANDBOX_FLOW_ID}_start_step"]
        self.assertEqual(start_step.flow_id, self.SANDBOX_FLOW_ID)

    def test_ids_unchanged_when_sandbox_ids_already_match(self):
        """A sandbox whose ids already match the branch leaves local resource ids alone."""
        with patch.object(
            AgentStudioProject,
            "get_remote_resources_by_name",
            return_value=deepcopy(self.project.resources),
        ):
            self.assertTrue(self.project.sync_ids_with_sandbox())

        self.assertIn(self.LOCAL_FLOW_ID, self.project.resources[FlowConfig])
        self.assertEqual(
            self.project.resources[FlowConfig][self.LOCAL_FLOW_ID].start_step, "start_step"
        )

    def test_raises_on_main_branch(self):
        """Syncing ids while on main is not allowed."""
        self.project.branch_id = "main"

        with self.assertRaises(ValueError) as ctx:
            self.project.sync_ids_with_sandbox()
        self.assertIn("Cannot sync ids while on main branch", str(ctx.exception))

    def test_raises_when_there_are_uncommitted_changes(self):
        """Uncommitted local changes must be committed before ids can be synced."""
        with patch.object(
            AgentStudioProject, "get_diffs", return_value={"topics/topic_1.yaml": "a diff"}
        ):
            with self.assertRaises(ValueError) as ctx:
                self.project.sync_ids_with_sandbox()
        self.assertIn("uncommitted changes", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
