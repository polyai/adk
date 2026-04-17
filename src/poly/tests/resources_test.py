"""Unit tests for ADK Resources

Copyright PolyAI Limited
"""

import os
import unittest

import yaml
from jsonschema import ValidationError

from poly.resources.agent_settings import (
    SettingsPersonality,
    SettingsRole,
    SettingsRules,
)
from poly.resources.api_integration import (
    AVAILABLE_AUTH_TYPES,
    AVAILABLE_OPERATIONS,
    URL_PATTERN,
    ApiIntegration,
    ApiIntegrationConfig,
    ApiIntegrationEnvironments,
    ApiIntegrationOperation,
)
from poly.resources.asr_settings import AsrSettings
from poly.resources.safety_filters import (
    ChatSafetyFilters,
    SafetyFilters,
    VoiceSafetyFilters,
    _SafetyFilterCategory,
    parse_categories_from_azure_config,
)
from poly.resources.channel_settings import (
    ChatGreeting,
    ChatStylePrompt,
    VoiceDisclaimerMessage,
    VoiceGreeting,
    VoiceStylePrompt,
)
from poly.resources.entities import Entity, EntityType
from poly.resources.experimental_config import ExperimentalConfig
from poly.resources.flows import (
    ASRBiasing,
    Condition,
    ConditionType,
    DTMFConfig,
    FlowConfig,
    FlowStep,
    FunctionStep,
    StepType,
)
from poly.resources.function import (
    Function,
    FunctionDelayResponse,
    FunctionLatencyControl,
    FunctionParameters,
    FunctionType,
)
from poly.resources.handoff import Handoff
from poly.resources.keyphrase_boosting import KeyphraseBoosting
from poly.resources.phrase_filter import PhraseFilter
from poly.resources.pronunciation import Pronunciation
from poly.resources.resource import MultiResourceYamlResource, ResourceMapping
from poly.resources.sms import EnvPhoneNumbers, SMSTemplate
from poly.resources.topic import (
    FUNCTION_REGEX,
    Topic,
)
from poly.handlers.sync_client import SyncClientHandler
from poly.resources.transcript_correction import RegularExpressionRule, TranscriptCorrection
from poly.resources.variable import Variable
from poly.resources.variant_attributes import Variant, VariantAttribute
from poly.tests.testing_utils import mock_read_from_file, mock_variant_attributes_file

TEST_CODE = """import random

@utils.test_decorator
def test_code(conv: Conversation, test_param: int):
    print(random.randint(1, test_param))
"""

TEST_CODE_RAW = """import random

@func_description('A test function')
@func_parameter('test_param', 'test parameter')
@utils.test_decorator
def test_code(conv: Conversation, test_param: int):
    print(random.randint(1, test_param))
"""

TEST_CODE_PRETTY = """from _gen import *  # <AUTO GENERATED>
import random

@func_description('A test function')
@func_parameter('test_param', 'test parameter')
@utils.test_decorator
def test_code(conv: Conversation, test_param: int):
    print(random.randint(1, test_param))
"""

TEST_FUNCTION = Function(
    resource_id="123",
    name="test_code",
    description="A test function",
    code=TEST_CODE,
    parameters=[
        FunctionParameters(
            name="test_param", description="test parameter", type="integer"
        )
    ],
    latency_control=FunctionLatencyControl(),
    flow_id=None,
    function_type=None,
)


class FunctionTests(unittest.TestCase):
    def test_get_raw(self):
        self.assertEqual(TEST_FUNCTION.raw, TEST_CODE_RAW)

    def test_to_pretty(self):
        pretty_code = TEST_FUNCTION.to_pretty(resource_mappings=[])
        self.assertEqual(
            pretty_code,
            TEST_CODE_PRETTY,
        )

    def test_to_pretty_import_after_docstring(self):
        function_with_docstring = Function(
            resource_id="123",
            name="test_code",
            description="A test function",
            code='"""This is a docstring."""\n\n' + TEST_CODE,
            parameters=[
                FunctionParameters(
                    name="test_param", description="test parameter", type="integer"
                )
            ],
            latency_control=FunctionLatencyControl(),
            flow_id=None,
            function_type=None,
        )
        pretty_code = function_with_docstring.to_pretty(resource_mappings=[])
        expected_code = '"""This is a docstring."""\n' + TEST_CODE_PRETTY
        self.assertEqual(pretty_code, expected_code)

    def test_to_pretty_convert_flow_import(self):
        function_code = """import random
from functions.flow_id.flow_utils import helper_function

def test_code(conv: Conversation, flow: Flow, test_param: int):
    print(random.randint(1, test_param))
"""

        expected_pretty_code = """from _gen import *  # <AUTO GENERATED>
import random
from flows.flow_name.functions.flow_utils import helper_function

def test_code(conv: Conversation, flow: Flow, test_param: int):
    print(random.randint(1, test_param))
"""

        resource_mappings = [
            ResourceMapping(
                resource_id="flow_id",
                resource_name="Flow Name",
                resource_type=FlowConfig,
                file_path="flows/flow_name/flow_config.yaml",
                flow_name="Flow Name",
                resource_prefix=None,
            )
        ]

        pretty_code = Function.make_pretty(
            function_code, resource_mappings=resource_mappings
        )
        self.assertEqual(pretty_code, expected_pretty_code)

    def test_convert_and_unconvert_code(self):
        converted_code = TEST_FUNCTION.to_pretty(resource_mappings=[])
        reverted_code = TEST_FUNCTION.from_pretty(converted_code, resource_mappings=[])
        self.assertNotEqual(reverted_code, TEST_FUNCTION.code)

        # NOTE: For local representation, we add decorators to denote things like:
        # Function Description
        # Function Parameters
        # Latency Control
        self.assertEqual(reverted_code, TEST_CODE_RAW)

    def test_validate_function_code(self):
        test_function = Function(
            resource_id="",
            name="test_code",
            description="Test description",
            code=TEST_CODE,
            parameters=[
                {
                    "name": "test_param",
                    "type": "integer",
                    "description": "A test parameter",
                }
            ],
            latency_control=FunctionLatencyControl(),
            function_type=FunctionType.GLOBAL,
        )
        self.assertIsNone(test_function.validate())

        # Test with missing function description
        test_function.description = ""
        with self.assertRaises(ValueError) as cm:
            test_function.validate()
        self.assertIn("Function description cannot be empty", str(cm.exception))
        test_function.description = "Test description"

        # Test with a syntax error
        test_function.code = "print('hel\n"
        with self.assertRaises(ValueError) as cm:
            test_function.validate()
        self.assertIn("Syntax error in function code", str(cm.exception))

        # Test with a missing function definition
        test_function.code = "print('Hello World')"

        with self.assertRaises(ValueError) as cm:
            test_function.validate()
        self.assertIn(
            "Function definition 'def test_code(conv: Conversation, "
            "test_param: int)' not found in code",
            str(cm.exception),
        )

        # Test flow_id handling
        test_function.flow_id = "test_flow"
        test_function.function_type = FunctionType.TRANSITION
        test_function.code = (
            "def test_code(conv: Conversation, flow: Flow, test_param: int):\n"
            "    print(random.randint(1, test_param))"
        )
        self.assertIsNone(test_function.validate())

        # Test with missing flow_id for transition function
        test_function.flow_id = None
        with self.assertRaises(ValueError) as cm:
            test_function.validate()
        self.assertIn("Can't find flow_id for transition function.", str(cm.exception))

        # Test with wrong parameter type
        test_function.parameters = [
            FunctionParameters(
                name="test_param",
                type="string",
                description="A test parameter",
            )
        ]
        with self.assertRaises(ValueError) as cm:
            test_function.validate()
        self.assertIn(
            "Function definition 'def test_code(conv: Conversation, "
            "flow: Flow, test_param: str)' not found in code",
            str(cm.exception),
        )

        # Test with ADK decorators in raw code
        test_function.function_type = FunctionType.GLOBAL
        test_function.code = "@func_description('A test function')\n@func_parameter('test_param', 'test parameter')\n@utils.test_decorator\ndef test_code(conv: Conversation, test_param: str):\n    print(random.randint(1, test_param))"
        with self.assertRaises(ValueError) as cm:
            test_function.validate()
        self.assertIn(
            "ADK decorators found in raw code. This might be because of a parameter mismatch.",
            str(cm.exception),
        )

    def test_read_local_resource(self):
        test_file_pretty_content = """from _gen import *  # <AUTO GENERATED>
import random


def another_function():
    pass

@func_description('A test function')
@func_parameter('test_param', 'test parameter')
@utils.test_decorator
def test_code(conv: Conversation, test_param: int):
    print(random.randint(1, test_param))
"""

        test_file_true_content = """import random


def another_function():
    pass

@utils.test_decorator
def test_code(conv: Conversation, test_param: int):
    print(random.randint(1, test_param))
"""

        with mock_read_from_file(test_file_pretty_content):
            result = Function.read_local_resource(
                file_path="functions/test_code.py",
                resource_id="func-123",
                resource_name="test_code",
                resource_mappings=[],
                known_parameters=[
                    FunctionParameters(
                        id="param-123",
                        name="test_param",
                        description="test parameter",
                        type="integer",
                    )
                ],
                known_latency_control=FunctionLatencyControl(),
            )

            self.assertEqual(result.function_type, FunctionType.GLOBAL)
            self.assertEqual(result.resource_id, "func-123")
            self.assertEqual(result.name, "test_code")
            self.assertEqual(result.description, "A test function")
            self.assertEqual(result.code, test_file_true_content)
            self.assertEqual(
                result.parameters,
                [
                    FunctionParameters(
                        id="param-123",
                        name="test_param",
                        description="test parameter",
                        type="integer",
                    )
                ],
            )

    def test_read_local_resource_flow_function(self):
        test_file_pretty_content = """from _gen import *  # <AUTO GENERATED>
import random

@func_description('A test function')
@func_parameter('test_param', 'test parameter')
@func_parameter('another_param', 'another parameter')
@utils.test_decorator
def test_code(conv: Conversation, flow: Flow, test_param: int, another_param: str):
    print(random.randint(1, test_param))
"""

        test_file_true_content = """import random

@utils.test_decorator
def test_code(conv: Conversation, flow: Flow, test_param: int, another_param: str):
    print(random.randint(1, test_param))
"""

        with mock_read_from_file(test_file_pretty_content):
            result = Function.read_local_resource(
                file_path="flows/flow_1/functions/test_code.py",
                resource_id="func-123",
                resource_name="test_code",
                resource_mappings=[
                    ResourceMapping(
                        resource_id="flow_1",
                        resource_name="Flow 1",
                        resource_type=FlowConfig,
                        file_path="flows/flow_1/flow_config.yaml",
                        flow_name="Flow 1",
                        resource_prefix=None,
                    )
                ],
                known_parameters=[
                    FunctionParameters(
                        id="param-123",
                        name="test_param",
                        description="test parameter",
                        type="integer",
                    ),
                    FunctionParameters(
                        id="param-456",
                        name="another_param",
                        description="another parameter",
                        type="string",
                    ),
                ],
                known_latency_control=FunctionLatencyControl(),
            )

            self.assertEqual(result.function_type, FunctionType.TRANSITION)
            self.assertEqual(result.resource_id, "func-123")
            self.assertEqual(result.name, "test_code")
            self.assertEqual(result.description, "A test function")
            self.assertEqual(result.code, test_file_true_content)
            self.assertEqual(
                result.parameters,
                [
                    FunctionParameters(
                        id="param-123",
                        name="test_param",
                        description="test parameter",
                        type="integer",
                    ),
                    FunctionParameters(
                        id="param-456",
                        name="another_param",
                        description="another parameter",
                        type="string",
                    ),
                ],
            )
            self.assertEqual(result.flow_id, "flow_1")
            self.assertEqual(result.flow_name, "Flow 1")

    def test_read_local_resource_start_function(self):
        # Example of how to use the mock_read_from_file context manager
        test_file_pretty_content = """from _gen import *  # <AUTO GENERATED>
import random

def start_function(conv: Conversation, test_param: int):
    print(random.randint(1, test_param))
"""

        with mock_read_from_file(test_file_pretty_content):
            result = Function.read_local_resource(
                file_path="functions/start_function.py",
                resource_id="func-123",
                resource_name="start_function",
                resource_mappings=[],
                known_parameters=[
                    FunctionParameters(
                        id="param-123",
                        name="test_param",
                        description="test parameter",
                        type="integer",
                    )
                ],
                known_latency_control=FunctionLatencyControl(),
            )

            self.assertEqual(result.function_type, FunctionType.START)

    def test_read_local_resource_end_function(self):
        test_file_pretty_content = """from _gen import *  # <AUTO GENERATED>
import random

def end_function(conv: Conversation, test_param: int):
    print(random.randint(1, test_param))
"""

        with mock_read_from_file(test_file_pretty_content):
            result = Function.read_local_resource(
                file_path="functions/end_function.py",
                resource_id="func-123",
                resource_name="end_function",
                resource_mappings=[],
                known_parameters=[
                    FunctionParameters(
                        id="param-123",
                        name="test_param",
                        description="test parameter",
                        type="integer",
                    )
                ],
                known_latency_control=FunctionLatencyControl(),
            )

            self.assertEqual(result.function_type, FunctionType.END)

    # ------------------------------------------------------------------
    # Latency-control decorator tests
    # ------------------------------------------------------------------

    def test_raw_includes_latency_control_decorator(self):
        """When latency_control.enabled is True, @func_latency_control appears in raw."""
        func = Function(
            resource_id="123",
            name="test_code",
            description="A test function",
            code=TEST_CODE,
            parameters=[],
            latency_control=FunctionLatencyControl(
                enabled=True,
                initial_delay=5000,
                interval=3000,
                delay_responses=[
                    FunctionDelayResponse(message="Please hold...", duration=5000),
                    FunctionDelayResponse(message="Still looking...", duration=8000),
                ],
            ),
            function_type=FunctionType.GLOBAL,
        )
        raw = func.raw
        self.assertIn("@func_latency_control(", raw)
        self.assertIn("delay_before_responses_start=5000", raw)
        self.assertIn("silence_after_each_response=3000", raw)
        self.assertIn("('Please hold...', 5000)", raw)
        self.assertIn("('Still looking...', 8000)", raw)

    def test_raw_omits_latency_control_when_disabled(self):
        """When latency_control.enabled is False, no decorator is rendered."""
        func = Function(
            resource_id="123",
            name="test_code",
            description="A test function",
            code=TEST_CODE,
            parameters=[
                FunctionParameters(
                    name="test_param", description="test parameter", type="integer"
                )
            ],
            latency_control=FunctionLatencyControl(enabled=False),
            function_type=FunctionType.GLOBAL,
        )
        raw = func.raw
        self.assertNotIn("@func_latency_control", raw)

    def test_extract_latency_control_decorator(self):
        """_extract_decorators parses @func_latency_control and strips it."""
        code_with_decorator = """@func_latency_control(delay_before_responses_start=5000, silence_after_each_response=3000, delay_responses=[('Hold on...', 5000)])
def my_func(conv: Conversation):
    pass
"""
        code, params, desc, lc = Function._extract_decorators(
            code_with_decorator, "my_func", []
        )
        self.assertTrue(lc.enabled)
        self.assertEqual(lc.initial_delay, 5000)
        self.assertEqual(lc.interval, 3000)
        self.assertEqual(len(lc.delay_responses), 1)
        self.assertEqual(lc.delay_responses[0].message, "Hold on...")
        self.assertEqual(lc.delay_responses[0].duration, 5000)
        # Decorator should be stripped from code
        self.assertNotIn("func_latency_control", code)

    def test_extract_preserves_known_delay_response_ids(self):
        """Existing delay-response IDs are preserved by message match."""
        code_with_decorator = """@func_latency_control(delay_before_responses_start=1000, silence_after_each_response=2000, delay_responses=[('Hold on...', 5000)])
def my_func(conv: Conversation):
    pass
"""
        known_lc = FunctionLatencyControl(
            enabled=True,
            initial_delay=1000,
            interval=2000,
            delay_responses=[
                FunctionDelayResponse(id="DELAY-existing", message="Hold on...", duration=5000),
            ],
        )
        _, _, _, lc = Function._extract_decorators(
            code_with_decorator, "my_func", [], known_lc
        )
        self.assertEqual(lc.delay_responses[0].id, "DELAY-existing")

    def test_latency_control_roundtrip(self):
        """to_pretty -> from_pretty -> _extract_decorators round-trip."""
        lc = FunctionLatencyControl(
            enabled=True,
            initial_delay=4000,
            interval=2000,
            delay_responses=[
                FunctionDelayResponse(id="DR-1", message="One moment...", duration=4000),
                FunctionDelayResponse(id="DR-2", message="Almost there...", duration=6000),
            ],
        )
        func = Function(
            resource_id="123",
            name="test_code",
            description="A test function",
            code=TEST_CODE,
            parameters=[
                FunctionParameters(
                    name="test_param", description="test parameter", type="integer"
                )
            ],
            latency_control=lc,
            function_type=FunctionType.GLOBAL,
        )
        pretty = func.to_pretty(resource_mappings=[])
        reverted = Function.from_pretty(pretty, resource_mappings=[])
        code, params, desc, extracted_lc = Function._extract_decorators(
            reverted, "test_code", [], lc
        )
        self.assertTrue(extracted_lc.enabled)
        self.assertEqual(extracted_lc.initial_delay, 4000)
        self.assertEqual(extracted_lc.interval, 2000)
        self.assertEqual(len(extracted_lc.delay_responses), 2)
        self.assertEqual(extracted_lc.delay_responses[0].message, "One moment...")
        self.assertEqual(extracted_lc.delay_responses[1].message, "Almost there...")
        # IDs are preserved
        self.assertEqual(extracted_lc.delay_responses[0].id, "DR-1")
        self.assertEqual(extracted_lc.delay_responses[1].id, "DR-2")

    def test_read_local_resource_with_latency_control(self):
        """read_local_resource correctly extracts latency control from file."""
        test_file_content = """from _gen import *  # <AUTO GENERATED>

@func_description('A test function')
@func_parameter('test_param', 'test parameter')
@func_latency_control(delay_before_responses_start=3000, silence_after_each_response=2000, delay_responses=[('Please wait...', 3000)])
def test_code(conv: Conversation, test_param: int):
    pass
"""
        known_lc = FunctionLatencyControl(
            enabled=True,
            initial_delay=3000,
            interval=2000,
            delay_responses=[
                FunctionDelayResponse(id="DR-known", message="Please wait...", duration=3000),
            ],
        )
        with mock_read_from_file(test_file_content):
            result = Function.read_local_resource(
                file_path="functions/test_code.py",
                resource_id="func-123",
                resource_name="test_code",
                resource_mappings=[],
                known_parameters=[
                    FunctionParameters(
                        id="param-123", name="test_param",
                        description="test parameter", type="integer",
                    )
                ],
                known_latency_control=known_lc,
            )
            self.assertTrue(result.latency_control.enabled)
            self.assertEqual(result.latency_control.initial_delay, 3000)
            self.assertEqual(result.latency_control.interval, 2000)
            self.assertEqual(len(result.latency_control.delay_responses), 1)
            self.assertEqual(result.latency_control.delay_responses[0].id, "DR-known")
            # Decorator should be stripped from the code
            self.assertNotIn("func_latency_control", result.code)

    def test_get_new_updated_deleted_subresources_latency_control(self):
        """Function detects latency-control changes as sub-resources."""
        old = Function(
            resource_id="fn-1",
            name="my_func",
            description="desc",
            code="def my_func(conv: Conversation):\n    pass\n",
            parameters=[],
            latency_control=FunctionLatencyControl(enabled=False),
            function_type=FunctionType.GLOBAL,
        )
        new_with_lc = Function(
            resource_id="fn-1",
            name="my_func",
            description="desc",
            code="def my_func(conv: Conversation):\n    pass\n",
            parameters=[],
            latency_control=FunctionLatencyControl(
                enabled=True, initial_delay=5000, interval=3000,
            ),
            function_type=FunctionType.GLOBAL,
        )

        # Enable latency control -> updated sub-resource
        new_subs, updated_subs, deleted_subs = new_with_lc.get_new_updated_deleted_subresources(old)
        self.assertEqual(len(new_subs), 0)
        self.assertEqual(len(updated_subs), 1)
        self.assertEqual(updated_subs[0].command_type, "latency_control")
        self.assertEqual(len(deleted_subs), 0)

        # Disable latency control -> update sub-resource
        new_subs, updated_subs, deleted_subs = old.get_new_updated_deleted_subresources(new_with_lc)
        self.assertEqual(len(new_subs), 0)
        self.assertEqual(len(updated_subs), 1)
        self.assertEqual(len(deleted_subs), 0)

        # Modify latency control -> updated sub-resource
        modified = Function(
            resource_id="fn-1",
            name="my_func",
            description="desc",
            code="def my_func(conv: Conversation):\n    pass\n",
            parameters=[],
            latency_control=FunctionLatencyControl(
                enabled=True, initial_delay=9000, interval=3000,
            ),
            function_type=FunctionType.GLOBAL,
        )
        new_subs, updated_subs, deleted_subs = modified.get_new_updated_deleted_subresources(
            new_with_lc
        )
        self.assertEqual(len(new_subs), 0)
        self.assertEqual(len(updated_subs), 1)
        self.assertEqual(len(deleted_subs), 0)

        # No change -> no sub-resources
        new_subs, updated_subs, deleted_subs = new_with_lc.get_new_updated_deleted_subresources(
            new_with_lc
        )
        self.assertEqual(len(new_subs), 0)
        self.assertEqual(len(updated_subs), 0)
        self.assertEqual(len(deleted_subs), 0)

    def test_validate_goto_step(self):
        """Test validation of flow.goto_step() references."""
        resource_mappings = [
            ResourceMapping(
                resource_id="flow-123",
                resource_name="Test Flow",
                resource_type=FlowConfig,
                file_path="flows/test_flow/flow_config.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            ),
            ResourceMapping(
                resource_id="Test Flow_step-1",
                resource_name="Step One",
                resource_type=FlowStep,
                file_path="flows/test_flow/steps/step_one.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            ),
            ResourceMapping(
                resource_id="Test Flow_process_payment",
                resource_name="process_payment",
                resource_type=FunctionStep,
                file_path="flows/test_flow/function_steps/process_payment.py",
                resource_prefix=None,
                flow_name="Test Flow",
            ),
            ResourceMapping(
                resource_id="Test Flow_dont_know",
                resource_name="Don't know/ Can't Find",
                resource_type=FlowStep,
                file_path="flows/test_flow/steps/dont_know.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            ),
        ]

        # Valid goto_step to a FlowStep
        func = Function(
            resource_id="func-1",
            name="my_func",
            description="desc",
            code='def my_func(conv: Conversation, flow: Flow):\n    flow.goto_step("Step One")\n',
            parameters=[],
            latency_control=FunctionLatencyControl(),
            flow_id="flow-123",
            flow_name="Test Flow",
            function_type=FunctionType.TRANSITION,
        )
        self.assertIsNone(func.validate(resource_mappings=resource_mappings))

        # Valid goto_step to a FunctionStep
        func.code = 'def my_func(conv: Conversation, flow: Flow):\n    flow.goto_step("process_payment")\n'
        self.assertIsNone(func.validate(resource_mappings=resource_mappings))

        # Valid goto_step with label argument
        func.code = 'def my_func(conv: Conversation, flow: Flow):\n    flow.goto_step("Step One", "my_label")\n'
        self.assertIsNone(func.validate(resource_mappings=resource_mappings))

        # Valid goto_step with apostrophes in step name (double-quoted string)
        func.code = 'def my_func(conv: Conversation, flow: Flow):\n    flow.goto_step("Don\'t know/ Can\'t Find")\n'
        self.assertIsNone(func.validate(resource_mappings=resource_mappings))

        # Invalid goto_step
        func.code = 'def my_func(conv: Conversation, flow: Flow):\n    flow.goto_step("Nonexistent Step")\n'
        with self.assertRaises(ValueError) as cm:
            func.validate(resource_mappings=resource_mappings)
        self.assertIn("flow.goto_step('Nonexistent Step')", str(cm.exception))
        self.assertIn("does not exist", str(cm.exception))

        # No error when no resource_mappings provided
        func.code = 'def my_func(conv: Conversation, flow: Flow):\n    flow.goto_step("Nonexistent Step")\n'
        self.assertIsNone(func.validate(resource_mappings=[]))

        # No error for global functions (no flow_name)
        global_func = Function(
            resource_id="func-2",
            name="global_func",
            description="desc",
            code='def global_func(conv: Conversation):\n    pass\n',
            parameters=[],
            latency_control=FunctionLatencyControl(),
            function_type=FunctionType.GLOBAL,
        )
        self.assertIsNone(global_func.validate(resource_mappings=resource_mappings))

        # No error when goto_step is commented out
        func.code = 'def my_func(conv: Conversation, flow: Flow):\n    # flow.goto_step("Nonexistent Step")\n    flow.goto_step("Step One")\n'
        self.assertIsNone(func.validate(resource_mappings=resource_mappings))

    def test_validate_goto_flow(self):
        """Test validation of conv.goto_flow() references."""
        resource_mappings = [
            ResourceMapping(
                resource_id="flow-123",
                resource_name="Test Flow",
                resource_type=FlowConfig,
                file_path="flows/test_flow/flow_config.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            ),
            ResourceMapping(
                resource_id="flow-456",
                resource_name="Other Flow",
                resource_type=FlowConfig,
                file_path="flows/other_flow/flow_config.yaml",
                resource_prefix=None,
                flow_name="Other Flow",
            ),
        ]

        # Valid goto_flow
        func = Function(
            resource_id="func-1",
            name="my_func",
            description="desc",
            code='def my_func(conv: Conversation):\n    conv.goto_flow("Other Flow")\n',
            parameters=[],
            latency_control=FunctionLatencyControl(),
            function_type=FunctionType.GLOBAL,
        )
        self.assertIsNone(func.validate(resource_mappings=resource_mappings))

        # Invalid goto_flow
        func.code = 'def my_func(conv: Conversation):\n    conv.goto_flow("Missing Flow")\n'
        with self.assertRaises(ValueError) as cm:
            func.validate(resource_mappings=resource_mappings)
        self.assertIn("conv.goto_flow('Missing Flow')", str(cm.exception))
        self.assertIn("does not exist", str(cm.exception))

        # Variable arguments should not be checked
        func.code = 'def my_func(conv: Conversation):\n    conv.goto_flow(flow_name)\n'
        self.assertIsNone(func.validate(resource_mappings=resource_mappings))

        # No error when no resource_mappings provided
        func.code = 'def my_func(conv: Conversation):\n    conv.goto_flow("Missing Flow")\n'
        self.assertIsNone(func.validate(resource_mappings=[]))

        # Valid goto_flow from transition function
        func = Function(
            resource_id="func-2",
            name="trans_func",
            description="desc",
            code='def trans_func(conv: Conversation, flow: Flow):\n    conv.goto_flow("Test Flow")\n',
            parameters=[],
            latency_control=FunctionLatencyControl(),
            flow_id="flow-123",
            flow_name="Test Flow",
            function_type=FunctionType.TRANSITION,
        )
        self.assertIsNone(func.validate(resource_mappings=resource_mappings))

        # No error when goto_flow is commented out
        func.code = 'def trans_func(conv: Conversation, flow: Flow):\n    # conv.goto_flow("Missing Flow")\n    conv.goto_flow("Other Flow")\n'
        self.assertIsNone(func.validate(resource_mappings=resource_mappings))

    def test_extract_decorators_untyped_parameter_raises_value_error(self):
        """A parameter without a type annotation raises ValueError."""
        code = """@func_description('Book a table')
@func_parameter('booking_ref', 'The booking reference')
def my_func(conv: Conversation, booking_ref):
    pass
"""
        with self.assertRaises(ValueError) as ctx:
            Function._extract_decorators(code, "my_func", [])
        self.assertIn("booking_ref", str(ctx.exception))
        self.assertIn("has no type annotation", str(ctx.exception))

    def test_extract_decorators_complex_type_annotation_raises_value_error(self):
        """A parameter with a complex annotation (e.g. Optional[str]) raises ValueError."""
        code = """@func_description('Book a table')
@func_parameter('booking_ref', 'The booking reference')
def my_func(conv: Conversation, booking_ref: Optional[str]):
    pass
"""
        with self.assertRaises(ValueError) as ctx:
            Function._extract_decorators(code, "my_func", [])
        self.assertIn("booking_ref", str(ctx.exception))
        self.assertIn("unsupported type annotation", str(ctx.exception))


TEST_TOPIC = Topic(
    resource_id="123",
    name="test_topic",
    actions="Run function {{fn:test_id}}",
    content="Test content",
    example_queries=["What is the capital of France?", "Who wrote '1984'?"],
    enabled=True,
)

TEST_TOPIC_RAW = """enabled: true
actions: Run function {{fn:test_id}}
content: Test content
example_queries:
- What is the capital of France?
- Who wrote '1984'?
"""

TEST_TOPIC_PRETTY = """enabled: true
actions: Run function {{fn:test_function}}
content: Test content
example_queries:
- What is the capital of France?
- Who wrote '1984'?
"""


class TopicTests(unittest.TestCase):
    def test_get_raw(self):
        """Test that raw property returns correct YAML representation."""
        self.assertEqual(TEST_TOPIC.raw, TEST_TOPIC_RAW)

    def test_to_pretty(self):
        """Test converting topic to pretty format with function name mapping."""
        resource_mappings = [
            ResourceMapping(
                resource_id="test_id",
                resource_name="test_function",
                resource_type=Function,
                file_path="functions/test_function.py",
                resource_prefix="fn",
                flow_name=None,
            )
        ]
        pretty_content = TEST_TOPIC.to_pretty(resource_mappings=resource_mappings)
        # Verify function ID is replaced with name
        self.assertIn("{{fn:test_function}}", pretty_content)
        self.assertNotIn("{{fn:test_id}}", pretty_content)

    def test_to_pretty_no_mappings(self):
        """Test to_pretty with no resource mappings."""
        pretty_content = TEST_TOPIC.to_pretty(resource_mappings=[])
        # Without mappings, IDs should remain unchanged
        self.assertIn("{{fn:test_id}}", pretty_content)

    def test_convert_and_unconvert_topic(self):
        """Test roundtrip conversion: to_pretty -> from_pretty."""
        resource_mappings = [
            ResourceMapping(
                resource_id="test_id",
                resource_name="test_function",
                resource_type=Function,
                file_path="functions/test_function.py",
                resource_prefix="fn",
                flow_name=None,
            )
        ]
        converted_topic = TEST_TOPIC.to_pretty(resource_mappings=resource_mappings)
        reverted_topic = Topic.from_pretty(
            converted_topic, resource_mappings=resource_mappings
        )
        # Should roundtrip back to original raw format
        self.assertEqual(reverted_topic, TEST_TOPIC.raw)

    def test_function_regex_pattern(self):
        """Test the function regex pattern."""
        # Test various patterns
        test_cases = [
            ("{{fn:func-123}}", ["func-123"]),
            ("Use {{fn:func-123}} and {{fn:func-456}}", ["func-123", "func-456"]),
            ("No functions here", []),
            ("{{fn:simple_name}}", ["simple_name"]),
            ("{{fn:name-with-dashes}}", ["name-with-dashes"]),
        ]

        for test_string, expected_matches in test_cases:
            matches = FUNCTION_REGEX.findall(test_string)
            self.assertEqual(matches, expected_matches)

    def test_validate_topic_ok(self):
        """Test validation with valid function references."""
        resource_mapping = [
            ResourceMapping(
                resource_id="test_id",
                resource_name="test_function",
                resource_type=Function,
                file_path="functions/test_function.py",
                resource_prefix="fn",
                flow_name=None,
            )
        ]
        self.assertIsNone(TEST_TOPIC.validate(resource_mappings=resource_mapping))

    def test_validate_topic_no_mappings(self):
        """Test validation with no resource mappings (should pass)."""
        with self.assertRaises(ValueError) as cm:
            TEST_TOPIC.validate(resource_mappings=[])
        self.assertIn("Invalid references: ['global_functions: test_id']", str(cm.exception))

    def test_validate_function_references(self):
        """Test validation of function references."""
        # Valid function references
        valid_topic = Topic(
            resource_id="789",
            name="valid_topic",
            actions="Use {{fn:func-123}}",
            content="Valid function references",
            example_queries=["Test query"],
        )

        resource_mapping = [
            ResourceMapping(
                resource_id="func-123",
                resource_name="process_data",
                resource_type=Function,
                file_path="functions/process_data.py",
                resource_prefix="fn",
                flow_name=None,
            )
        ]
        self.assertIsNone(valid_topic.validate(resource_mappings=resource_mapping))

        # Invalid function references
        invalid_topic = Topic(
            resource_id="789",
            name="invalid_topic",
            actions="Use {{fn:func-123}} and {{fn:func-456}}",
            content="Invalid function references",
            example_queries=["Test query"],
        )

        # Only provide func-123, not func-456
        resource_mapping = [
            ResourceMapping(
                resource_id="func-123",
                resource_name="process_data",
                resource_type=Function,
                file_path="functions/process_data.py",
                resource_prefix="fn",
                flow_name=None,
            )
        ]

        with self.assertRaises(ValueError) as cm:
            invalid_topic.validate(resource_mappings=resource_mapping)
        self.assertIn("Invalid references: ['global_functions: func-456']", str(cm.exception))

    def test_validate_variable_references(self):
        """Test validation of variable (vrbl) references."""
        topic_with_var = Topic(
            resource_id="789",
            name="topic_with_var",
            actions="Use {{vrbl:VAR-customer_name}} for personalization",
            content="Variable reference",
            example_queries=["Test query"],
        )
        with self.assertRaises(ValueError) as cm:
            topic_with_var.validate(resource_mappings=[])
        self.assertIn("Invalid references: ['variables: VAR-customer_name']", str(cm.exception))

        valid_mapping = [
            ResourceMapping(
                resource_id="VAR-customer_name",
                resource_name="customer_name",
                resource_type=Variable,
                file_path="variables/customer_name",
                flow_name=None,
                resource_prefix="vrbl",
            )
        ]
        self.assertIsNone(topic_with_var.validate(resource_mappings=valid_mapping))

        invalid_topic = Topic(
            resource_id="789",
            name="invalid_topic",
            actions="Use {{vrbl:VAR-customer_name}} and {{vrbl:VAR-nonexistent}}",
            content="One valid one invalid",
            example_queries=["Test query"],
        )
        with self.assertRaises(ValueError) as cm:
            invalid_topic.validate(resource_mappings=valid_mapping)
        self.assertIn("Invalid references: ['variables: VAR-nonexistent']", str(cm.exception))

    def test_validate_attribute_references(self):
        """Test validation of attribute (attr) / variant attribute references."""
        topic_with_attr = Topic(
            resource_id="789",
            name="topic_with_attr",
            actions="Check {{attr:attr-customer-name}} status",
            content="Attribute reference",
            example_queries=["Test query"],
        )
        with self.assertRaises(ValueError) as cm:
            topic_with_attr.validate(resource_mappings=[])
        self.assertIn("Invalid references: ['attributes: attr-customer-name']", str(cm.exception))

        valid_mapping = [
            ResourceMapping(
                resource_id="attr-customer-name",
                resource_name="customer-name",
                resource_type=VariantAttribute,
                file_path="config/variant_attributes.yaml/variant_attributes/customer-name",
                flow_name=None,
                resource_prefix="attr",
            )
        ]
        self.assertIsNone(topic_with_attr.validate(resource_mappings=valid_mapping))

    def test_validate_sms_references(self):
        """Test validation of SMS template (twilio_sms) references."""
        topic_with_sms = Topic(
            resource_id="789",
            name="topic_with_sms",
            actions="Send via {{twilio_sms:SMS_TEMPLATE-123}}",
            content="SMS reference",
            example_queries=["Test query"],
        )
        with self.assertRaises(ValueError) as cm:
            topic_with_sms.validate(resource_mappings=[])
        self.assertIn("Invalid references: ['sms: SMS_TEMPLATE-123']", str(cm.exception))

        valid_mapping = [
            ResourceMapping(
                resource_id="SMS_TEMPLATE-123",
                resource_name="template_123",
                resource_type=SMSTemplate,
                file_path="config/sms_templates.yaml/sms_templates/template_123",
                flow_name=None,
                resource_prefix="twilio_sms",
            )
        ]
        self.assertIsNone(topic_with_sms.validate(resource_mappings=valid_mapping))

    def test_validate_handoff_references(self):
        """Test validation of handoff (ho) references."""
        topic_with_handoff = Topic(
            resource_id="789",
            name="topic_with_handoff",
            actions="Transfer with {{ho:handoff-1}}",
            content="Handoff reference",
            example_queries=["Test query"],
        )
        with self.assertRaises(ValueError) as cm:
            topic_with_handoff.validate(resource_mappings=[])
        self.assertIn("Invalid references: ['handoff: handoff-1']", str(cm.exception))

        valid_mapping = [
            ResourceMapping(
                resource_id="handoff-1",
                resource_name="default",
                resource_type=Handoff,
                file_path="config/handoffs.yaml/handoffs/default",
                flow_name=None,
                resource_prefix="ho",
            )
        ]
        self.assertIsNone(topic_with_handoff.validate(resource_mappings=valid_mapping))

    def test_validate_entity_references(self):
        """Test validation of entity references (used in FlowStep no_code steps)."""
        step_with_entity = FlowStep(
            resource_id="step-1",
            step_id="step-1",
            name="Collect",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.DEFAULT_STEP,
            prompt="What is your {{entity:ENTITY-customer_name}}?",
            position={"x": 0.0, "y": 0.0},
            conditions=[],
            extracted_entities=["ENTITY-customer_name"],
        )
        flow_mapping = [
            ResourceMapping(
                resource_id="flow-123",
                resource_name="Test Flow",
                resource_type=FlowConfig,
                file_path="flows/test_flow/flow_config.yaml",
                flow_name="Test Flow",
                resource_prefix=None,
            )
        ]
        with self.assertRaises(ValueError) as cm:
            step_with_entity.validate(resource_mappings=flow_mapping)
        self.assertIn("Invalid references: ['entities: ENTITY-customer_name']", str(cm.exception))

        valid_mapping = flow_mapping + [
            ResourceMapping(
                resource_id="ENTITY-customer_name",
                resource_name="customer_name",
                resource_type=Entity,
                file_path="config/entities.yaml/entities/customer_name",
                flow_name=None,
                resource_prefix="entity",
            )
        ]
        self.assertIsNone(step_with_entity.validate(resource_mappings=valid_mapping))

    def test_validate_transition_function_references(self):
        """Test validation of transition function (ft) references in flow steps."""
        step_with_ft = FlowStep(
            resource_id="step-1",
            step_id="step-1",
            name="Process",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.ADVANCED_STEP,
            prompt="Call {{ft:FUNCTION-flow_process}} to process",
            position={"x": 0.0, "y": 0.0},
        )
        flow_mapping = [
            ResourceMapping(
                resource_id="flow-123",
                resource_name="Test Flow",
                resource_type=FlowConfig,
                file_path="flows/test_flow/flow_config.yaml",
                flow_name="Test Flow",
                resource_prefix=None,
            )
        ]
        with self.assertRaises(ValueError) as cm:
            step_with_ft.validate(resource_mappings=flow_mapping)
        self.assertIn(
            "Invalid references: ['transition_functions: FUNCTION-flow_process']",
            str(cm.exception),
        )

        valid_mapping = flow_mapping + [
            ResourceMapping(
                resource_id="FUNCTION-flow_process",
                resource_name="flow_process",
                resource_type=Function,
                file_path="flows/test_flow/functions/flow_process.py",
                flow_name="Test Flow",
                resource_prefix="ft",
            )
        ]
        self.assertIsNone(step_with_ft.validate(resource_mappings=valid_mapping))

    def test_validate_transition_function_flow_name_scoping(self):
        """Flow step only accepts ft references from the same flow."""
        step_in_flow_a = FlowStep(
            resource_id="step-1",
            step_id="step-1",
            name="Process",
            flow_id="flow-123",
            flow_name="Flow A",
            step_type=StepType.ADVANCED_STEP,
            prompt="Call {{ft:FUNCTION-flow_b_func}} to process",
            position={"x": 0.0, "y": 0.0},
        )
        flow_mapping = [
            ResourceMapping(
                resource_id="flow-123",
                resource_name="Flow A",
                resource_type=FlowConfig,
                file_path="flows/flow_a/flow_config.yaml",
                flow_name="Flow A",
                resource_prefix=None,
            ),
            ResourceMapping(
                resource_id="FUNCTION-flow_b_func",
                resource_name="flow_b_func",
                resource_type=Function,
                file_path="flows/flow_b/functions/flow_b_func.py",
                flow_name="Flow B",
                resource_prefix="ft",
            ),
        ]
        with self.assertRaises(ValueError) as cm:
            step_in_flow_a.validate(resource_mappings=flow_mapping)
        self.assertIn(
            "Invalid references: ['transition_functions: FUNCTION-flow_b_func']",
            str(cm.exception),
        )

    def test_validate_flow_function_reference(self):
        """Test validation rejects flow function references."""
        topic_with_flow_function = Topic(
            resource_id="789",
            name="invalid_topic",
            actions="Use {{ft:flow-func-123}}",
            content="Invalid flow function reference",
            example_queries=["Test query"],
        )

        with self.assertRaises(ValueError) as cm:
            topic_with_flow_function.validate(resource_mappings=[])
        self.assertIn(
            "Invalid reference type: transition_functions is not a valid reference type for this resource. Valid references are: ['global_functions', 'sms', 'handoff', 'attributes', 'variables']", str(cm.exception)
        )

    def test_validate_topic_example_queries(self):
        """Test validation rejects topic with too many example queries."""
        topic_with_too_many_example_queries = Topic(
            resource_id="789",
            name="invalid_topic",
            actions="",
            content="Invalid flow function reference",
            example_queries=["Test query"] * 21,
        )

        with self.assertRaises(ValueError) as cm:
            topic_with_too_many_example_queries.validate(resource_mappings=[])
        self.assertIn(
            "Example queries must be less than 20", str(cm.exception)
        )

    def test_read_local_resource(self):
        """Test reading a topic from a YAML file."""
        test_file_pretty_content = """actions: Run function {{fn:test_function}}
content: Test content for the topic
example_queries:
- What is the capital of France?
- Who wrote '1984'?
"""

        resource_mappings = [
            ResourceMapping(
                resource_id="func-123",
                resource_name="test_function",
                resource_type=Function,
                file_path="functions/test_function.py",
                resource_prefix="fn",
                flow_name=None,
            )
        ]

        with mock_read_from_file(test_file_pretty_content):
            result = Topic.read_local_resource(
                file_path="topics/test_topic.yaml",
                resource_id="topic-123",
                resource_name="test_topic",
                resource_mappings=resource_mappings,
            )

            self.assertEqual(result.resource_id, "topic-123")
            self.assertEqual(result.name, "test_topic")
            # Function name should be converted back to ID
            self.assertIn("{{fn:func-123}}", result.actions)
            self.assertEqual(result.content, "Test content for the topic")
            self.assertEqual(len(result.example_queries), 2)
            self.assertIn("What is the capital of France?", result.example_queries)

    def test_read_local_resource_no_function_references(self):
        """Test reading a topic with no function references."""
        test_file_pretty_content = """actions: Simple action without functions
content: Test content
example_queries:
- Query 1
- Query 2
"""

        with mock_read_from_file(test_file_pretty_content):
            result = Topic.read_local_resource(
                file_path="topics/simple_topic.yaml",
                resource_id="topic-456",
                resource_name="simple_topic",
                resource_mappings=[],
            )

            self.assertEqual(result.resource_id, "topic-456")
            self.assertEqual(result.name, "simple_topic")
            self.assertEqual(result.actions, "Simple action without functions")
            self.assertEqual(result.content, "Test content")
            self.assertEqual(len(result.example_queries), 2)

    def test_read_local_resource_empty_fields(self):
        """Test reading a topic with empty optional fields."""
        test_file_pretty_content = """actions: ''
content: ''
example_queries: []
"""

        with mock_read_from_file(test_file_pretty_content):
            result = Topic.read_local_resource(
                file_path="topics/empty_topic.yaml",
                resource_id="topic-789",
                resource_name="empty_topic",
                resource_mappings=[],
            )

            self.assertEqual(result.resource_id, "topic-789")
            self.assertEqual(result.name, "empty_topic")
            self.assertEqual(result.actions, "")
            self.assertEqual(result.content, "")
            self.assertEqual(result.example_queries, [])


TEST_DISCLAIMER = VoiceDisclaimerMessage(
    resource_id="disclaimer_123",
    name="disclaimer_message",
    message="This call may be recorded for quality purposes.",
    enabled=True,
    language_code="en-GB",
)

DISCLAIMER_RAW = """message: This call may be recorded for quality purposes.
enabled: true
language_code: en-GB
"""


class VoiceDisclaimerMessageTests(unittest.TestCase):
    def setUp(self):
        MultiResourceYamlResource._file_cache.clear()

    def test_get_raw(self):
        """Test that raw property returns correct YAML representation."""
        self.assertEqual(TEST_DISCLAIMER.raw, DISCLAIMER_RAW)

    def test_to_pretty(self):
        """Test converting disclaimer to pretty format."""
        pretty_content = TEST_DISCLAIMER.to_pretty()
        # Should return YAML with function IDs replaced (if any)
        self.assertIn("This call may be recorded", pretty_content)

    def test_convert_and_unconvert_disclaimer(self):
        """Test roundtrip conversion: to_pretty -> from_pretty."""
        converted_disclaimer = TEST_DISCLAIMER.to_pretty()
        reverted_disclaimer = VoiceDisclaimerMessage.from_pretty(
            converted_disclaimer
        )
        self.assertEqual(reverted_disclaimer, TEST_DISCLAIMER.raw)

    def test_validate_disclaimer_message(self):
        """Test validation of disclaimer message."""
        self.assertIsNone(TEST_DISCLAIMER.validate(resource_mappings=[]))

        # Test with invalid function reference
        invalid_disclaimer = VoiceDisclaimerMessage(
            resource_id="disclaimer_123",
            name="disclaimer_message",
            message="Use {{fn:func-123}} in disclaimer",
            enabled=True,
            language_code="en-GB",
        )
        with self.assertRaises(ValueError) as cm:
            invalid_disclaimer.validate(resource_mappings=[])
        self.assertIn(
            "Invalid reference type: global_functions is not a valid reference type for this resource. Valid references are: ['attributes', 'variables']",
            str(cm.exception),
        )

        # Test with invalid handoff reference
        handoff_disclaimer = VoiceDisclaimerMessage(
            resource_id="disclaimer_123",
            name="disclaimer_message",
            message="Hand off to {{ho:some-handoff}}",
            enabled=True,
            language_code="en-GB",
        )
        with self.assertRaises(ValueError) as cm:
            handoff_disclaimer.validate(resource_mappings=[])
        self.assertIn(
            "Invalid reference type: handoff is not a valid reference type for this resource. Valid references are: ['attributes', 'variables']",
            str(cm.exception),
        )

        # Test with invalid attribute reference ID (attr exists in prompt but not in mappings)
        attr_disclaimer = VoiceDisclaimerMessage(
            resource_id="disclaimer_123",
            name="disclaimer_message",
            message="Your status is {{attr:attr-nonexistent}}.",
            enabled=True,
            language_code="en-GB",
        )
        with self.assertRaises(ValueError) as cm:
            attr_disclaimer.validate(resource_mappings=[])
        self.assertIn(
            "Invalid references: ['attributes: attr-nonexistent']",
            str(cm.exception),
        )

        # Valid attr reference
        valid_attr_mapping = [
            ResourceMapping(
                resource_id="attr-customer-name",
                resource_name="customer-name",
                resource_type=VariantAttribute,
                file_path="config/variant_attributes.yaml/variant_attributes/customer-name",
                flow_name=None,
                resource_prefix="attr",
            )
        ]
        valid_attr_disclaimer = VoiceDisclaimerMessage(
            resource_id="disclaimer_123",
            name="disclaimer_message",
            message="Your status is {{attr:attr-customer-name}}.",
            enabled=True,
            language_code="en-GB",
        )
        self.assertIsNone(valid_attr_disclaimer.validate(resource_mappings=valid_attr_mapping))

        # Test with empty language code
        empty_lang_disclaimer = VoiceDisclaimerMessage(
            resource_id="disclaimer_123",
            name="disclaimer_message",
            message="This call may be recorded.",
            enabled=True,
            language_code="",
        )
        with self.assertRaises(ValueError) as cm:
            empty_lang_disclaimer.validate(resource_mappings=[])
        self.assertIn("Language code cannot be empty.", str(cm.exception))

    def test_read_local_resource(self):
        """Test reading a disclaimer from a YAML file."""
        test_file_content = """disclaimer_messages:
  message: This call may be recorded.
  enabled: true
  language_code: en-GB
"""

        def exists_config(path):
            return "configuration.yaml" in str(path) or os.path.exists(path)

        def isfile_config(path):
            return "configuration.yaml" in str(path) or os.path.isfile(path)

        def getmtime_config(path):
            return 1.0 if "configuration.yaml" in str(path) else os.path.getmtime(path)

        with mock_read_from_file({"voice/configuration.yaml": test_file_content}):
            with unittest.mock.patch(
                "poly.resources.resource.os.path.exists", side_effect=exists_config
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.isfile", side_effect=isfile_config
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.getmtime", side_effect=getmtime_config
            ):
                result = VoiceDisclaimerMessage.read_local_resource(
                    file_path="voice/configuration.yaml/disclaimer_messages",
                    resource_id="disclaimer_123",
                    resource_name="disclaimer_message",
                )

            self.assertEqual(result.resource_id, "disclaimer_123")
            self.assertEqual(result.name, "disclaimer_message")
            self.assertEqual(result.message, "This call may be recorded.")
            self.assertEqual(result.enabled, True)
            self.assertEqual(result.language_code, "en-GB")


TEST_GREETING = VoiceGreeting(
    resource_id="greeting_123",
    name="greeting",
    welcome_message="Hello! How can I help you today?",
    language_code="en-GB",
)

GREETING_RAW = """welcome_message: Hello! How can I help you today?
language_code: en-GB
"""


class VoiceGreetingTests(unittest.TestCase):
    def setUp(self):
        MultiResourceYamlResource._file_cache.clear()

    def test_get_raw(self):
        """Test that raw property returns correct YAML representation."""
        self.assertEqual(TEST_GREETING.raw, GREETING_RAW)

    def test_to_pretty(self):
        """Test converting greeting to pretty format."""
        pretty_content = TEST_GREETING.to_pretty()
        self.assertIn("Hello! How can I help you today?", pretty_content)

    def test_convert_and_unconvert_greeting(self):
        """Test roundtrip conversion: to_pretty -> from_pretty."""
        converted_greeting = TEST_GREETING.to_pretty()
        reverted_greeting = VoiceGreeting.from_pretty(converted_greeting)
        self.assertEqual(reverted_greeting, TEST_GREETING.raw)

    def test_validate_greeting_message(self):
        """Test validation of greeting message."""
        self.assertIsNone(TEST_GREETING.validate(resource_mappings=[]))

        # Test with empty message
        empty_greeting = VoiceGreeting(
            resource_id="greeting_123",
            name="greeting",
            welcome_message="",
            language_code="en-GB",
        )
        with self.assertRaises(ValueError) as cm:
            empty_greeting.validate(resource_mappings=[])
        self.assertIn("Welcome message cannot be empty.", str(cm.exception))

        # Test with invalid function reference
        invalid_greeting = VoiceGreeting(
            resource_id="greeting_123",
            name="greeting",
            welcome_message="Use {{fn:func-123}} in greeting",
            language_code="en-GB",
        )
        with self.assertRaises(ValueError) as cm:
            invalid_greeting.validate(resource_mappings=[])
        self.assertIn(
            "Invalid reference type: global_functions is not a valid reference type for this resource. Valid references are: ['attributes', 'variables']",
            str(cm.exception),
        )

        # Test with invalid handoff reference
        handoff_greeting = VoiceGreeting(
            resource_id="greeting_123",
            name="greeting",
            welcome_message="Transfer to {{ho:human-agent}}",
            language_code="en-GB",
        )
        with self.assertRaises(ValueError) as cm:
            handoff_greeting.validate()
        self.assertIn(
            "Invalid reference type: handoff is not a valid reference type for this resource. Valid references are: ['attributes', 'variables']",
            str(cm.exception),
        )

        # Test with empty language code
        empty_lang_greeting = VoiceGreeting(
            resource_id="greeting_123",
            name="greeting",
            welcome_message="Hello!",
            language_code="",
        )
        with self.assertRaises(ValueError) as cm:
            empty_lang_greeting.validate()
        self.assertIn("Language code cannot be empty.", str(cm.exception))

    def test_read_local_resource(self):
        """Test reading a greeting from a YAML file."""
        test_file_content = """greeting:
  welcome_message: Hello! How can I help you?
  language_code: en-GB
"""

        def exists_config(path):
            return "configuration.yaml" in str(path) or os.path.exists(path)

        def isfile_config(path):
            return "configuration.yaml" in str(path) or os.path.isfile(path)

        def getmtime_config(path):
            return 1.0 if "configuration.yaml" in str(path) else os.path.getmtime(path)

        with mock_read_from_file({"voice/configuration.yaml": test_file_content}):
            with unittest.mock.patch(
                "poly.resources.resource.os.path.exists", side_effect=exists_config
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.isfile", side_effect=isfile_config
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.getmtime", side_effect=getmtime_config
            ):
                result = VoiceGreeting.read_local_resource(
                    file_path="voice/configuration.yaml/greeting",
                    resource_id="greeting_123",
                    resource_name="greeting",
                )

            self.assertEqual(result.resource_id, "greeting_123")
            self.assertEqual(result.name, "greeting")
            self.assertEqual(result.welcome_message, "Hello! How can I help you?")
            self.assertEqual(result.language_code, "en-GB")


TEST_PERSONALITY = SettingsPersonality(
    resource_id="personality_123",
    name="personality",
    adjectives={"Polite": True, "Calm": True, "Kind": False},
    custom="",
)

PERSONALITY_RAW = """adjectives:
  Polite: true
  Calm: true
  Kind: false
custom: ''
"""


class SettingsPersonalityTests(unittest.TestCase):
    def test_get_raw(self):
        """Test that raw property returns correct YAML representation."""
        self.assertEqual(TEST_PERSONALITY.raw, PERSONALITY_RAW)

    def test_to_pretty(self):
        """Test converting personality to pretty format."""
        pretty_content = TEST_PERSONALITY.to_pretty()
        self.assertIn("Polite", pretty_content)

    def test_convert_and_unconvert_personality(self):
        """Test roundtrip conversion: to_pretty -> from_pretty."""
        converted_personality = TEST_PERSONALITY.to_pretty()
        reverted_personality = SettingsPersonality.from_pretty(converted_personality)
        self.assertEqual(reverted_personality, TEST_PERSONALITY.raw)

    def test_validate_personality_settings(self):
        """Test validation of personality settings."""
        self.assertIsNone(TEST_PERSONALITY.validate())

        # Test with custom and other adjectives (invalid)
        invalid_personality = SettingsPersonality(
            resource_id="personality_123",
            name="personality",
            adjectives={"Polite": True, "Other": True},
            custom="Custom personality description",
        )
        with self.assertRaises(ValueError) as cm:
            invalid_personality.validate()
        self.assertIn(
            "Other adjective can only be set if no other adjectives are selected.",
            str(cm.exception),
        )

        # Test with invalid adjectives
        invalid_personality = SettingsPersonality(
            resource_id="personality_123",
            name="personality",
            adjectives={"InvalidAdjective": True},
            custom="",
        )
        with self.assertRaises(ValueError) as cm:
            invalid_personality.validate()
        self.assertIn("Adjectives must be from the allowed set:", str(cm.exception))

        # Test with custom and 'Other' selected (valid case)
        valid_personality = SettingsPersonality(
            resource_id="personality_123",
            name="personality",
            adjectives={"Other": True},
            custom="Custom personality description",
        )
        self.assertIsNone(valid_personality.validate())

        # Test with invalid function reference in custom field
        invalid_personality = SettingsPersonality(
            resource_id="personality_123",
            name="personality",
            adjectives={"Other": True},
            custom="Use {{fn:func-123}} in custom personality",
        )
        with self.assertRaises(ValueError) as cm:
            invalid_personality.validate()
        self.assertIn(
            "Invalid reference type: global_functions is not a valid reference type for this resource. Valid references are: ['attributes', 'variables']",
            str(cm.exception),
        )

    def test_read_local_resource(self):
        """Test reading a personality from a YAML file."""
        test_file_pretty_content = """adjectives:
  Polite: true
  Calm: true
custom: ''
"""

        with mock_read_from_file(test_file_pretty_content):
            result = SettingsPersonality.read_local_resource(
                file_path="agent_settings/personality.yaml",
                resource_id="personality_123",
                resource_name="personality",
            )

            self.assertEqual(result.resource_id, "personality_123")
            self.assertEqual(result.name, "personality")
            self.assertIn("Polite", result.adjectives)
            self.assertEqual(result.custom, "")


TEST_ROLE = SettingsRole(
    resource_id="role_123",
    name="role",
    value="Customer Service Representative",
    additional_info="Handles customer inquiries and support requests",
    custom="",
)

ROLE_RAW = """value: Customer Service Representative
additional_info: Handles customer inquiries and support requests
custom: ''
"""


class SettingsRoleTests(unittest.TestCase):
    def test_get_raw(self):
        """Test that raw property returns correct YAML representation."""
        self.assertEqual(TEST_ROLE.raw, ROLE_RAW)

    def test_to_pretty(self):
        """Test converting role to pretty format."""
        pretty_content = TEST_ROLE.to_pretty()
        self.assertIn("Customer Service Representative", pretty_content)

    def test_convert_and_unconvert_role(self):
        """Test roundtrip conversion: to_pretty -> from_pretty."""
        converted_role = TEST_ROLE.to_pretty()
        reverted_role = SettingsRole.from_pretty(converted_role)
        self.assertEqual(reverted_role, TEST_ROLE.raw)

    def test_validate_role_settings(self):
        """Test validation of role settings."""
        self.assertIsNone(TEST_ROLE.validate(resource_mappings=[]))

        # Test with custom and non-other role (invalid)
        invalid_role = SettingsRole(
            resource_id="role_123",
            name="role",
            value="Customer Service Representative",
            additional_info="",
            custom="Custom role description",
        )
        with self.assertRaises(ValueError) as cm:
            invalid_role.validate(resource_mappings=[])
        self.assertIn(
            "Custom role can only be set if role is 'other'.", str(cm.exception)
        )

        # Test with custom and 'other' role (valid case)
        valid_role = SettingsRole(
            resource_id="role_123",
            name="role",
            value="Other",
            additional_info="",
            custom="Custom role description",
        )
        self.assertIsNone(valid_role.validate(resource_mappings=[]))

        # Test with invalid function reference in custom field
        invalid_role = SettingsRole(
            resource_id="role_123",
            name="role",
            value="Other",
            additional_info="",
            custom="Use {{fn:func-123}} in custom role",
        )
        with self.assertRaises(ValueError) as cm:
            invalid_role.validate(resource_mappings=[])
        self.assertIn(
            "Invalid reference type: global_functions is not a valid reference type for this resource. Valid references are: ['attributes', 'variables']",
            str(cm.exception),
        )

    def test_read_local_resource(self):
        """Test reading a role from a YAML file."""
        test_file_pretty_content = """value: Customer Service Representative
additional_info: Handles customer inquiries
custom: ''
"""

        with mock_read_from_file(test_file_pretty_content):
            result = SettingsRole.read_local_resource(
                file_path="agent_settings/role.yaml",
                resource_id="role_123",
                resource_name="role",
            )

            self.assertEqual(result.resource_id, "role_123")
            self.assertEqual(result.name, "role")
            self.assertEqual(result.value, "Customer Service Representative")
            self.assertEqual(result.additional_info, "Handles customer inquiries")


TEST_RULES = SettingsRules(
    resource_id="rules_123",
    name="rules",
    behaviour="Always be polite and helpful. Use {{fn:func-123}} when needed.",
)


class SettingsRulesTests(unittest.TestCase):
    def test_get_raw(self):
        """Test that raw property returns the behaviour string."""
        self.assertEqual(TEST_RULES.raw, TEST_RULES.behaviour)

    def test_to_pretty(self):
        """Test converting rules to pretty format with function name mapping."""
        resource_mappings = [
            ResourceMapping(
                resource_id="func-123",
                resource_name="test_function",
                resource_type=Function,
                file_path="functions/test_function.py",
                resource_prefix="fn",
                flow_name=None,
            )
        ]
        pretty_content = TEST_RULES.to_pretty(resource_mappings=resource_mappings)
        # Verify function ID is replaced with name
        self.assertIn("{{fn:test_function}}", pretty_content)
        self.assertNotIn("{{fn:func-123}}", pretty_content)

    def test_to_pretty_no_mappings(self):
        """Test to_pretty with no resource mappings."""
        pretty_content = TEST_RULES.to_pretty(resource_mappings=[])
        # Without mappings, IDs should remain unchanged
        self.assertIn("{{fn:func-123}}", pretty_content)

    def test_convert_and_unconvert_rules(self):
        """Test roundtrip conversion: to_pretty -> from_pretty."""
        resource_mappings = [
            ResourceMapping(
                resource_id="func-123",
                resource_name="test_function",
                resource_type=Function,
                file_path="functions/test_function.py",
                resource_prefix="fn",
                flow_name=None,
            )
        ]
        converted_rules = TEST_RULES.to_pretty(resource_mappings=resource_mappings)
        reverted_rules = SettingsRules.from_pretty(
            converted_rules, resource_mappings=resource_mappings
        )
        # Should roundtrip back to original raw format
        self.assertEqual(reverted_rules, TEST_RULES.raw)

    def test_function_name_swapping(self):
        """Test the core function name swapping functionality."""
        original_content = "Use {{fn:func-123}} and {{fn:func-456}}"

        resource_mappings = [
            ResourceMapping(
                resource_id="func-123",
                resource_name="process_data",
                resource_type=Function,
                file_path="functions/process_data.py",
                resource_prefix="fn",
                flow_name=None,
            ),
            ResourceMapping(
                resource_id="func-456",
                resource_name="validate_input",
                resource_type=Function,
                file_path="functions/validate_input.py",
                resource_prefix="fn",
                flow_name=None,
            ),
        ]

        # Test make_pretty (function IDs -> names)
        pretty_content = SettingsRules.make_pretty(
            original_content, resource_mappings=resource_mappings
        )
        expected_pretty = "Use {{fn:process_data}} and {{fn:validate_input}}"
        self.assertEqual(pretty_content, expected_pretty)

        # Test from_pretty (function names -> IDs)
        restored_content = SettingsRules.from_pretty(
            pretty_content, resource_mappings=resource_mappings
        )
        self.assertEqual(restored_content, original_content)

    def test_validate_rules_behaviour(self):
        """Test validation of rules behaviour."""
        # Test with valid function reference
        resource_mapping = [
            ResourceMapping(
                resource_id="func-123",
                resource_name="test_function",
                resource_type=Function,
                file_path="functions/test_function.py",
                resource_prefix="fn",
                flow_name=None,
            )
        ]
        self.assertIsNone(TEST_RULES.validate(resource_mappings=resource_mapping))

        # Test with invalid function reference
        resource_mapping = [
            ResourceMapping(
                resource_id="func-456",
                resource_name="other_function",
                resource_type=Function,
                file_path="functions/other_function.py",
                resource_prefix="fn",
                flow_name=None,
            )
        ]

        with self.assertRaises(ValueError) as cm:
            TEST_RULES.validate(resource_mappings=resource_mapping)
        self.assertIn("Invalid references: ['global_functions: func-123']", str(cm.exception))

        # Test with invalid attribute reference
        rules_with_attr = SettingsRules(
            resource_id="rules_123",
            name="rules",
            behaviour="Use {{attr:attr-nonexistent}} for personalization.",
        )
        with self.assertRaises(ValueError) as cm:
            rules_with_attr.validate(resource_mappings=[])
        self.assertIn(
            "Invalid references: ['attributes: attr-nonexistent']",
            str(cm.exception),
        )

        # Test with invalid variable reference
        rules_with_var = SettingsRules(
            resource_id="rules_123",
            name="rules",
            behaviour="Hello {{vrbl:VAR-nonexistent}}.",
        )
        with self.assertRaises(ValueError) as cm:
            rules_with_var.validate(resource_mappings=[])
        self.assertIn(
            "Invalid references: ['variables: VAR-nonexistent']",
            str(cm.exception),
        )

    def test_read_local_resource(self):
        """Test reading rules from a text file."""
        test_file_pretty_content = """Always be polite and helpful. Use {{fn:test_function}} when needed.
"""

        resource_mappings = [
            ResourceMapping(
                resource_id="func-123",
                resource_name="test_function",
                resource_type=Function,
                file_path="functions/test_function.py",
                resource_prefix="fn",
                flow_name=None,
            )
        ]

        with mock_read_from_file(test_file_pretty_content):
            result = SettingsRules.read_local_resource(
                file_path="agent_settings/rules.txt",
                resource_id="rules_123",
                resource_name="rules",
                resource_mappings=resource_mappings,
            )

            self.assertEqual(result.resource_id, "rules_123")
            self.assertEqual(result.name, "rules")
            # Function name should be converted back to ID
            self.assertIn("{{fn:func-123}}", result.behaviour)
            self.assertIn("Always be polite", result.behaviour)


TEST_FLOW_CONFIG = FlowConfig(
    resource_id="flow-123",
    name="Test Flow",
    description="A test flow description",
    start_step="step-1",
)

FLOW_CONFIG_RAW = """name: Test Flow
description: A test flow description
start_step: step-1
"""


class FlowConfigTests(unittest.TestCase):
    def test_get_raw(self):
        """Test that raw property returns correct YAML representation."""
        self.assertEqual(TEST_FLOW_CONFIG.raw, FLOW_CONFIG_RAW)

    def test_to_pretty(self):
        """Test converting flow config to pretty format with start_step name mapping."""
        resource_mappings = [
            ResourceMapping(
                resource_id="Test Flow_step-1",
                resource_name="Start Step",
                resource_type=FlowStep,
                file_path="flows/test_flow/steps/start_step.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            )
        ]
        pretty_content = TEST_FLOW_CONFIG.to_pretty(
            resource_name="Test Flow", resource_mappings=resource_mappings
        )
        # Verify start_step ID is replaced with name
        self.assertIn("start_step: Start Step", pretty_content)
        self.assertNotIn("start_step: step-1", pretty_content)

    def test_to_pretty_no_mappings(self):
        """Test to_pretty with no resource mappings."""
        pretty_content = TEST_FLOW_CONFIG.to_pretty(resource_mappings=[])
        # Without mappings, IDs should remain unchanged
        self.assertIn("start_step: step-1", pretty_content)

    def test_convert_and_unconvert_flow_config(self):
        """Test roundtrip conversion: to_pretty -> from_pretty."""
        resource_mappings = [
            ResourceMapping(
                resource_id="Test Flow_step-1",
                resource_name="Start Step",
                resource_type=FlowStep,
                file_path="flows/test_flow/steps/start_step.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            )
        ]
        converted_config = TEST_FLOW_CONFIG.to_pretty(
            resource_name="Test Flow", resource_mappings=resource_mappings
        )
        reverted_config = FlowConfig.from_pretty(
            converted_config,
            resource_name="Test Flow",
            resource_mappings=resource_mappings,
        )
        # Should roundtrip back to original raw format
        self.assertEqual(reverted_config, TEST_FLOW_CONFIG.raw)

    def test_start_step_swapping(self):
        """Test the core start_step name swapping functionality."""
        original_content = "start_step: step-1\n"

        resource_mappings = [
            ResourceMapping(
                resource_id="Test Flow_step-1",
                resource_name="Start Step",
                resource_type=FlowStep,
                file_path="flows/test_flow/steps/start_step.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            ),
            ResourceMapping(
                resource_id="Test Flow_step-2",
                resource_name="Start Step",
                resource_type=FlowStep,
                file_path="flows/test_flow_2/steps/start_step.yaml",
                resource_prefix=None,
                flow_name="Test Flow 2",
            ),
        ]

        # Test make_pretty (step ID -> name)
        pretty_content = FlowConfig.make_pretty(
            original_content,
            resource_name="Test Flow",
            resource_mappings=resource_mappings,
        )
        expected_pretty = "start_step: Start Step\n"
        self.assertEqual(pretty_content, expected_pretty)

        # Test from_pretty (step name -> ID)
        restored_content = FlowConfig.from_pretty(
            pretty_content,
            resource_name="Test Flow",
            resource_mappings=resource_mappings,
        )
        self.assertEqual(restored_content, original_content)

    def test_validate_flow_config(self):
        """Test validation of flow config."""
        resource_mappings = [
            ResourceMapping(
                resource_id="Test Flow_step-1",
                resource_name="Start Step",
                resource_type=FlowStep,
                file_path="flows/test_flow/steps/start_step.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            )
        ]
        self.assertIsNone(
            TEST_FLOW_CONFIG.validate(resource_mappings=resource_mappings)
        )

        # Test with empty start_step
        invalid_config = FlowConfig(
            resource_id="flow-123",
            name="Test Flow",
            description="A test flow description",
            start_step="",
        )
        with self.assertRaises(ValueError) as cm:
            invalid_config.validate(resource_mappings=resource_mappings)
        self.assertIn("Start step cannot be empty.", str(cm.exception))

        # Test with missing start_step in mappings
        invalid_config = FlowConfig(
            resource_id="flow-123",
            name="Test Flow",
            description="A test flow description",
            start_step="missing-step",
        )
        with self.assertRaises(ValueError) as cm:
            invalid_config.validate(resource_mappings=resource_mappings)
        self.assertIn("Start step 'missing-step' not found.", str(cm.exception))

        # Test with empty description
        invalid_config = FlowConfig(
            resource_id="flow-123",
            name="Test Flow",
            description="",
            start_step="step-1",
        )
        with self.assertRaises(ValueError) as cm:
            invalid_config.validate(resource_mappings=resource_mappings)
        self.assertIn("Description cannot be empty.", str(cm.exception))

        # Test with invalid description
        invalid_config = FlowConfig(
            resource_id="flow-123",
            name="Test Flow",
            description=" A test flow description",
            start_step="step-1",
        )
        with self.assertRaises(ValueError) as cm:
            invalid_config.validate(resource_mappings=resource_mappings)
        self.assertIn("Description cannot contain leading or trailing whitespace.", str(cm.exception))

    def test_read_local_resource(self):
        """Test reading a flow config from a YAML file."""
        test_file_pretty_content = """name: Test Flow
description: A test flow description
start_step: Start Step
"""

        resource_mappings = [
            ResourceMapping(
                resource_id="flow-123",
                resource_name="Test Flow",
                resource_type=FlowConfig,
                file_path="flows/test_flow/flow_config.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            ),
            ResourceMapping(
                resource_id="Test Flow_step-1",
                resource_name="Start Step",
                resource_type=FlowStep,
                file_path="flows/test_flow/steps/start_step.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            ),
        ]

        with mock_read_from_file(test_file_pretty_content):
            result = FlowConfig.read_local_resource(
                file_path="flows/test_flow/flow_config.yaml",
                resource_id="flow-123",
                resource_name="Test Flow",
                resource_mappings=resource_mappings,
            )

            self.assertEqual(result.resource_id, "flow-123")
            self.assertEqual(result.name, "Test Flow")
            # Start step name should be converted back to ID
            self.assertEqual(result.start_step, "step-1")
            self.assertEqual(result.description, "A test flow description")

    def test_read_local_resource_flow_name_mismatch(self):
        """Test reading flow config with mismatched flow folder name."""
        test_file_pretty_content = """name: Different Flow Name
description: A test flow description
start_step: step-1
"""

        with mock_read_from_file(test_file_pretty_content):
            with self.assertRaises(ValueError) as cm:
                FlowConfig.read_local_resource(
                    file_path="flows/test_flow/flow_config.yaml",
                    resource_id="flow-123",
                    resource_name="Different Flow Name",
                )
            self.assertIn(
                "Flow folder name does not match flow name in config", str(cm.exception)
            )

    def test_start_step_with_colon_in_name(self):
        """Test that flow names with colons are properly quoted in YAML."""
        original_content = "name: Test Flow\ndescription: A test flow\nstart_step: step-1\n"

        resource_mappings = [
            ResourceMapping(
                resource_id="Test Flow: Main_step-1",
                resource_name="Step: Start",
                resource_type=FlowStep,
                file_path="flows/test_flow_main/steps/start_step.yaml",
                resource_prefix=None,
                flow_name="Test Flow: Main",
            )
        ]

        # Test make_pretty (step ID -> name with colon)
        pretty_content = FlowConfig.make_pretty(
            original_content,
            resource_name="Test Flow: Main",
            resource_mappings=resource_mappings,
        )
        # YAML should properly quote the value with colon
        yaml_dict = yaml.safe_load(pretty_content)
        self.assertEqual(yaml_dict["start_step"], "Step: Start")
        # Verify it's valid YAML that can be parsed
        self.assertIsNotNone(yaml_dict)

        # Test from_pretty (step name with colon -> ID)
        restored_content = FlowConfig.from_pretty(
            pretty_content,
            resource_name="Test Flow: Main",
            resource_mappings=resource_mappings,
        )
        restored_yaml = yaml.safe_load(restored_content)
        self.assertEqual(restored_yaml["start_step"], "step-1")


TEST_FLOW_STEP = FlowStep(
    resource_id="flow-123_step-1",
    step_id="step-1",
    name="Test Step",
    flow_id="flow-123",
    flow_name="Test Flow",
    step_type=StepType.ADVANCED_STEP,
    asr_biasing=ASRBiasing(
        flow_id="flow-123",
        step_id="step-1",
        custom_keywords=["Hello", "Help", "Support"],
        is_enabled=True,
    ),
    dtmf_config=DTMFConfig(
        flow_id="flow-123",
        step_id="step-1",
        is_enabled=False,
    ),
    conditions=[],
    prompt="Hello, how can I help you?",
    position={"x": 0.0, "y": 0.0},
)

FLOW_STEP_RAW = """step_type: advanced_step
name: Test Step
asr_biasing:
  is_enabled: true
  alphanumeric: false
  name_spelling: false
  numeric: false
  party_size: false
  precise_date: false
  relative_date: false
  single_number: false
  time: false
  yes_no: false
  address: false
  custom_keywords:
  - Hello
  - Help
  - Support
dtmf_config:
  is_enabled: false
  inter_digit_timeout: 0
  max_digits: 0
  end_key: '#'
  collect_while_agent_speaking: false
  is_pii: false
prompt: Hello, how can I help you?
"""

FLOW_STEP_RAW_NO_ASR_DTMF = """step_type: advanced_step
name: Test Step
prompt: Hello, how can I help you?
"""

TEST_NO_CODE_FLOW_STEP = FlowStep(
    resource_id="flow-123_step-1",
    step_id="step-1",
    name="Test Step",
    flow_id="flow-123",
    flow_name="Test Flow",
    step_type=StepType.DEFAULT_STEP,
    conditions=[
        Condition(
            resource_id="cond-1",
            name="has_option",
            description="User selected option",
            condition_type=ConditionType.STEP,
            child_step="step-2",
            step_id="step-1",
            flow_id="flow-123",
            required_entities=[],
            position={"x": 0.0, "y": 0.0},
        )
    ],
    prompt="Hello, how can I help you?",
    position={"x": 0.0, "y": 0.0},
    extracted_entities=["customer_name"],
)

FLOW_NO_CODE_STEP_RAW = """step_type: default_step
name: Test Step
conditions:
- name: has_option
  condition_type: step_condition
  description: User selected option
  child_step: step-2
  required_entities: []
extracted_entities:
- customer_name
prompt: Hello, how can I help you?
"""

class FlowStepTests(unittest.TestCase):
    def test_get_raw(self):
        """Test that raw property returns correct YAML representation."""
        self.assertEqual(TEST_FLOW_STEP.raw, FLOW_STEP_RAW)

    def test_get_raw_no_code_step(self):
        """Test that raw property returns correct YAML representation for no code step."""
        self.assertEqual(TEST_NO_CODE_FLOW_STEP.raw, FLOW_NO_CODE_STEP_RAW)

    def test_to_pretty(self):
        """Test converting flow step to pretty format with function name mapping."""
        resource_mappings = [
            ResourceMapping(
                resource_id="func-123",
                resource_name="test_function",
                resource_type=Function,
                file_path="functions/test_function.py",
                resource_prefix="fn",
                flow_name=None,
            )
        ]
        pretty_content = TEST_FLOW_STEP.to_pretty(resource_mappings=resource_mappings)
        # Should return YAML with function IDs replaced (if any)
        self.assertIn("Test Step", pretty_content)

    def test_to_pretty_no_code_step(self):
        """Test converting no code step to pretty format."""
        resource_mappings = [
            ResourceMapping(
                resource_id="customer_name",
                resource_name="Customer Name",
                resource_type=Entity,
                file_path="entities/customer_name.yaml",
                resource_prefix="entity",
                flow_name=None,
            )
        ]
        pretty_content = TEST_NO_CODE_FLOW_STEP.to_pretty(resource_mappings=resource_mappings)
        # Should return YAML with entity IDs replaced (if any)
        self.assertIn("Customer Name", pretty_content)

    def test_convert_and_unconvert_flow_step(self):
        """Test roundtrip conversion: to_pretty -> from_pretty."""
        resource_mappings = [
            ResourceMapping(
                resource_id="func-123",
                resource_name="test_function",
                resource_type=Function,
                file_path="functions/test_function.py",
                resource_prefix="fn",
                flow_name=None,
            )
        ]
        converted_step = TEST_FLOW_STEP.to_pretty(resource_mappings=resource_mappings)
        reverted_step = FlowStep.from_pretty(
            converted_step,
            file_path=TEST_FLOW_STEP.file_path,
            resource_mappings=resource_mappings,
        )
        # Should roundtrip back to original raw format
        self.assertEqual(reverted_step, TEST_FLOW_STEP.raw)

    def test_convert_and_unconvert_no_code_step(self):
        """Test roundtrip conversion: to_pretty -> from_pretty."""
        resource_mappings = [
            ResourceMapping(
                resource_id="entity-123",
                resource_name="Customer Name",
                resource_type=Entity,
                file_path="entities/customer_name.yaml",
                resource_prefix="entity",
                flow_name=None,
            )
        ]
        converted_step = TEST_NO_CODE_FLOW_STEP.to_pretty(resource_mappings=resource_mappings)
        reverted_step = FlowStep.from_pretty(
            converted_step,
            file_path=TEST_NO_CODE_FLOW_STEP.file_path,
            resource_mappings=resource_mappings,
        )
        # Should roundtrip back to original raw format
        self.assertEqual(reverted_step, TEST_NO_CODE_FLOW_STEP.raw)

    def test_read_step_with_no_asr_dtmf(self):
        """Test reading a flow step with no ASR or DTMF config."""
        yaml_dict = yaml.safe_load(FLOW_STEP_RAW_NO_ASR_DTMF)
        step = FlowStep.from_yaml_dict(
            yaml_dict,
            resource_id="Test Flow_step-1",
            file_name="test_step",
            flow_id="flow-123",
            flow_name="Test Flow",
            resource_mappings=[]
        )
        self.assertEqual(step.asr_biasing, ASRBiasing(flow_id="flow-123", step_id="step-1"))
        self.assertEqual(step.dtmf_config, DTMFConfig(flow_id="flow-123", step_id="step-1"))

    def test_function_name_swapping(self):
        """Test the core function name swapping functionality."""
        original_content = "prompt: Use {{fn:func-123}} and {{fn:func-456}}\n"

        resource_mappings = [
            ResourceMapping(
                resource_id="func-123",
                resource_name="process_data",
                resource_type=Function,
                file_path="functions/process_data.py",
                resource_prefix="fn",
                flow_name=None,
            ),
            ResourceMapping(
                resource_id="func-456",
                resource_name="validate_input",
                resource_type=Function,
                file_path="functions/validate_input.py",
                resource_prefix="fn",
                flow_name=None,
            ),
        ]

        # Test make_pretty (function IDs -> names)
        pretty_content = FlowStep.make_pretty(
            original_content,
            file_path="flows/test_flow/steps/test_step.yaml",
            resource_mappings=resource_mappings,
        )
        self.assertIn("{{fn:process_data}}", pretty_content)
        self.assertIn("{{fn:validate_input}}", pretty_content)

        # Test from_pretty (function names -> IDs)
        restored_content = FlowStep.from_pretty(
            pretty_content,
            file_path="flows/test_flow/steps/test_step.yaml",
            resource_mappings=resource_mappings,
        )
        self.assertEqual(restored_content, original_content)

    def test_child_step_with_colon_in_name(self):
        """Test that flow step names with colons are properly quoted in YAML."""
        original_content = """step_type: default_step
name: Test Step
prompt: What would you like to do?
conditions:
  - name: has_option
    condition_type: step_condition
    description: User selected option
    required_entities: []
    child_step: step-2
"""

        resource_mappings = [
            ResourceMapping(
                resource_id="Test Flow: Main_step-2",
                resource_name="Step: Next",
                resource_type=FlowStep,
                file_path="flows/test_flow_main/steps/next_step.yaml",
                resource_prefix=None,
                flow_name="Test Flow: Main",
            ),
            ResourceMapping(
                resource_id="entity-123",
                resource_name="Customer: Name",
                resource_type=Entity,
                file_path="entities/customer_name.yaml",
                resource_prefix="entity",
                flow_name=None,
            ),
        ]

        # Test make_pretty (step ID -> name with colon)
        pretty_content = FlowStep.make_pretty(
            original_content,
            file_path="flows/test_flow_main/steps/test_step.yaml",
            resource_mappings=resource_mappings,
        )
        # YAML should properly quote the value with colon
        yaml_dict = yaml.safe_load(pretty_content)
        self.assertEqual(yaml_dict["conditions"][0]["child_step"], "Step: Next")
        # Verify it's valid YAML that can be parsed
        self.assertIsNotNone(yaml_dict)

        # Test from_pretty (step name with colon -> ID)
        restored_content = FlowStep.from_pretty(
            pretty_content,
            file_path="flows/test_flow_main/steps/test_step.yaml",
            resource_mappings=resource_mappings,
        )
        restored_yaml = yaml.safe_load(restored_content)
        self.assertEqual(restored_yaml["conditions"][0]["child_step"], "step-2")

    def test_validate_flow_step(self):
        """Test validation of flow step."""
        resource_mappings = [
            ResourceMapping(
                resource_id="flow-123",
                resource_name="Test Flow",
                resource_type=FlowConfig,
                file_path="flows/test_flow/flow_config.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            )
        ]
        self.assertIsNone(TEST_FLOW_STEP.validate(resource_mappings=resource_mappings))

        # Test with empty prompt
        invalid_step = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Test Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.ADVANCED_STEP,
            asr_biasing=None,
            dtmf_config=None,
            conditions=[],
            prompt=None,
            position={"x": 0.0, "y": 0.0},
        )
        with self.assertRaises(ValueError) as cm:
            invalid_step.validate(resource_mappings=resource_mappings)
        self.assertIn("Prompt cannot be empty.", str(cm.exception))

        # Test with missing flow config
        invalid_step = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Test Step",
            flow_id="missing-flow",
            flow_name="Test Flow",
            step_type=StepType.ADVANCED_STEP,
            asr_biasing=None,
            dtmf_config=None,
            conditions=[],
            prompt="Test prompt",
            position={"x": 0.0, "y": 0.0},
        )
        with self.assertRaises(ValueError) as cm:
            invalid_step.validate(resource_mappings=resource_mappings)
        self.assertIn("Flow config not found.", str(cm.exception))

        # Test default step cannot reference functions
        default_step = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Test Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.DEFAULT_STEP,
            asr_biasing=None,
            dtmf_config=None,
            conditions=[],
            prompt="Use {{fn:func-123}}",
            position={"x": 0.0, "y": 0.0},
        )
        with self.assertRaises(ValueError) as cm:
            default_step.validate(resource_mappings=resource_mappings)
        self.assertIn("Default steps cannot reference functions.", str(cm.exception))

        # Test with invalid extracted entities
        invalid_step = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Test Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.DEFAULT_STEP,
            asr_biasing=None,
            dtmf_config=None,
            conditions=[],
            prompt="Hello, how can I help you?",
            position={"x": 0.0, "y": 0.0},
            extracted_entities=["customer_name"],
        )
        with self.assertRaises(ValueError) as cm:
            invalid_step.validate(resource_mappings=resource_mappings)
        self.assertIn("Requested entity 'customer_name' not found.", str(cm.exception))

    def test_flow_step_name_must_match_pattern(self):
        """Test flow step name must match allowed pattern (letters, numbers, _ & , / . -)."""
        resource_mappings = [
            ResourceMapping(
                resource_id="flow-123",
                resource_name="Test Flow",
                resource_type=FlowConfig,
                file_path="flows/test_flow/flow_config.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            )
        ]
        for valid_name in ("Test Step", "Step_1", "Step & 2", "Step 1, 2", "a/b", "v1.0", "café"):
            step = FlowStep(
                resource_id="flow-123_step-1",
                step_id="step-1",
                name=valid_name,
                flow_id="flow-123",
                flow_name="Test Flow",
                step_type=StepType.ADVANCED_STEP,
                asr_biasing=None,
                dtmf_config=None,
                conditions=[],
                prompt="Prompt",
                position={"x": 0.0, "y": 0.0},
            )
            step.validate(resource_mappings=resource_mappings)

        for invalid_name in ("Step#1", "Step@2", "Step\n", "Step(two)"):
            step = FlowStep(
                resource_id="flow-123_step-1",
                step_id="step-1",
                name=invalid_name,
                flow_id="flow-123",
                flow_name="Test Flow",
                step_type=StepType.ADVANCED_STEP,
                asr_biasing=None,
                dtmf_config=None,
                conditions=[],
                prompt="Prompt",
                position={"x": 0.0, "y": 0.0},
            )
            with self.assertRaises(ValueError) as cm:
                step.validate(resource_mappings=resource_mappings)
            self.assertIn("Name must contain only", str(cm.exception))

    def test_validate_conditions(self):
        """Test validation of flow step conditions."""
        # Create resource mappings with correct format (flow_name_step_id)
        resource_mappings_with_correct_format = [
            ResourceMapping(
                resource_id="flow-123",
                resource_name="Test Flow",
                resource_type=FlowConfig,
                file_path="flows/test_flow/flow_config.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            ),
            ResourceMapping(
                resource_id="Test Flow_step-2",  # Format: flow_name_step_id
                resource_name="Step 2",
                resource_type=FlowStep,
                file_path="flows/test_flow/steps/step_2.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            ),
        ]

        # Test with valid condition
        # child_step should match the step_id part after removing flow_name prefix from resource_id
        valid_condition = Condition(
            resource_id="cond-1",
            name="Valid Condition",
            description="A valid condition",
            condition_type=ConditionType.STEP,
            child_step="step-2",
            step_id="step-1",
            flow_id="flow-123",
            required_entities=[],
            position={"x": 0.0, "y": 0.0},
        )
        self.assertIsNone(
            valid_condition.validate(
                resource_mappings=resource_mappings_with_correct_format
            )
        )

        # Test with empty name
        invalid_condition = Condition(
            resource_id="cond-2",
            name="",
            description="Invalid condition",
            condition_type=ConditionType.STEP,
            child_step="step-2",
            step_id="step-1",
            flow_id="flow-123",
            required_entities=[],
            position={"x": 0.0, "y": 0.0},
        )
        with self.assertRaises(ValueError) as cm:
            invalid_condition.validate(
                resource_mappings=resource_mappings_with_correct_format
            )
        self.assertIn("Condition name cannot be empty.", str(cm.exception))

        # Test with missing child step
        invalid_condition = Condition(
            resource_id="cond-3",
            name="Invalid Condition",
            description="Missing child step",
            condition_type=ConditionType.STEP,
            child_step="missing-step",
            step_id="step-1",
            flow_id="flow-123",
            required_entities=[],
            position={"x": 0.0, "y": 0.0},
        )
        with self.assertRaises(ValueError) as cm:
            invalid_condition.validate(
                resource_mappings=resource_mappings_with_correct_format
            )
        self.assertIn("Step 'missing-step' not found", str(cm.exception))

        # Test exit flow condition (no child step required)
        exit_condition = Condition(
            resource_id="cond-4",
            name="Exit Flow",
            description="Exit the flow",
            condition_type=ConditionType.EXIT_FLOW,
            child_step="",
            step_id="step-1",
            flow_id="flow-123",
            required_entities=[],
            position={"x": 0.0, "y": 0.0},
        )
        self.assertIsNone(
            exit_condition.validate(
                resource_mappings=resource_mappings_with_correct_format
            )
        )

        # Test with missing required entities
        resource_mappings_with_entities = resource_mappings_with_correct_format + [
            ResourceMapping(
                resource_id="entity-1",
                resource_name="Entity 1",
                resource_type=Entity,
                file_path="entities/entity_1.yaml",
                resource_prefix=None,
                flow_name=None,
            ),
        ]
        condition_with_missing_entities = Condition(
            resource_id="cond-5",
            name="Condition with Missing Entities",
            description="A condition with missing required entities",
            condition_type=ConditionType.STEP,
            child_step="step-2",
            step_id="step-1",
            flow_id="flow-123",
            required_entities=["entity-1", "entity-2"],  # entity-2 is missing
            position={"x": 0.0, "y": 0.0},
        )
        with self.assertRaises(ValueError) as cm:
            condition_with_missing_entities.validate(
                resource_mappings=resource_mappings_with_entities
            )
        self.assertIn("Required entities not found: {'entity-2'}", str(cm.exception))

        # Test with all required entities present
        resource_mappings_with_all_entities = resource_mappings_with_correct_format + [
            ResourceMapping(
                resource_id="entity-1",
                resource_name="Entity 1",
                resource_type=Entity,
                file_path="entities/entity_1.yaml",
                resource_prefix=None,
                flow_name=None,
            ),
            ResourceMapping(
                resource_id="entity-2",
                resource_name="Entity 2",
                resource_type=Entity,
                file_path="entities/entity_2.yaml",
                resource_prefix=None,
                flow_name=None,
            ),
        ]
        condition_with_all_entities = Condition(
            resource_id="cond-6",
            name="Condition with All Entities",
            description="A condition with all required entities present",
            condition_type=ConditionType.STEP,
            child_step="step-2",
            step_id="step-1",
            flow_id="flow-123",
            required_entities=["entity-1", "entity-2"],
            position={"x": 0.0, "y": 0.0},
        )
        self.assertIsNone(
            condition_with_all_entities.validate(
                resource_mappings=resource_mappings_with_all_entities
            )
        )

    def test_get_new_updated_deleted_subresources(self):
        """Test get_new_updated_deleted_subresources for flow step.

        Advanced steps only check ASR/DTMF (updates only).
        Default steps only check conditions (new/updated/deleted).
        """
        # ===== ADVANCED STEP TESTS (ASR/DTMF only, updates only) =====

        # Test Advanced step with no old resource
        new, updated, deleted = TEST_FLOW_STEP.get_new_updated_deleted_subresources(
            old_resource=None
        )
        self.assertEqual(len(new), 0)
        self.assertEqual(len(updated), 0)  # No old_resource, so no updates
        self.assertEqual(len(deleted), 0)

        # Test Advanced step with same resource (no changes)
        new, updated, deleted = TEST_FLOW_STEP.get_new_updated_deleted_subresources(
            old_resource=TEST_FLOW_STEP
        )
        self.assertEqual(len(new), 0)
        self.assertEqual(len(updated), 0)  # ASR/DTMF unchanged
        self.assertEqual(len(deleted), 0)

        # Test Advanced step: ASR biasing changed (update)
        new_asr = ASRBiasing(
            alphanumeric=True,
            name_spelling=False,
            numeric=True,
            party_size=False,
            precise_date=False,
            relative_date=False,
            single_number=False,
            time=False,
            yes_no=False,
            address=False,
            custom_keywords=["keyword1"],
            is_enabled=True,
            step_id="step-1",
            flow_id="flow-123",
        )

        step_with_asr = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Test Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.ADVANCED_STEP,
            asr_biasing=new_asr,
            dtmf_config=None,
            conditions=[],
            prompt="Test prompt",
            position={"x": 0.0, "y": 0.0},
        )

        new, updated, deleted = step_with_asr.get_new_updated_deleted_subresources(
            old_resource=TEST_FLOW_STEP
        )
        self.assertEqual(len(new), 0)  # Advanced steps don't have "new" ASR/DTMF
        self.assertEqual(len(updated), 1)  # ASR changed
        self.assertEqual(updated[0].resource_id, "flow-123.step-1")
        self.assertEqual(updated[0].command_type, "flow_step_asr_config")
        self.assertEqual(
            len(deleted), 0
        )  # Advanced steps don't have "deleted" ASR/DTMF

        # Test Advanced step: DTMF config changed (update)
        new_dtmf = DTMFConfig(
            is_enabled=True,
            inter_digit_timeout=5,
            max_digits=4,
            end_key="#",
            collect_while_agent_speaking=False,
            is_pii=False,
            step_id="step-1",
            flow_id="flow-123",
        )

        step_with_dtmf = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Test Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.ADVANCED_STEP,
            asr_biasing=None,
            dtmf_config=new_dtmf,
            conditions=[],
            prompt="Test prompt",
            position={"x": 0.0, "y": 0.0},
        )

        new, updated, deleted = step_with_dtmf.get_new_updated_deleted_subresources(
            old_resource=TEST_FLOW_STEP
        )
        self.assertEqual(len(new), 0)  # Advanced steps don't have "new" DTMF
        self.assertEqual(len(updated), 1)  # DTMF changed
        self.assertEqual(updated[0].resource_id, "flow-123.step-1")
        self.assertEqual(updated[0].command_type, "flow_step_dtmf_config")
        self.assertEqual(updated[0].max_digits, 4)
        self.assertEqual(len(deleted), 0)  # Advanced steps don't have "deleted" DTMF

        # Test Advanced step: Both ASR and DTMF updated
        step_with_both = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Test Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.ADVANCED_STEP,
            asr_biasing=new_asr,
            dtmf_config=new_dtmf,
            conditions=[],
            prompt="Test prompt",
            position={"x": 0.0, "y": 0.0},
        )

        new, updated, deleted = step_with_both.get_new_updated_deleted_subresources(
            old_resource=TEST_FLOW_STEP
        )
        self.assertEqual(len(new), 0)
        self.assertEqual(len(updated), 2)  # Both ASR and DTMF updated
        updated_types = {u.command_type for u in updated}
        self.assertIn("flow_step_asr_config", updated_types)
        self.assertIn("flow_step_dtmf_config", updated_types)
        self.assertEqual(len(deleted), 0)

        # ===== DEFAULT STEP TESTS (Conditions only, new/updated/deleted) =====

        # Test Default step with no old resource
        default_step_empty = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Test Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.DEFAULT_STEP,
            asr_biasing=None,
            dtmf_config=None,
            conditions=[],
            prompt="Test prompt",
            position={"x": 0.0, "y": 0.0},
        )

        new, updated, deleted = default_step_empty.get_new_updated_deleted_subresources(
            old_resource=None
        )
        self.assertEqual(len(new), 0)
        self.assertEqual(len(updated), 0)
        self.assertEqual(len(deleted), 0)

        # Test Default step: New condition
        new_condition = Condition(
            resource_id="cond-1",
            name="New Condition",
            description="A new condition",
            condition_type=ConditionType.STEP,
            child_step="step-2",
            step_id="step-1",
            flow_id="flow-123",
            required_entities=[],
            position={"x": 0.0, "y": 0.0},
        )

        step_with_condition = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Test Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.DEFAULT_STEP,
            asr_biasing=None,
            dtmf_config=None,
            conditions=[new_condition],
            prompt="Test prompt",
            position={"x": 0.0, "y": 0.0},
        )

        new, updated, deleted = (
            step_with_condition.get_new_updated_deleted_subresources(
                old_resource=default_step_empty
            )
        )
        self.assertEqual(len(new), 1)  # New condition
        self.assertEqual(new[0].resource_id, "cond-1")
        self.assertEqual(new[0].command_type, "no_code_condition")
        self.assertEqual(len(updated), 0)
        self.assertEqual(len(deleted), 0)

        # Test Default step: Updated condition
        updated_condition = Condition(
            resource_id="cond-1",
            name="Updated Condition",
            description="An updated condition",
            condition_type=ConditionType.STEP,
            child_step="step-3",
            step_id="step-1",
            flow_id="flow-123",
            required_entities=["entity-1"],
            position={"x": 1.0, "y": 1.0},
        )

        step_with_updated_condition = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Test Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.DEFAULT_STEP,
            asr_biasing=None,
            dtmf_config=None,
            conditions=[updated_condition],
            prompt="Test prompt",
            position={"x": 0.0, "y": 0.0},
        )

        new, updated, deleted = (
            step_with_updated_condition.get_new_updated_deleted_subresources(
                old_resource=step_with_condition
            )
        )
        self.assertEqual(len(new), 0)
        self.assertEqual(len(updated), 1)  # Condition updated
        self.assertEqual(updated[0].resource_id, "cond-1")
        self.assertEqual(updated[0].name, "Updated Condition")
        self.assertEqual(updated[0].child_step, "step-3")
        self.assertEqual(len(deleted), 0)

        # Test Default step: Deleted condition
        new, updated, deleted = default_step_empty.get_new_updated_deleted_subresources(
            old_resource=step_with_condition
        )
        self.assertEqual(len(new), 0)
        self.assertEqual(len(updated), 0)
        self.assertEqual(len(deleted), 1)  # Condition deleted
        self.assertEqual(deleted[0].resource_id, "cond-1")

        # Test Default step: Multiple conditions (new, updated, deleted)
        condition_1 = Condition(
            resource_id="cond-1",
            name="Condition 1",
            description="Condition 1",
            condition_type=ConditionType.STEP,
            child_step="step-2",
            step_id="step-1",
            flow_id="flow-123",
            required_entities=[],
            position={"x": 0.0, "y": 0.0},
        )
        condition_2 = Condition(
            resource_id="cond-2",
            name="Condition 2",
            description="Condition 2",
            condition_type=ConditionType.STEP,
            child_step="step-3",
            step_id="step-1",
            flow_id="flow-123",
            required_entities=[],
            position={"x": 1.0, "y": 0.0},
        )
        condition_3 = Condition(
            resource_id="cond-3",
            name="Condition 3",
            description="Condition 3",
            condition_type=ConditionType.STEP,
            child_step="step-4",
            step_id="step-1",
            flow_id="flow-123",
            required_entities=[],
            position={"x": 2.0, "y": 0.0},
        )

        old_step = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Test Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.DEFAULT_STEP,
            asr_biasing=None,
            dtmf_config=None,
            conditions=[condition_1, condition_2, condition_3],
            prompt="Test prompt",
            position={"x": 0.0, "y": 0.0},
        )

        # Updated condition_1, keep condition_2, delete condition_3, add condition_4
        updated_condition_1 = Condition(
            resource_id="cond-1",
            name="Updated Condition 1",
            description="Updated Condition 1",
            condition_type=ConditionType.STEP,
            child_step="step-5",
            step_id="step-1",
            flow_id="flow-123",
            required_entities=["entity-1"],
            position={"x": 0.0, "y": 1.0},
        )
        condition_4 = Condition(
            resource_id="cond-4",
            name="Condition 4",
            description="Condition 4",
            condition_type=ConditionType.STEP,
            child_step="step-6",
            step_id="step-1",
            flow_id="flow-123",
            required_entities=[],
            position={"x": 3.0, "y": 0.0},
        )

        new_step = FlowStep(
            resource_id="flow-123_step-1",
            step_id="step-1",
            name="Test Step",
            flow_id="flow-123",
            flow_name="Test Flow",
            step_type=StepType.DEFAULT_STEP,
            asr_biasing=None,
            dtmf_config=None,
            conditions=[updated_condition_1, condition_2, condition_4],
            prompt="Test prompt",
            position={"x": 0.0, "y": 0.0},
        )

        new, updated, deleted = new_step.get_new_updated_deleted_subresources(
            old_resource=old_step
        )
        self.assertEqual(len(new), 1)  # condition_4 is new
        self.assertEqual(new[0].resource_id, "cond-4")
        self.assertEqual(len(updated), 1)  # condition_1 is updated
        self.assertEqual(updated[0].resource_id, "cond-1")
        self.assertEqual(updated[0].name, "Updated Condition 1")
        self.assertEqual(len(deleted), 1)  # condition_3 is deleted
        self.assertEqual(deleted[0].resource_id, "cond-3")

    def test_read_local_resource_advanced_step(self):
        """Test reading a flow step from a YAML file with ASR and DTMF."""
        test_file_pretty_content = """step_type: advanced_step
name: Test Step
prompt: Hello, how can I help you?
asr_biasing:
  is_enabled: true
  alphanumeric: true
  name_spelling: false
  numeric: true
  custom_keywords:
    - keyword1
    - keyword2
dtmf_config:
  is_enabled: true
  inter_digit_timeout: 5
  max_digits: 4
  end_key: "#"
  collect_while_agent_speaking: false
  is_pii: false
"""

        resource_mappings = [
            ResourceMapping(
                resource_id="flow-123",
                resource_name="Test Flow",
                resource_type=FlowConfig,
                file_path="flows/test_flow/flow_config.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            )
        ]

        with mock_read_from_file(test_file_pretty_content):
            result = FlowStep.read_local_resource(
                file_path="flows/test_flow/steps/test_step.yaml",
                resource_id="flow-123_step-1",
                resource_name="test_step",
                resource_mappings=resource_mappings,
            )

            self.assertEqual(result.resource_id, "flow-123_step-1")
            self.assertEqual(result.name, "Test Step")
            self.assertEqual(result.flow_id, "flow-123")
            self.assertEqual(result.flow_name, "Test Flow")
            self.assertEqual(result.step_type, StepType.ADVANCED_STEP)
            self.assertEqual(result.prompt, "Hello, how can I help you?")
            # Verify ASR biasing
            self.assertIsNotNone(result.asr_biasing)
            self.assertEqual(result.asr_biasing.is_enabled, True)
            self.assertEqual(result.asr_biasing.alphanumeric, True)
            self.assertEqual(
                result.asr_biasing.custom_keywords, ["keyword1", "keyword2"]
            )
            # Verify DTMF config
            self.assertIsNotNone(result.dtmf_config)
            self.assertEqual(result.dtmf_config.is_enabled, True)
            self.assertEqual(result.dtmf_config.max_digits, 4)
            self.assertEqual(result.dtmf_config.end_key, "#")

    def test_read_local_resource_default_step(self):
        """Test reading a flow step with conditions."""
        test_file_pretty_content = """step_type: default_step
name: Test Step
prompt: Please select an option
conditions:
  - name: Option 1
    condition_type: step_condition
    description: Go to step 2
    child_step: Step 2
    required_entities: []
"""

        resource_mappings = [
            ResourceMapping(
                resource_id="flow-123",
                resource_name="Test Flow",
                resource_type=FlowConfig,
                file_path="flows/test_flow/flow_config.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            ),
            ResourceMapping(
                resource_id="Test Flow_step-2",
                resource_name="Step 2",
                resource_type=FlowStep,
                file_path="flows/test_flow/steps/step_2.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            ),
        ]

        # Mock the child step file to avoid recursion
        step_2_content = """step_type: advanced_step
name: Step 2
prompt: This is step 2
"""
        file_content_map = {
            "flows/test_flow/steps/test_step.yaml": test_file_pretty_content,
            "flows/test_flow/steps/step_2.yaml": step_2_content,
        }

        with mock_read_from_file(file_content_map):
            result = FlowStep.read_local_resource(
                file_path="flows/test_flow/steps/test_step.yaml",
                resource_id="flow-123_step-1",
                resource_name="test_step",
                resource_mappings=resource_mappings,
            )

            self.assertEqual(result.resource_id, "flow-123_step-1")
            self.assertEqual(len(result.conditions), 1)
            self.assertEqual(result.conditions[0].name, "Option 1")
            self.assertEqual(result.conditions[0].child_step, "step-2")
            self.assertEqual(result.conditions[0].condition_type, ConditionType.STEP)

    def test_read_local_resource_conditions(self):
        """Test reading a flow step with multiple condition types."""
        test_file_pretty_content = """step_type: default_step
name: Test Step
prompt: Please select an option
conditions:
  - name: Go to Advanced Step
    condition_type: step_condition
    description: Navigate to an advanced step
    child_step: Advanced Step
    required_entities: []
  - name: Go to Default Step
    condition_type: step_condition
    description: Navigate to a default step
    child_step: Default Step
    required_entities: [entity-1]
  - name: Go to Function Step
    condition_type: step_condition
    description: Navigate to a function step
    child_step: function_step
    required_entities: []
  - name: Exit Flow
    condition_type: exit_flow_condition
    description: Exit the flow
    required_entities: []
"""

        # Create known conditions with specific resource IDs
        # Note: Both step_condition types map to "step_condition" in YAML
        # The actual type (STEP vs NO_CODE_STEP) is determined by child_step_type
        known_conditions = [
            Condition(
                resource_id="cond-advanced-123",
                name="Go to Advanced Step",
                description="Navigate to an advanced step",
                condition_type=ConditionType.STEP,  # Routes to Advanced Step
                child_step="advanced-step-1",
                step_id="step-1",
                flow_id="flow-123",
                required_entities=[],
                position={"x": 0.0, "y": 0.0},
            ),
            Condition(
                resource_id="cond-default-456",
                name="Go to Default Step",
                description="Navigate to a default step",
                condition_type=ConditionType.NO_CODE_STEP,  # Routes to Default Step
                child_step="default-step-1",
                step_id="step-1",
                flow_id="flow-123",
                required_entities=["entity-1"],
                position={"x": 1.0, "y": 0.0},
            ),
            Condition(
                resource_id="cond-exit-789",
                name="Exit Flow",
                description="Exit the flow",
                condition_type=ConditionType.EXIT_FLOW,
                child_step="",
                step_id="step-1",
                flow_id="flow-123",
                required_entities=[],
                position={"x": 2.0, "y": 0.0},
                exit_flow_position={"x": 10.0, "y": 10.0},
            ),
            Condition(
                resource_id="cond-function-step-123",
                name="Go to Function Step",
                description="Navigate to a function step",
                condition_type=ConditionType.FUNCTION_STEP,
                child_step="function-step-1",
                step_id="step-1",
                flow_id="flow-123",
            ),
        ]

        resource_mappings = [
            ResourceMapping(
                resource_id="flow-123",
                resource_name="Test Flow",
                resource_type=FlowConfig,
                file_path="flows/test_flow/flow_config.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            ),
            ResourceMapping(
                resource_id="Test Flow_advanced-step-1",
                resource_name="Advanced Step",
                resource_type=FlowStep,
                file_path="flows/test_flow/steps/advanced_step.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            ),
            ResourceMapping(
                resource_id="Test Flow_default-step-1",
                resource_name="Default Step",
                resource_type=FlowStep,
                file_path="flows/test_flow/steps/default_step.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            ),
            ResourceMapping(
                resource_id="Test Flow_function-step-1",
                resource_name="function_step",
                resource_type=FunctionStep,
                file_path="flows/test_flow/function_steps/function_step.py",
                resource_prefix=None,
                flow_name="Test Flow",
            ),
        ]

        # Mock files for child steps so their step_type can be determined
        advanced_step_content = """step_type: advanced_step
name: Advanced Step
prompt: This is an advanced step
"""
        default_step_content = """step_type: default_step
name: Default Step
prompt: This is a default step
"""

        file_content_map = {
            "flows/test_flow/steps/test_step.yaml": test_file_pretty_content,
            "flows/test_flow/steps/advanced_step.yaml": advanced_step_content,
            "flows/test_flow/steps/default_step.yaml": default_step_content,
        }

        with mock_read_from_file(file_content_map):
            result = FlowStep.read_local_resource(
                file_path="flows/test_flow/steps/test_step.yaml",
                resource_id="flow-123_step-1",
                resource_name="test_step",
                resource_mappings=resource_mappings,
                known_conditions=known_conditions,
            )

            self.assertEqual(result.resource_id, "flow-123_step-1")
            self.assertEqual(len(result.conditions), 4)

            condition_by_resource_id = {c.resource_id: c for c in result.conditions}

            # Verify step condition that routes to Advanced Step
            # When child_step is an Advanced Step, condition_type becomes STEP
            advanced_cond = condition_by_resource_id["cond-advanced-123"]
            self.assertEqual(advanced_cond.resource_id, "cond-advanced-123")
            self.assertEqual(advanced_cond.name, "Go to Advanced Step")
            self.assertEqual(advanced_cond.condition_type, ConditionType.STEP)
            self.assertEqual(advanced_cond.child_step, "advanced-step-1")
            self.assertEqual(advanced_cond.description, "Navigate to an advanced step")
            self.assertEqual(advanced_cond.required_entities, [])

            # Verify step condition that routes to Default Step
            # When child_step is a Default Step, condition_type becomes NO_CODE_STEP
            default_cond = condition_by_resource_id["cond-default-456"]
            self.assertEqual(default_cond.resource_id, "cond-default-456")
            self.assertEqual(default_cond.name, "Go to Default Step")
            self.assertEqual(default_cond.condition_type, ConditionType.NO_CODE_STEP)
            self.assertEqual(default_cond.child_step, "default-step-1")
            self.assertEqual(default_cond.required_entities, ["entity-1"])
            self.assertEqual(default_cond.description, "Navigate to a default step")

            # Verify function step condition
            function_step_cond = condition_by_resource_id["cond-function-step-123"]
            self.assertEqual(function_step_cond.resource_id, "cond-function-step-123")
            self.assertEqual(function_step_cond.name, "Go to Function Step")
            self.assertEqual(function_step_cond.condition_type, ConditionType.FUNCTION_STEP)
            self.assertEqual(function_step_cond.child_step, "function-step-1")
            self.assertEqual(function_step_cond.required_entities, [])
            self.assertEqual(function_step_cond.description, "Navigate to a function step")

            # Verify exit flow condition
            # Exit flow condition name doesn't contain step names, so it matches known_condition
            exit_cond = condition_by_resource_id["cond-exit-789"]
            self.assertEqual(exit_cond.resource_id, "cond-exit-789")
            self.assertEqual(exit_cond.name, "Exit Flow")
            self.assertEqual(exit_cond.condition_type, ConditionType.EXIT_FLOW)
            self.assertEqual(exit_cond.exit_flow_position, {"x": 10.0, "y": 10.0})
            self.assertEqual(exit_cond.description, "Exit the flow")


class EntityTests(unittest.TestCase):
    def test_validate_entity(self):
        """Test validation of entity config fields."""
        # Test valid numeric entity
        valid_entity = Entity(
            resource_id="entity-123",
            name="test_entity",
            description="A test entity",
            entity_type=EntityType.NUMERIC,
            config={
                "has_decimal": True,
                "has_range": False,
                "min": 0.0,
                "max": 100.0,
            },
        )
        self.assertIsNone(valid_entity.validate())

        # Test invalid numeric entity - wrong type for has_decimal
        invalid_entity = Entity(
            resource_id="entity-123",
            name="test_entity",
            description="A test entity",
            entity_type=EntityType.NUMERIC,
            config={
                "has_decimal": "true",  # Should be bool, not str
                "has_range": False,
                "min": 0.0,
                "max": 100.0,
            },
        )
        with self.assertRaises(ValueError) as cm:
            invalid_entity.validate()
        self.assertIn(
            "Config field 'has_decimal' should be of type 'bool'",
            str(cm.exception),
        )

        # Test valid enum entity
        valid_enum_entity = Entity(
            resource_id="entity-456",
            name="test_enum",
            description="A test enum entity",
            entity_type=EntityType.ENUM,
            config={"options": ["option1", "option2"]},
        )
        self.assertIsNone(valid_enum_entity.validate())

        # Test invalid enum entity - wrong type for options
        invalid_enum_entity = Entity(
            resource_id="entity-456",
            name="test_enum",
            description="A test enum entity",
            entity_type=EntityType.ENUM,
            config={"options": "not a list"},  # Should be list, not str
        )
        with self.assertRaises(ValueError) as cm:
            invalid_enum_entity.validate()
        self.assertIn(
            "Config field 'options' should be of type 'list'",
            str(cm.exception),
        )

        # Test valid alphanumeric entity
        valid_alphanumeric_entity = Entity(
            resource_id="entity-789",
            name="test_alphanumeric",
            description="A test alphanumeric entity",
            entity_type=EntityType.ALPHANUMERIC,
            config={
                "enabled": True,
                "validation_type": "regex",
                "regular_expression": "[a-z]+",
            },
        )
        self.assertIsNone(valid_alphanumeric_entity.validate())

        # Test invalid alphanumeric entity - wrong type for enabled
        invalid_alphanumeric_entity = Entity(
            resource_id="entity-789",
            name="test_alphanumeric",
            description="A test alphanumeric entity",
            entity_type=EntityType.ALPHANUMERIC,
            config={
                "enabled": "yes",  # Should be bool, not str
                "validation_type": "regex",
                "regular_expression": "[a-z]+",
            },
        )
        with self.assertRaises(ValueError) as cm:
            invalid_alphanumeric_entity.validate()
        self.assertIn(
            "Config field 'enabled' should be of type 'bool'",
            str(cm.exception),
        )

        # Test entity with missing config field (should pass - fields are optional)
        entity_without_config = Entity(
            resource_id="entity-999",
            name="test_entity",
            description="A test entity",
            entity_type=EntityType.FREE_TEXT,
            config={},  # FREE_TEXT has no required config fields
        )
        self.assertIsNone(entity_without_config.validate())


TEST_FUNCTION_STEP_CODE = """def process_data(conv: Conversation, flow: Flow):
    \"\"\"Process some data.\"\"\"
    return "processed"
"""

TEST_FUNCTION_STEP_RAW = """@func_latency_control(delay_before_responses_start=3, silence_after_each_response=0)
def process_data(conv: Conversation, flow: Flow):
    \"\"\"Process some data.\"\"\"
    return "processed"
"""

TEST_FUNCTION_STEP_CODE_PRETTY = """from _gen import *  # <AUTO GENERATED>


@func_latency_control(delay_before_responses_start=3, silence_after_each_response=0)
def process_data(conv: Conversation, flow: Flow):
    \"\"\"Process some data.\"\"\"
    return "processed"
"""

TEST_FUNCTION_STEP = FunctionStep(
    resource_id="test_flow_process_data",
    step_id="process_data",
    name="process_data",
    flow_id="test_flow",
    flow_name="Test Flow",
    function_id="FUNCTION-12345678",
    code=TEST_FUNCTION_STEP_CODE,
    parameters=[],
    latency_control=FunctionLatencyControl(enabled=True, initial_delay=3, interval=0, delay_responses=[]),
    position={"x": 0.0, "y": 0.0},
)


class FunctionStepTests(unittest.TestCase):
    def test_get_raw(self):
        """Test that raw property returns the code with latency control decorator."""
        self.assertEqual(TEST_FUNCTION_STEP.raw, TEST_FUNCTION_STEP_RAW)

    def test_to_pretty(self):
        """Test converting function step to pretty format."""
        pretty_code = TEST_FUNCTION_STEP.to_pretty(resource_mappings=[])
        self.assertEqual(pretty_code, TEST_FUNCTION_STEP_CODE_PRETTY)

    def test_read_local_resource(self):
        """Test reading a function step from a Python file."""
        test_file_pretty_content = TEST_FUNCTION_STEP_CODE_PRETTY

        resource_mappings = [
            ResourceMapping(
                resource_id="test_flow",
                resource_name="Test Flow",
                resource_type=FlowConfig,
                file_path="flows/test_flow/flow_config.yaml",
                resource_prefix=None,
                flow_name="Test Flow",
            )
        ]

        with mock_read_from_file(test_file_pretty_content):
            result = FunctionStep.read_local_resource(
                file_path="flows/test_flow/function_steps/process_data.py",
                resource_id="Test Flow_process_data",
                resource_name="process_data",
                resource_mappings=resource_mappings,
                known_latency_control={},
            )

            self.assertEqual(result.resource_id, "Test Flow_process_data")
            self.assertEqual(result.step_id, "process_data")
            self.assertEqual(result.name, "process_data")
            self.assertEqual(result.flow_id, "test_flow")
            self.assertEqual(result.flow_name, "Test Flow")
            self.assertEqual(result.step_type, StepType.FUNCTION_STEP)
            self.assertEqual(result.function_type, FunctionType.FUNCTION_STEP)
            self.assertEqual(result.code, TEST_FUNCTION_STEP_CODE)
            self.assertEqual(result.parameters, [])
            self.assertIsNotNone(result.function_id)
            self.assertRegex(result.function_id, r"^FUNCTION-[a-f0-9]{8}$")


class ExperimentalConfigTests(unittest.TestCase):
    def test_validate_experimental_config(self):
        """Test validation of experimental config."""
        experimental_config = ExperimentalConfig(
            resource_id="experimental-config-123",
            name="experimental_config",
            config={
                "asr": {
                    "provider": "riva",
                    "model": "poly-latency",
                    "language": "en-GB"
                }
            }
        )
        self.assertIsNone(experimental_config.validate())

    def test_invalid_experimental_config(self):
        """Test validation of experimental config."""
        experimental_config = ExperimentalConfig(
            resource_id="experimental-config-123",
            name="experimental_config",
            config={
                "asr": {
                    "provider": "deepgram",
                    "model": "nova-2",
                    "language": "en"
                }
            }
        )
        with self.assertRaises(ValidationError) as cm:
            experimental_config.validate()
        self.assertIn(
            "'deepgram' is not one of",
            str(cm.exception),
        )


TEST_SMS_TEMPLATE_1 = SMSTemplate(
    resource_id="sms-template-123",
    name="test_template_1",
    text="This is a test template",
    env_phone_numbers=EnvPhoneNumbers(
        sandbox="",
        pre_release="",
        live="+447700102347",
    ),
)

TEST_SMS_TEMPLATE_2 = SMSTemplate(
    resource_id="sms-template-456",
    name="test_template_2",
    text="This is a second test template",
    env_phone_numbers=EnvPhoneNumbers(
        sandbox="+447700102348",
        pre_release="+447700102349",
        live="+447700102347",
    ),
)

SMS_TEMPLATES_RAW = """name: test_template_1
text: This is a test template
env_phone_numbers:
  sandbox: ''
  pre_release: ''
  live: '+447700102347'
"""


class SMSTemplateTests(unittest.TestCase):
    def setUp(self):
        MultiResourceYamlResource._file_cache.clear()

    def test_get_raw(self):
        """Test that raw property returns correct YAML representation."""
        self.assertEqual(TEST_SMS_TEMPLATE_1.raw, SMS_TEMPLATES_RAW)

    def test_to_pretty(self):
        """Test converting SMS templates to pretty format."""
        pretty_content = TEST_SMS_TEMPLATE_1.to_pretty()
        # Should return YAML with resource IDs replaced (if any)
        self.assertIn("test_template_1", pretty_content)
        self.assertIn("This is a test template", pretty_content)

    def test_convert_and_unconvert_sms_templates(self):
        """Test roundtrip conversion: to_pretty -> from_pretty."""
        converted_templates = TEST_SMS_TEMPLATE_1.to_pretty()
        reverted_templates = SMSTemplate.from_pretty(converted_templates)
        self.assertEqual(reverted_templates, TEST_SMS_TEMPLATE_1.raw)

    def test_read_local_resource(self):
        """Test reading a single SMS template from the multi-resource YAML file."""
        test_file_pretty_content = """sms_templates:
- name: test_template_1
  text: This is a test template
  env_phone_numbers:
    sandbox: ''
    pre_release: ''
    live: '+447700102347'
- name: test_template_2
  text: This is a second test template
  env_phone_numbers:
    sandbox: '+447700102348'
    pre_release: '+447700102349'
    live: '+447700102347'
"""

        def exists_sms(path):
            return True if "sms_templates.yaml" in str(path) else os.path.exists(path)

        def isfile_sms(path):
            return True if "sms_templates.yaml" in str(path) else os.path.isfile(path)

        def getmtime_sms(path):
            return 1.0 if "sms_templates.yaml" in str(path) else os.path.getmtime(path)

        with mock_read_from_file(test_file_pretty_content):
            with unittest.mock.patch(
                "poly.resources.resource.os.path.exists", side_effect=exists_sms
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.isfile", side_effect=isfile_sms
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.getmtime", side_effect=getmtime_sms
            ):
                result = SMSTemplate.read_local_resource(
                    file_path="config/sms_templates.yaml/sms_templates/test_template_1",
                    resource_id="sms-template-123",
                    resource_name="test_template_1",
                )

            self.assertEqual(result.resource_id, "sms-template-123")
            self.assertEqual(result.name, "test_template_1")
            self.assertEqual(result.text, "This is a test template")
            self.assertEqual(result.env_phone_numbers.live, "+447700102347")

    def test_discover_resources(self):
        """Test discovering SMS templates from the multi-resource YAML file."""
        test_file_content = """sms_templates:
- name: template_a
  text: Template A text
  env_phone_numbers:
    sandbox: ''
    pre_release: ''
    live: '+447700102347'
- name: template_b
  text: Template B text
  env_phone_numbers:
    sandbox: ''
    pre_release: ''
    live: '+447700102347'
"""
        base_path = "."
        sms_templates_path = os.path.join(base_path, "config", "sms_templates.yaml")
        def exists_sms(path):
            return True if "sms_templates.yaml" in str(path) else os.path.exists(path)

        def isfile_sms(path):
            return True if "sms_templates.yaml" in str(path) else os.path.isfile(path)

        def getmtime_sms(path):
            return 1.0 if "sms_templates.yaml" in str(path) else os.path.getmtime(path)

        with mock_read_from_file({sms_templates_path: test_file_content}):
            with unittest.mock.patch(
                "poly.resources.sms.os.path.exists", side_effect=exists_sms
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.exists", side_effect=exists_sms
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.isfile", side_effect=isfile_sms
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.getmtime", side_effect=getmtime_sms
            ):
                discovered = SMSTemplate.discover_resources(base_path)
        self.assertEqual(len(discovered), 2)
        self.assertIn(os.path.join(sms_templates_path, "sms_templates", "template_a"), discovered)
        self.assertIn(os.path.join(sms_templates_path, "sms_templates", "template_b"), discovered)

    def test_discover_resources_encodes_slash_in_template_name(self):
        """Templates with '/' in the name should be discovered with path-safe encoding."""
        test_file_content = """sms_templates:
- name: merch/vouchers
  text: Voucher template
  env_phone_numbers:
    sandbox: ''
    pre_release: ''
    live: '+447700102347'
"""
        base_path = "."
        sms_templates_path = os.path.join(base_path, "config", "sms_templates.yaml")

        def exists_sms(path):
            return True if "sms_templates.yaml" in str(path) else os.path.exists(path)

        def isfile_sms(path):
            return True if "sms_templates.yaml" in str(path) else os.path.isfile(path)

        def getmtime_sms(path):
            return 1.0 if "sms_templates.yaml" in str(path) else os.path.getmtime(path)

        with mock_read_from_file({sms_templates_path: test_file_content}):
            with unittest.mock.patch(
                "poly.resources.sms.os.path.exists", side_effect=exists_sms
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.exists", side_effect=exists_sms
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.isfile", side_effect=isfile_sms
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.getmtime", side_effect=getmtime_sms
            ):
                discovered = SMSTemplate.discover_resources(base_path)
        self.assertEqual(len(discovered), 1)
        self.assertIn(
            os.path.join(sms_templates_path, "sms_templates", "merch_vouchers"),
            discovered,
            "Slash in template name should be encoded via clean_name in discovered path",
        )

    def test_sms_template_with_slash_in_name_saves_correctly(self):
        """Templates with '/' in the name (e.g. merch/vouchers) should save without NotADirectoryError."""
        import tempfile

        base_path = tempfile.mkdtemp()
        sms_file = os.path.join(base_path, "config", "sms_templates.yaml")
        os.makedirs(os.path.dirname(sms_file), exist_ok=True)
        initial_content = """sms_templates:
- name: merch/vouchers
  text: Voucher template
  env_phone_numbers:
    sandbox: ''
    pre_release: ''
    live: '+447700102347'
"""
        with open(sms_file, "w") as f:
            f.write(initial_content)
        try:
            template = SMSTemplate.read_local_resource(
                file_path=os.path.join(sms_file, "sms_templates", "merch_vouchers"),
                resource_id="id-1",
                resource_name="merch/vouchers",
            )
            self.assertEqual(template.name, "merch/vouchers")
            template.text = "Updated voucher template"
            template.save(base_path)  # Should not raise NotADirectoryError
            with open(sms_file) as f:
                content = f.read()
            self.assertIn("merch/vouchers", content)
            self.assertIn("Updated voucher template", content)
        finally:
            import shutil

            shutil.rmtree(base_path, ignore_errors=True)

    def test_validate_sms_template(self):
        """Test validation of SMS template."""
        self.assertIsNone(TEST_SMS_TEMPLATE_1.validate())

        # Test with empty name
        invalid_template = SMSTemplate(
            resource_id="sms-template-999",
            name="",
            text="Template text",
            env_phone_numbers=EnvPhoneNumbers(
                sandbox="",
                pre_release="",
                live="+447700102347",
            ),
        )
        with self.assertRaises(ValueError) as cm:
            invalid_template.validate()
        self.assertIn("Name is required", str(cm.exception))

        # Test with empty text
        invalid_template = SMSTemplate(
            resource_id="sms-template-999",
            name="test_template",
            text="",
            env_phone_numbers=EnvPhoneNumbers(
                sandbox="",
                pre_release="",
                live="+447700102347",
            ),
        )
        with self.assertRaises(ValueError) as cm:
            invalid_template.validate()
        self.assertIn("Text is required", str(cm.exception))

        # Test with None env_phone_numbers
        invalid_template = SMSTemplate(
            resource_id="sms-template-999",
            name="test_template",
            text="Template text",
            env_phone_numbers=None,
        )
        with self.assertRaises(ValueError) as cm:
            invalid_template.validate()
        self.assertIn("Env phone numbers are required", str(cm.exception))

    def test_validate_variable_references(self):
        """Test validation when SMS template text references a variable."""
        default_env = EnvPhoneNumbers(
            sandbox="",
            pre_release="",
            live="+447700102347",
        )
        template_with_var = SMSTemplate(
            resource_id="sms-1",
            name="with_var",
            text="Hi {{vrbl:VAR-customer_name}}, your booking is confirmed.",
            env_phone_numbers=default_env,
        )
        with self.assertRaises(ValueError) as cm:
            template_with_var.validate(resource_mappings=[])
        self.assertIn("Invalid references: ['variables: VAR-customer_name']", str(cm.exception))

        valid_mapping = [
            ResourceMapping(
                resource_id="VAR-customer_name",
                resource_name="customer_name",
                resource_type=Variable,
                file_path="variables/customer_name",
                flow_name=None,
                resource_prefix="vrbl",
            )
        ]
        self.assertIsNone(template_with_var.validate(resource_mappings=valid_mapping))

        template_two_vars = SMSTemplate(
            resource_id="sms-2",
            name="two_vars",
            text="Hi {{vrbl:VAR-customer_name}}, order {{vrbl:VAR-order_id}}.",
            env_phone_numbers=default_env,
        )
        with self.assertRaises(ValueError) as cm:
            template_two_vars.validate(resource_mappings=valid_mapping)
        self.assertIn("Invalid references: ['variables: VAR-order_id']", str(cm.exception))

    def test_to_yaml_dict(self):
        """Test converting SMS template to YAML dictionary."""
        yaml_dict = TEST_SMS_TEMPLATE_1.to_yaml_dict()
        self.assertEqual(yaml_dict["name"], "test_template_1")
        self.assertEqual(yaml_dict["text"], "This is a test template")
        self.assertIn("env_phone_numbers", yaml_dict)
        self.assertEqual(yaml_dict["env_phone_numbers"]["live"], "+447700102347")

    def test_from_yaml(self):
        """Test creating SMS template from YAML dictionary."""
        yaml_data = {
            "name": "test_template",
            "text": "Template text",
            "env_phone_numbers": {
                "sandbox": "+447700102348",
                "pre_release": "+447700102349",
                "live": "+447700102347",
            },
        }
        template = SMSTemplate.from_yaml_dict(
            yaml_data, "sms-template-123", "test_template"
        )
        self.assertEqual(template.resource_id, "sms-template-123")
        self.assertEqual(template.name, "test_template")
        self.assertEqual(template.text, "Template text")
        self.assertEqual(template.env_phone_numbers.sandbox, "+447700102348")
        self.assertEqual(template.env_phone_numbers.pre_release, "+447700102349")
        self.assertEqual(template.env_phone_numbers.live, "+447700102347")

    def test_env_phone_numbers_pre_release_alias(self):
        """Test that preRelease alias works for pre_release field."""
        yaml_data = {
            "name": "test_template",
            "text": "Template text",
            "env_phone_numbers": {
                "sandbox": "",
                "preRelease": "+447700102349",  # Using camelCase alias
                "live": "+447700102347",
            },
        }
        template = SMSTemplate.from_yaml_dict(
            yaml_data, "sms-template-123", "test_template"
        )
        self.assertEqual(template.env_phone_numbers.pre_release, "+447700102349")


TEST_VARIANT = Variant(resource_id="VARIANT-default", name="default")
TEST_VARIANT_DEFAULT = Variant(resource_id="VARIANT-default", name="default", is_default=True)
TEST_VARIANT_ATTRIBUTE = VariantAttribute(
    resource_id="attr-customer-name",
    name="customer-name",
    mappings={"VARIANT-default": "value"},
)


class VariantTests(unittest.TestCase):
    """Tests for Variant resource."""

    def setUp(self):
        MultiResourceYamlResource._file_cache.clear()

    def test_to_yaml_dict(self):
        """Test converting variant to YAML dictionary (returns name string)."""
        self.assertEqual(TEST_VARIANT.to_yaml_dict(), {"name": "default"})
        self.assertEqual(TEST_VARIANT_DEFAULT.to_yaml_dict(), {"name": "default", "is_default": True})

    def test_from_yaml(self):
        """Test creating variant from YAML data"""
        variant = Variant.from_yaml_dict({"name": "test"}, "VARIANT-test", "test")
        self.assertEqual(variant.resource_id, "VARIANT-test")
        self.assertEqual(variant.name, "test")
        self.assertEqual(variant.is_default, False)

        variant_default: Variant = Variant.from_yaml_dict({"name": "default", "is_default": True}, "VARIANT-default", "default")
        self.assertEqual(variant_default.resource_id, "VARIANT-default")
        self.assertEqual(variant_default.name, "default")
        self.assertEqual(variant_default.is_default, True)

    def test_file_path(self):
        """Test file path property."""
        self.assertEqual(
            TEST_VARIANT.file_path,
            os.path.join("config", "variant_attributes.yaml", "variants", "default"),
        )

    def test_discover_resources(self):
        """Test discovering variants from the multi-resource YAML file."""
        test_file_content = """variants:
  - name: default
    is_default: true
  - name: production
"""
        base_path = "."
        variant_attributes_path = os.path.join(base_path, "config", "variant_attributes.yaml")

        with mock_variant_attributes_file(test_file_content, base_path):
            discovered = Variant.discover_resources(base_path)
        self.assertEqual(len(discovered), 2)
        self.assertIn(
            os.path.join(variant_attributes_path, "variants", "default"), discovered
        )
        self.assertIn(
            os.path.join(variant_attributes_path, "variants", "production"), discovered
        )

    def test_validate_duplicate_name(self):
        """Test validation fails when variant name already exists."""
        base_path = "."
        variant_attributes_path = os.path.join(base_path, "config", "variant_attributes.yaml")
        self_mapping = ResourceMapping(
            resource_id="VARIANT-default",
            resource_type=Variant,
            resource_name="default",
            file_path=os.path.join(variant_attributes_path, "variants", "default"),
            flow_name=None,
            resource_prefix=None,
        )
        duplicate_mapping = ResourceMapping(
            resource_id="VARIANT-other",
            resource_type=Variant,
            resource_name="default",
            file_path="",
            flow_name=None,
            resource_prefix=None,
        )
        with self.assertRaises(ValueError) as cm:
            TEST_VARIANT.validate(resource_mappings=[self_mapping, duplicate_mapping])
        self.assertIn("Variant default already exists", str(cm.exception))

    def test_validate_no_duplicate(self):
        """Test validation passes when no duplicate names and default variant exists."""
        base_path = "."
        variant_attributes_path = os.path.join(base_path, "config", "variant_attributes.yaml")
        test_file_content = """variants:
  - name: default
    is_default: true
  - name: production
"""
        self_mapping = ResourceMapping(
            resource_id="VARIANT-default",
            resource_type=Variant,
            resource_name="default",
            file_path=os.path.join(variant_attributes_path, "variants", "default"),
            flow_name=None,
            resource_prefix=None,
        )
        other_mapping = ResourceMapping(
            resource_id="VARIANT-other",
            resource_type=Variant,
            resource_name="production",
            file_path="",
            flow_name=None,
            resource_prefix=None,
        )

        with mock_variant_attributes_file(test_file_content, base_path):
            self.assertIsNone(
                TEST_VARIANT.validate(resource_mappings=[self_mapping, other_mapping])
            )

    def test_validate_multiple_default_variants(self):
        """Test validation fails when multiple variants have is_default true."""
        with self.assertRaises(ValueError) as cm:
            Variant.validate_collection({"variant_1": TEST_VARIANT_DEFAULT, "variant_2": TEST_VARIANT_DEFAULT})
        self.assertIn("Multiple or zero default variants detected: ['default', 'default']. One variant must be set as default.", str(cm.exception))

    def test_validate_no_default_variant(self):
        """Test validation fails when no variant has is_default true."""
        with self.assertRaises(ValueError) as cm:
            Variant.validate_collection({"variant_1": TEST_VARIANT, "variant_2": TEST_VARIANT})
        self.assertIn("Multiple or zero default variants detected: []. One variant must be set as default.", str(cm.exception))


class VariantAttributeTests(unittest.TestCase):
    """Tests for VariantAttribute resource."""

    def setUp(self):
        MultiResourceYamlResource._file_cache.clear()

    def test_to_yaml_dict(self):
        """Test converting variant attribute to YAML dictionary."""
        yaml_dict = TEST_VARIANT_ATTRIBUTE.to_yaml_dict()
        self.assertEqual(yaml_dict["name"], "customer-name")
        self.assertEqual(yaml_dict["values"], {"VARIANT-default": "value"})

    def test_from_yaml(self):
        """Test creating variant attribute from YAML dictionary."""
        yaml_dict = {
            "name": "email-address",
            "values": {"VARIANT-default": "user@example.com"},
        }
        attr = VariantAttribute.from_yaml_dict(yaml_dict, "attr-email-address")
        self.assertEqual(attr.resource_id, "attr-email-address")
        self.assertEqual(attr.name, "email-address")
        self.assertEqual(attr.mappings, {"VARIANT-default": "user@example.com"})

    def test_file_path(self):
        """Test file path property."""
        self.assertEqual(
            TEST_VARIANT_ATTRIBUTE.file_path,
            os.path.join("config", "variant_attributes.yaml", "attributes", "customer_name"),
        )

    def test_discover_resources(self):
        """Test discovering variant attributes from the multi-resource YAML file."""
        test_file_content = """variants:
  - default
attributes:
  - name: customer-name
    values:
      VARIANT-default: ""
  - name: email-address
    values:
      VARIANT-default: ""
"""
        base_path = "."
        variant_attributes_path = os.path.join(base_path, "config", "variant_attributes.yaml")

        with mock_variant_attributes_file(test_file_content, base_path):
            discovered = VariantAttribute.discover_resources(base_path)
        self.assertEqual(len(discovered), 2)
        self.assertIn(
            os.path.join(variant_attributes_path, "attributes", "customer_name"), discovered
        )
        self.assertIn(
            os.path.join(variant_attributes_path, "attributes", "email_address"), discovered
        )

    def test_read_local_resource(self):
        """Test reading a single variant attribute from the multi-resource YAML file."""
        test_file_content = """variants:
  - default
attributes:
  - name: customer-name
    values:
      VARIANT-default: "test value"
  - name: email-address
    values:
      VARIANT-default: ""
"""
        variant_mapping = ResourceMapping(
            resource_id="VARIANT-default",
            resource_type=Variant,
            resource_name="default",
            file_path="",
            flow_name=None,
            resource_prefix=None,
        )

        with mock_variant_attributes_file(test_file_content):
            result = VariantAttribute.read_local_resource(
                file_path="config/variant_attributes.yaml/attributes/customer_name",
                resource_id="attr-customer-name",
                resource_name="customer-name",
                resource_mappings=[variant_mapping],
            )

        self.assertEqual(result.resource_id, "attr-customer-name")
        self.assertEqual(result.name, "customer-name")
        self.assertEqual(result.mappings, {"VARIANT-default": "test value"})

    def test_validate_empty_name(self):
        """Test validation fails when name is empty."""
        attr = VariantAttribute(
            resource_id="attr-test",
            name="",
            mappings={"VARIANT-default": ""},
        )
        with self.assertRaises(ValueError) as cm:
            attr.validate(resource_mappings=[])
        self.assertIn("Name is required", str(cm.exception))

    def test_validate_empty_mappings(self):
        """Test validation fails when mappings are empty."""
        attr = VariantAttribute(
            resource_id="attr-test",
            name="test-attr",
            mappings={},
        )
        variant_mapping = ResourceMapping(
            resource_id="VARIANT-default",
            resource_type=Variant,
            resource_name="default",
            file_path="",
            flow_name=None,
            resource_prefix=None,
        )
        with self.assertRaises(ValueError) as cm:
            attr.validate(resource_mappings=[variant_mapping])
        self.assertIn("Mappings are required", str(cm.exception))

    def test_validate_missing_variants(self):
        """Test validation fails when attribute is missing values for some variants."""
        attr = VariantAttribute(
            resource_id="attr-test",
            name="test-attr",
            mappings={"VARIANT-default": ""},
        )
        variant_mappings = [
            ResourceMapping(
                resource_id="VARIANT-default",
                resource_type=Variant,
                resource_name="default",
                file_path="",
                flow_name=None,
                resource_prefix=None,
            ),
            ResourceMapping(
                resource_id="VARIANT-production",
                resource_type=Variant,
                resource_name="production",
                file_path="",
                flow_name=None,
                resource_prefix=None,
            ),
        ]
        with self.assertRaises(ValueError) as cm:
            attr.validate(resource_mappings=variant_mappings)
        self.assertIn("Missing variants for variant attribute", str(cm.exception))

    def test_validate_additional_variants(self):
        """Test validation fails when attribute has values for unknown variants."""
        attr = VariantAttribute(
            resource_id="attr-test",
            name="test-attr",
            mappings={"VARIANT-default": "", "VARIANT-unknown": ""},
        )
        variant_mapping = ResourceMapping(
            resource_id="VARIANT-default",
            resource_type=Variant,
            resource_name="default",
            file_path="",
            flow_name=None,
            resource_prefix=None,
        )
        with self.assertRaises(ValueError) as cm:
            attr.validate(resource_mappings=[variant_mapping])
        self.assertIn("Additional variants found for attribute", str(cm.exception))

    def test_validate_valid(self):
        """Test validation passes when attribute has correct mappings."""
        variant_mapping = ResourceMapping(
            resource_id="VARIANT-default",
            resource_type=Variant,
            resource_name="default",
            file_path="",
            flow_name=None,
            resource_prefix=None,
        )
        self.assertIsNone(TEST_VARIANT_ATTRIBUTE.validate(resource_mappings=[variant_mapping]))

    def test_make_pretty_replaces_variant_ids_with_names(self):
        """Test make_pretty replaces variant IDs with names in values."""
        raw_content = "name: customer-name\nvalues:\n  VARIANT-default: hello\n"
        variant_mapping = ResourceMapping(
            resource_id="VARIANT-default",
            resource_type=Variant,
            resource_name="default",
            file_path="",
            flow_name=None,
            resource_prefix=None,
        )
        pretty = VariantAttribute.make_pretty(
            raw_content,
            resource_mappings=[variant_mapping],
        )
        self.assertIn("default:", pretty)
        self.assertNotIn("VARIANT-default:", pretty)

    def test_from_pretty_replaces_variant_names_with_ids(self):
        """Test from_pretty replaces variant names with IDs in values."""
        pretty_content = "name: customer-name\nvalues:\n  default: hello\n"
        variant_mapping = ResourceMapping(
            resource_id="VARIANT-default",
            resource_type=Variant,
            resource_name="default",
            file_path="",
            flow_name=None,
            resource_prefix=None,
        )
        raw = VariantAttribute.from_pretty(
            pretty_content,
            resource_mappings=[variant_mapping],
        )
        self.assertIn("VARIANT-default:", raw)
        # Values dict should use variant ID as key, not name
        self.assertIn("VARIANT-default: hello", raw)


class MultiResourceYamlResourceCacheTests(unittest.TestCase):
    """Tests for MultiResourceYamlResource file cache behavior."""

    def setUp(self):
        """Clear the file cache before each test to avoid cross-test pollution."""
        MultiResourceYamlResource._file_cache.clear()

    def test_multiple_reads_from_same_file_only_read_once(self):
        """Multiple read_local_resource calls for the same file should only read from disk once."""
        content = """sms_templates:
- name: template_a
  text: Text A
  env_phone_numbers:
    sandbox: ''
    pre_release: ''
    live: '+447700102347'
- name: template_b
  text: Text B
  env_phone_numbers:
    sandbox: ''
    pre_release: ''
    live: '+447700102347'
"""
        read_count = 0

        def count_reads(path):
            nonlocal read_count
            read_count += 1
            return content

        def exists_sms(path):
            return "sms_templates.yaml" in str(path)

        def isfile_sms(path):
            return "sms_templates.yaml" in str(path)

        def getmtime_sms(path):
            return 1.0 if "sms_templates.yaml" in str(path) else os.path.getmtime(path)

        with unittest.mock.patch(
            "poly.resources.resource.os.path.exists", side_effect=exists_sms
        ), unittest.mock.patch(
            "poly.resources.resource.os.path.isfile", side_effect=isfile_sms
        ), unittest.mock.patch(
            "poly.resources.resource.os.path.getmtime", side_effect=getmtime_sms
        ), unittest.mock.patch(
            "poly.resources.resource.Resource.read_from_file",
            side_effect=count_reads,
        ):
            SMSTemplate.read_local_resource(
                file_path="config/sms_templates.yaml/sms_templates/template_a",
                resource_id="id-a",
                resource_name="template_a",
            )
            SMSTemplate.read_local_resource(
                file_path="config/sms_templates.yaml/sms_templates/template_b",
                resource_id="id-b",
                resource_name="template_b",
            )
        self.assertEqual(read_count, 1, "read_from_file should be called once for both resources")

    def test_save_updates_cache_so_next_read_sees_new_content(self):
        """After save(), cache is updated so next read sees the written content without re-reading."""
        import tempfile

        base_path = tempfile.mkdtemp()
        sms_file = os.path.join(base_path, "config", "sms_templates.yaml")
        os.makedirs(os.path.dirname(sms_file), exist_ok=True)
        initial_content = """sms_templates:
- name: only_one
  text: Original
  env_phone_numbers:
    sandbox: ''
    pre_release: ''
    live: '+447700102347'
"""
        with open(sms_file, "w") as f:
            f.write(initial_content)
        try:
            r1 = SMSTemplate.read_local_resource(
                    file_path=os.path.join(sms_file, "sms_templates", "only_one"),
                    resource_id="id-1",
                    resource_name="only_one",
                )
            self.assertEqual(r1.text, "Original")
            r1.text = "Updated"
            r1.save(base_path)
            r2 = SMSTemplate.read_local_resource(
                file_path=os.path.join(sms_file, "sms_templates", "only_one"),
                resource_id="id-1",
                resource_name="only_one",
            )
            self.assertEqual(r2.text, "Updated", "Next read after save should see updated content")
        finally:
            import shutil

            shutil.rmtree(base_path, ignore_errors=True)

    def test_mtime_change_refreshes_cache(self):
        """When file mtime changes (e.g. external edit), next read re-reads from disk."""
        content_v1 = """sms_templates:
- name: only
  text: First
  env_phone_numbers:
    sandbox: ''
    pre_release: ''
    live: '+447700102347'
"""
        content_v2 = """sms_templates:
- name: only
  text: Second
  env_phone_numbers:
    sandbox: ''
    pre_release: ''
    live: '+447700102347'
"""
        mtime = [1.0]

        def getmtime_sms(path):
            if "sms_templates.yaml" in str(path):
                return mtime[0]
            return os.path.getmtime(path)

        def exists_sms(path):
            return "sms_templates.yaml" in str(path)

        def isfile_sms(path):
            return "sms_templates.yaml" in str(path)

        def read_return_v1_or_v2(path):
            return content_v2 if mtime[0] == 2.0 else content_v1

        with unittest.mock.patch(
            "poly.resources.resource.os.path.exists", side_effect=exists_sms
        ), unittest.mock.patch(
            "poly.resources.resource.os.path.isfile", side_effect=isfile_sms
        ), unittest.mock.patch(
            "poly.resources.resource.os.path.getmtime", side_effect=getmtime_sms
        ), unittest.mock.patch(
            "poly.resources.resource.Resource.read_from_file",
            side_effect=read_return_v1_or_v2,
        ):
            r1 = SMSTemplate.read_local_resource(
                file_path="config/sms_templates.yaml/sms_templates/only",
                resource_id="id-1",
                resource_name="only",
            )
            self.assertEqual(r1.text, "First")
            mtime[0] = 2.0
            r2 = SMSTemplate.read_local_resource(
                file_path="config/sms_templates.yaml/sms_templates/only",
                resource_id="id-1",
                resource_name="only",
            )
            self.assertEqual(r2.text, "Second", "After mtime change, read should see new content")


class ChannelSettingsDictFormatTests(unittest.TestCase):
    """Tests that channel greeting/style prompt save as dict format, not list format."""

    def setUp(self):
        MultiResourceYamlResource._file_cache.clear()

    def test_voice_greeting_saves_as_dict_not_list(self):
        """VoiceGreeting.save() produces greeting: { key: value } not greeting: [ - key: value ]."""
        import shutil
        import tempfile

        base_path = tempfile.mkdtemp()
        config_file = os.path.join(base_path, "voice", "configuration.yaml")
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        try:
            greeting = VoiceGreeting(
                resource_id="voice_greeting",
                name="voice_greeting",
                welcome_message="Hello, I do want to help you",
                language_code="en-GB",
            )
            greeting.save(base_path)
            with open(config_file) as f:
                content = f.read()
            data = yaml.safe_load(content)
            self.assertIsInstance(data["greeting"], dict, "greeting should be a dict, not a list")
            self.assertEqual(data["greeting"]["welcome_message"], "Hello, I do want to help you")
            self.assertEqual(data["greeting"]["language_code"], "en-GB")
            self.assertNotIn("- welcome_message", content, "Should not have list format with '-'")
        finally:
            shutil.rmtree(base_path, ignore_errors=True)

    def test_voice_style_prompt_saves_as_dict_not_list(self):
        """VoiceStylePrompt.save() produces style_prompt: { key: value } not list format."""
        import shutil
        import tempfile

        base_path = tempfile.mkdtemp()
        config_file = os.path.join(base_path, "voice", "configuration.yaml")
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        try:
            style_prompt = VoiceStylePrompt.from_yaml_dict(
                {"prompt": "You are helpful."},
                resource_id="voice_style_prompt",
                name="voice_style_prompt",
            )
            style_prompt.save(base_path)
            with open(config_file) as f:
                content = f.read()
            data = yaml.safe_load(content)
            self.assertIsInstance(
                data["style_prompt"], dict, "style_prompt should be a dict, not a list"
            )
            self.assertEqual(data["style_prompt"]["prompt"], "You are helpful.")
            self.assertNotIn("- prompt", content, "Should not have list format with '-'")
        finally:
            shutil.rmtree(base_path, ignore_errors=True)

    def test_chat_greeting_saves_as_dict_not_list(self):
        """ChatGreeting.save() produces greeting: { key: value } in chat config."""
        import shutil
        import tempfile

        base_path = tempfile.mkdtemp()
        config_file = os.path.join(base_path, "chat", "configuration.yaml")
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        try:
            greeting = ChatGreeting(
                resource_id="chat_greeting",
                name="chat_greeting",
                welcome_message="Welcome to chat!",
                language_code="en-US",
            )
            greeting.save(base_path)
            with open(config_file) as f:
                content = f.read()
            data = yaml.safe_load(content)
            self.assertIsInstance(data["greeting"], dict, "greeting should be a dict, not a list")
            self.assertEqual(data["greeting"]["welcome_message"], "Welcome to chat!")
            self.assertEqual(data["greeting"]["language_code"], "en-US")
            self.assertNotIn("- welcome_message", content, "Should not have list format with '-'")
        finally:
            shutil.rmtree(base_path, ignore_errors=True)

    def test_chat_style_prompt_saves_as_dict_not_list(self):
        """ChatStylePrompt.save() produces style_prompt: { key: value } in chat config."""
        import shutil
        import tempfile

        base_path = tempfile.mkdtemp()
        config_file = os.path.join(base_path, "chat", "configuration.yaml")
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        try:
            style_prompt = ChatStylePrompt.from_yaml_dict(
                {"prompt": "You are a friendly assistant."},
                resource_id="chat_style_prompt",
                name="chat_style_prompt",
            )
            style_prompt.save(base_path)
            with open(config_file) as f:
                content = f.read()
            data = yaml.safe_load(content)
            self.assertIsInstance(
                data["style_prompt"], dict, "style_prompt should be a dict, not a list"
            )
            self.assertEqual(data["style_prompt"]["prompt"], "You are a friendly assistant.")
            self.assertNotIn("- prompt", content, "Should not have list format with '-'")
        finally:
            shutil.rmtree(base_path, ignore_errors=True)

    def test_channel_greeting_file_paths(self):
        """VoiceGreeting and ChatGreeting use correct channel config paths."""
        vg = VoiceGreeting(
            resource_id="vg", name="vg", welcome_message="Hi", language_code="en-GB"
        )
        cg = ChatGreeting(
            resource_id="cg", name="cg", welcome_message="Hello", language_code="en-US"
        )
        self.assertIn("voice", vg.file_path)
        self.assertIn("chat", cg.file_path)
        self.assertIn("configuration.yaml", vg.file_path)
        self.assertIn("configuration.yaml", cg.file_path)


class HandoffTests(unittest.TestCase):
    def test_init_to_yaml_dict_roundtrip(self):
        """Init from kwargs (dict sip_config), to_yaml_dict has no references, from_yaml_dict roundtrip."""
        h = Handoff(
            resource_id="ho-1",
            name="Default",
            description="Main handoff",
            is_default=True,
            sip_config={"method": "invite", "phone_number": "+44", "outbound_endpoint": "sip:foo", "outbound_encryption": "TLS/SRTP"},
            sip_headers=[{"key": "X-Foo", "value": "bar"}],
        )
        d = h.to_yaml_dict()
        self.assertNotIn("references", d)
        self.assertEqual(d["name"], "Default")
        self.assertEqual(d["sip_config"]["method"], "invite")
        self.assertEqual(d["sip_headers"][0]["key"], "X-Foo")
        h2 = Handoff.from_yaml_dict(d, "ho-1", "Default")
        self.assertEqual(h2.name, h.name)
        self.assertEqual(h2.sip_config.method, h.sip_config.method)
        self.assertEqual(h2.sip_headers, h.sip_headers)

    def test_file_path_command_type_prefix(self):
        """file_path, command_type, get_resource_prefix return expected values."""
        h = Handoff(resource_id="ho-1", name="My Handoff", sip_config={"method": "bye"}, sip_headers=[])
        self.assertIn("config", h.file_path)
        self.assertIn("handoffs.yaml", h.file_path)
        self.assertIn("handoffs", h.file_path)
        self.assertEqual(h.command_type, "handoff")
        self.assertEqual(Handoff.get_resource_prefix(), "ho")

    def test_build_protos(self):
        """build_create_proto, build_update_proto, build_delete_proto set id/name and sip_headers."""
        h = Handoff(
            resource_id="ho-id",
            name="Test",
            description="Desc",
            is_default=False,
            sip_config={"method": "refer", "phone_number": "+1"},
            sip_headers=[{"key": "K", "value": "V"}],
        )
        create = h.build_create_proto()
        update = h.build_update_proto()
        delete = h.build_delete_proto()
        self.assertEqual(create.id, "ho-id")
        self.assertEqual(create.name, "Test")
        self.assertEqual(update.description, "Desc")
        self.assertTrue(create.active and update.active)
        self.assertEqual(delete.id, "ho-id")
        self.assertEqual(len(create.sip_headers.headers), 1)
        self.assertEqual(create.sip_headers.headers[0].key, "K")

    def test_validate_and_validate_collection(self):
        """validate raises for missing name, invalid method, invalid encryption; validate_collection for 0/2 defaults."""
        with self.assertRaises(ValueError) as cm:
            Handoff(resource_id="x", name="", sip_config={"method": "bye"}, sip_headers=[]).validate()
        self.assertIn("name is required", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            Handoff(resource_id="x", name="H", sip_config={"method": "invalid"}, sip_headers=[]).validate()
        self.assertIn("Invalid SIP method", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            Handoff(
                resource_id="x", name="H",
                sip_config={"method": "invite", "outbound_encryption": "bad"},
                sip_headers=[],
            ).validate()
        self.assertIn("Invalid encryption", str(cm.exception))
        Handoff(resource_id="x", name="H", sip_config={"method": "bye"}, sip_headers=[]).validate()
        with self.assertRaises(ValueError):
            Handoff.validate_collection({})
        with self.assertRaises(ValueError):
            Handoff.validate_collection({
                "a": Handoff(resource_id="1", name="A", sip_config={"method": "bye"}, sip_headers=[], is_default=True),
                "b": Handoff(resource_id="2", name="B", sip_config={"method": "bye"}, sip_headers=[], is_default=True),
            })
        Handoff.validate_collection({
            "a": Handoff(resource_id="1", name="A", sip_config={"method": "bye"}, sip_headers=[], is_default=True),
        })

    def test_make_pretty_from_pretty_discover(self):
        """make_pretty/from_pretty pass through to utils; discover_resources returns [] when no file, paths when file exists."""
        content = "name: Test\nsip_config:\n  method: bye\n"
        self.assertEqual(Handoff.make_pretty(content, []), content)
        self.assertEqual(Handoff.from_pretty(content, []), content)
        self.assertEqual(Handoff.discover_resources("/nonexistent"), [])
        handoffs_yaml = "handoffs:\n- name: H1\n  description: ''\n  is_default: true\n  sip_config:\n    method: bye\n  sip_headers: []\n"
        base_path = "."
        path = os.path.join(base_path, "config", "handoffs.yaml")
        def exists_handoff(p):
            return path in str(p) or os.path.exists(p)
        def isfile_handoff(p):
            return path in str(p) or os.path.isfile(p)
        def getmtime_handoff(p):
            return 1.0 if path in str(p) else os.path.getmtime(p)
        with mock_read_from_file({path: handoffs_yaml}):
            with unittest.mock.patch("poly.resources.handoff.os.path.exists", side_effect=exists_handoff), unittest.mock.patch(
                "poly.resources.resource.os.path.exists", side_effect=exists_handoff
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.isfile", side_effect=isfile_handoff
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.getmtime", side_effect=getmtime_handoff
            ):
                discovered = Handoff.discover_resources(base_path)
        self.assertEqual(len(discovered), 1)
        self.assertIn("handoffs", discovered[0])
        self.assertIn("H1", discovered[0])


class ApiIntegrationTest(unittest.TestCase):
    """Tests for ApiIntegration, ApiIntegrationConfig, Environments, ApiIntegrationOperation."""

    def setUp(self):
        MultiResourceYamlResource._file_cache.clear()

    def test_api_integration_config_from_dict_and_to_proto(self):
        """ApiIntegrationConfig from_dict handles None, empty, and camelCase; to_proto returns proto."""
        c = ApiIntegrationConfig.from_dict(None)
        self.assertEqual(c.base_url, "")
        self.assertEqual(c.auth_type, "none")
        c = ApiIntegrationConfig.from_dict({"baseUrl": "https://api.example.com", "authType": "oauth2"})
        self.assertEqual(c.base_url, "https://api.example.com")
        self.assertEqual(c.auth_type, "oauth2")
        proto = c.to_proto()
        self.assertEqual(proto.base_url, "https://api.example.com")
        self.assertEqual(proto.auth_type, "oauth2")

    def test_api_integration_config_build_config_update_proto(self):
        """build_config_update_proto returns ApiIntegrationConfig_Update with integration_id and environment."""
        c = ApiIntegrationConfig(base_url="https://sandbox.example.com", auth_type="api_key")
        update = c.build_config_update_proto("int-123", "sandbox")
        self.assertEqual(update.id, "int-123")
        self.assertEqual(update.environment, "sandbox")
        self.assertEqual(update.base_url, "https://sandbox.example.com")
        self.assertEqual(update.auth_type, "api_key")

    def test_environments_from_dict_and_to_proto(self):
        """Environments from_dict and to_proto roundtrip."""
        env = ApiIntegrationEnvironments.from_dict(None)
        self.assertEqual(env.sandbox.base_url, "")
        data = {
            "sandbox": {"base_url": "https://sb.com", "auth_type": "oauth2"},
            "live": {"base_url": "https://live.com", "auth_type": "none"},
        }
        env = ApiIntegrationEnvironments.from_dict(data)
        self.assertEqual(env.sandbox.base_url, "https://sb.com")
        self.assertEqual(env.live.auth_type, "none")
        proto = env.to_proto()
        self.assertEqual(proto.sandbox.base_url, "https://sb.com")
        self.assertEqual(proto.live.auth_type, "none")

    def test_api_integration_operation_from_dict_and_protos(self):
        """ApiIntegrationOperation from_dict sets resource_id from id; build_*_proto set integration_id."""
        op = ApiIntegrationOperation.from_dict(None)
        self.assertEqual(op.resource_id, "")
        self.assertEqual(op.name, "")
        op = ApiIntegrationOperation.from_dict({
            "id": "op-abc",
            "name": "get_ticket",
            "method": "GET",
            "resource": "/tickets/{id}",
        })
        self.assertEqual(op.resource_id, "op-abc")
        self.assertEqual(op.name, "get_ticket")
        self.assertEqual(op.method, "GET")
        self.assertEqual(op.resource, "/tickets/{id}")
        self.assertEqual(op.command_type, "api_integration_operation")
        op.integration_id = "int-1"
        create = op.build_create_proto()
        self.assertEqual(create.id, "op-abc")
        self.assertEqual(create.integration_id, "int-1")
        self.assertEqual(create.name, "get_ticket")
        update = op.build_update_proto()
        self.assertEqual(update.id, "op-abc")
        self.assertEqual(update.integration_id, "int-1")
        delete = op.build_delete_proto()
        self.assertEqual(delete.id, "op-abc")
        self.assertEqual(delete.integration_id, "int-1")

    def test_api_integration_file_path_and_command_type(self):
        """ApiIntegration file_path includes name segment; command_type and update_command_type."""
        i = ApiIntegration(resource_id="int-1", name="My API", description="Desc")
        self.assertIn("config", i.file_path)
        self.assertIn("api_integrations.yaml", i.file_path)
        self.assertIn("api_integrations", i.file_path)
        self.assertIn("My_API", i.file_path)
        self.assertEqual(i.command_type, "api_integration")
        self.assertEqual(i.update_command_type, "update_api_integration")

    def test_api_integration_to_yaml_dict_and_from_yaml_dict(self):
        """ApiIntegration to_yaml_dict and from_yaml_dict roundtrip with environments and operations."""
        env = ApiIntegrationEnvironments.from_dict({
            "sandbox": {"base_url": "https://sb.com", "auth_type": "none"},
        })
        ops = [
            ApiIntegrationOperation(resource_id="op-1", name="get", method="GET", resource="/x"),
        ]
        i = ApiIntegration(
            resource_id="int-1",
            name="TestAPI",
            description="Description",
            environments=env,
            operations=ops,
        )
        d = i.to_yaml_dict()
        self.assertEqual(d["name"], "TestAPI")
        self.assertEqual(d["description"], "Description")
        self.assertIn("environments", d)
        self.assertEqual(d["environments"]["sandbox"]["base_url"], "https://sb.com")
        self.assertEqual(len(d["operations"]), 1)
        self.assertEqual(d["operations"][0]["name"], "get")
        i2 = ApiIntegration.from_yaml_dict(d, resource_id="int-1", name="TestAPI")
        self.assertEqual(i2.resource_id, "int-1")
        self.assertEqual(i2.name, "TestAPI")
        self.assertEqual(i2.environments.sandbox.base_url, "https://sb.com")
        self.assertEqual(len(i2.operations), 1)
        self.assertEqual(i2.operations[0].name, "get")
        self.assertEqual(i2.operations[0].resource_id, "")

    def test_api_integration_build_protos(self):
        """ApiIntegration build_create_proto, build_update_proto, build_delete_proto set id and environments."""
        env = ApiIntegrationEnvironments.from_dict({"sandbox": {"base_url": "https://x.com", "auth_type": "none"}})
        i = ApiIntegration(resource_id="int-1", name="API", description="D", environments=env)
        create = i.build_create_proto()
        self.assertEqual(create.id, "int-1")
        self.assertEqual(create.name, "API")
        self.assertEqual(create.description, "D")
        self.assertEqual(create.environments.sandbox.base_url, "https://x.com")
        update = i.build_update_proto()
        self.assertEqual(update.id, "int-1")
        self.assertEqual(update.name, "API")
        delete = i.build_delete_proto()
        self.assertEqual(delete.id, "int-1")

    def test_api_integration_get_new_updated_deleted_subresources(self):
        """get_new_updated_deleted_subresources returns new/updated/deleted operations with integration_id set."""
        op1 = ApiIntegrationOperation(resource_id="op-1", name="get", method="GET", resource="/a")
        op2 = ApiIntegrationOperation(resource_id="op-2", name="post", method="POST", resource="/b")
        new_integration = ApiIntegration(
            resource_id="int-1",
            name="API",
            operations=[op1, op2],
        )
        new_ops, updated_ops, deleted_ops = new_integration.get_new_updated_deleted_subresources(None)
        self.assertEqual(len(new_ops), 2)
        self.assertEqual(len(updated_ops), 0)
        self.assertEqual(len(deleted_ops), 0)
        self.assertEqual(new_ops[0].integration_id, "int-1")
        self.assertEqual(new_ops[1].integration_id, "int-1")

        old_integration = ApiIntegration(
            resource_id="int-1",
            name="API",
            operations=[
                ApiIntegrationOperation(resource_id="op-1", name="get", method="GET", resource="/a"),
                ApiIntegrationOperation(resource_id="op-3", name="delete", method="DELETE", resource="/c"),
            ],
        )
        current = ApiIntegration(
            resource_id="int-1",
            name="API",
            operations=[
                ApiIntegrationOperation(resource_id="op-1", name="get_renamed", method="GET", resource="/a"),
                op2,
            ],
        )
        new_ops, updated_ops, deleted_ops = current.get_new_updated_deleted_subresources(old_integration)
        self.assertEqual(len(new_ops), 1)
        self.assertEqual(new_ops[0].name, "post")
        self.assertEqual(len(updated_ops), 1)
        self.assertEqual(updated_ops[0].name, "get_renamed")
        self.assertEqual(len(deleted_ops), 1)
        self.assertEqual(deleted_ops[0].name, "delete")
        self.assertEqual(deleted_ops[0].integration_id, "int-1")

    def test_api_integration_discover_resources(self):
        """discover_resources returns [] when no file; returns paths for each integration in the list."""
        import tempfile
        self.assertEqual(ApiIntegration.discover_resources("/nonexistent"), [])
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = os.path.join(tmpdir, "config")
            os.makedirs(config_dir, exist_ok=True)
            yaml_path = os.path.join(config_dir, "api_integrations.yaml")
            with open(yaml_path, "w") as f:
                yaml.dump({
                    "api_integrations": [
                        {"name": "API One", "description": "First"},
                        {"name": "API Two", "description": "Second"},
                    ],
                }, f)
            discovered = ApiIntegration.discover_resources(tmpdir)
            self.assertEqual(len(discovered), 2)
            self.assertIn("api_integrations.yaml", discovered[0])
            self.assertIn("API_One", discovered[0])
            self.assertIn("API_Two", discovered[1])

    def test_api_integration_read_local_resource(self):
        """read_local_resource loads integration from multi-resource path and returns ApiIntegration."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = os.path.join(tmpdir, "config")
            os.makedirs(config_dir, exist_ok=True)
            yaml_path = os.path.join(config_dir, "api_integrations.yaml")
            with open(yaml_path, "w") as f:
                yaml.dump({
                    "api_integrations": [
                        {
                            "name": "TestAPI",
                            "description": "A test",
                            "environments": {
                                "sandbox": {"base_url": "https://sb.com", "auth_type": "none"},
                            },
                            "operations": [{"name": "get", "method": "GET", "resource": "/x"}],
                        },
                    ],
                }, f)
            resource_path = os.path.join(yaml_path, "api_integrations", "TestAPI")
            integration = ApiIntegration.read_local_resource(
                file_path=resource_path,
                resource_id="int-1",
                resource_name="TestAPI",
            )
            self.assertEqual(integration.resource_id, "int-1")
            self.assertEqual(integration.name, "TestAPI")
            self.assertEqual(integration.description, "A test")
            self.assertEqual(integration.environments.sandbox.base_url, "https://sb.com")
            self.assertEqual(len(integration.operations), 1)
            self.assertEqual(integration.operations[0].name, "get")
            self.assertEqual(integration.operations[0].method, "GET")


class VariableTest(unittest.TestCase):
    """Basic tests for the Variable resource."""

    def test_file_path(self):
        var = Variable(resource_id="VAR-123", name="customer_name")
        self.assertEqual(var.file_path, "variables/customer_name")

    def test_raw(self):
        var = Variable(resource_id="VAR-123", name="order_id")
        self.assertEqual(var.raw, "vrbl:order_id")

    def test_get_resource_prefix(self):
        self.assertEqual(Variable.get_resource_prefix(), "vrbl")

    def test_read_local_resource(self):
        var = Variable.read_local_resource(
            file_path="variables/test_var",
            resource_id="VAR-abc",
            resource_name="test_var",
        )
        self.assertEqual(var.resource_id, "VAR-abc")
        self.assertEqual(var.name, "test_var")

    def test_read_from_file(self):
        content = Variable.read_from_file("/path/variables/customer_name")
        self.assertEqual(content, "vrbl:customer_name")

    def test_make_pretty_from_pretty_passthrough(self):
        content = "vrbl:customer_name"
        self.assertEqual(Variable.make_pretty(content, []), content)
        self.assertEqual(Variable.from_pretty(content, []), content)

    def test_discover_resources_from_functions(self):
        """Variables are discovered from conv.state.<name> in function code."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "functions"), exist_ok=True)
            os.makedirs(os.path.join(tmpdir, "flows"), exist_ok=True)
            func_file = os.path.join(tmpdir, "functions", "my_func.py")
            with open(func_file, "w") as f:
                f.write("def my_func(conv):\n    x = conv.state.customer_name\n")
            discovered = Variable.discover_resources(tmpdir)
            self.assertIn(os.path.join(tmpdir, "variables", "customer_name"), discovered)

    def test_discover_resources_empty_when_no_functions(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "flows"), exist_ok=True)
            discovered = Variable.discover_resources(tmpdir)
            self.assertEqual(discovered, [])

    def test_discover_resources_excludes_commented_conv_state(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "functions"), exist_ok=True)
            os.makedirs(os.path.join(tmpdir, "flows"), exist_ok=True)
            func_file = os.path.join(tmpdir, "functions", "my_func.py")
            with open(func_file, "w") as f:
                f.write("# conv.state.commented\nx = conv.state.actual_var\n")
            discovered = Variable.discover_resources(tmpdir)
            self.assertCountEqual(
                discovered,
                [
                    os.path.join(tmpdir, "variables", "actual_var"),
                    os.path.join(tmpdir, "variables", "commented"),
                ]
            )

class PhraseFilterTests(unittest.TestCase):
    def setUp(self):
        MultiResourceYamlResource._file_cache.clear()

    def test_init_to_yaml_dict_from_yaml_dict_roundtrip(self):
        """Init from kwargs, to_yaml_dict, from_yaml_dict roundtrip preserves all fields."""
        pf = PhraseFilter(
            resource_id="sk-1",
            name="Block Profanity",
            description="Blocks profane words",
            regular_expressions=[r"\bbadword\b", r"\bother\b"],
            say_phrase=True,
            language_code="en-GB",
            function="handle_profanity",
        )
        d = pf.to_yaml_dict()
        self.assertEqual(d["name"], "Block Profanity")
        self.assertEqual(d["regular_expressions"], [r"\bbadword\b", r"\bother\b"])
        self.assertTrue(d["say_phrase"])
        self.assertEqual(d["function"], "handle_profanity")
        pf2 = PhraseFilter.from_yaml_dict(d, resource_id="sk-1", name="Block Profanity")
        self.assertEqual(pf2.name, pf.name)
        self.assertEqual(pf2.regular_expressions, pf.regular_expressions)
        self.assertEqual(pf2.say_phrase, pf.say_phrase)
        self.assertEqual(pf2.function, pf.function)

    def test_to_yaml_dict_omits_empty_strings(self):
        """Fields with empty string values are excluded from the YAML dict."""
        pf = PhraseFilter(
            resource_id="sk-2",
            name="Filter",
            regular_expressions=[r"test"],
            say_phrase=False,
        )
        d = pf.to_yaml_dict()
        self.assertNotIn("description", d)
        self.assertNotIn("language_code", d)
        self.assertNotIn("function", d)

    def test_make_pretty_replaces_function_id_with_name(self):
        """make_pretty should swap the function ID for its human-readable name."""
        resource_mappings = [
            ResourceMapping(
                resource_id="FUNCTION-handle_profanity",
                resource_name="handle_profanity",
                resource_type=Function,
                file_path="functions/handle_profanity.py",
                flow_name=None,
                resource_prefix=None,
            ),
        ]
        content = "name: Block Profanity\nfunction: FUNCTION-handle_profanity\n"
        result = PhraseFilter.make_pretty(content, resource_mappings=resource_mappings)
        self.assertIn("handle_profanity", result)
        self.assertNotIn("FUNCTION-handle_profanity", result)

    def test_from_pretty_replaces_function_name_with_id(self):
        """from_pretty should swap human-readable function name back to its ID."""
        resource_mappings = [
            ResourceMapping(
                resource_id="FUNCTION-handle_profanity",
                resource_name="handle_profanity",
                resource_type=Function,
                file_path="functions/handle_profanity.py",
                flow_name=None,
                resource_prefix=None,
            ),
        ]
        content = "name: Block Profanity\nfunction: handle_profanity\n"
        result = PhraseFilter.from_pretty(content, resource_mappings=resource_mappings)
        self.assertIn("FUNCTION-handle_profanity", result)

    def test_make_pretty_no_function_returns_unchanged(self):
        """make_pretty with no function field returns content unchanged (modulo YAML re-dump)."""
        content = "name: Simple Filter\nregular_expressions:\n- test\n"
        result = PhraseFilter.make_pretty(content, resource_mappings=[])
        self.assertIn("Simple Filter", result)

    def test_from_pretty_invalid_yaml_returns_original(self):
        """from_pretty with invalid YAML returns the original string."""
        bad_yaml = ": : invalid: [yaml"
        self.assertEqual(PhraseFilter.from_pretty(bad_yaml, resource_mappings=[]), bad_yaml)

    def test_validate_missing_name_raises(self):
        """validate raises ValueError when name is missing."""
        pf = PhraseFilter(resource_id="sk-1", name="", regular_expressions=[r"x"])
        with self.assertRaises(ValueError) as cm:
            pf.validate(resource_mappings=[])
        self.assertIn("Name is required", str(cm.exception))

    def test_validate_missing_regex_raises(self):
        """validate raises ValueError when regular_expressions is empty."""
        pf = PhraseFilter(resource_id="sk-1", name="Filter", regular_expressions=[])
        with self.assertRaises(ValueError) as cm:
            pf.validate(resource_mappings=[])
        self.assertIn("regular expression", str(cm.exception).lower())

    def test_build_protos(self):
        """build_create_proto, build_update_proto, build_delete_proto set fields correctly."""
        pf = PhraseFilter(
            resource_id="sk-id",
            name="Test Filter",
            description="Desc",
            regular_expressions=[r"\bword\b"],
            say_phrase=True,
            language_code="en-US",
            function="FUNCTION-fn1",
        )
        create = pf.build_create_proto()
        update = pf.build_update_proto()
        delete = pf.build_delete_proto()
        self.assertEqual(create.id, "sk-id")
        self.assertEqual(create.title, "Test Filter")
        self.assertEqual(create.description, "Desc")
        self.assertEqual(list(create.regular_expressions), [r"\bword\b"])
        self.assertTrue(create.say_phrase)
        self.assertEqual(update.id, "sk-id")
        self.assertEqual(update.language_code, "en-US")
        self.assertEqual(delete.id, "sk-id")

    def test_discover_resources_nonexistent_path(self):
        """discover_resources returns empty list when YAML file doesn't exist."""
        self.assertEqual(PhraseFilter.discover_resources("/nonexistent"), [])

    def test_discover_resources_with_file(self):
        """discover_resources returns paths for each phrase filter in the YAML."""
        yaml_content = """phrase_filtering:
- name: Block Profanity
  description: Blocks bad words
  regular_expressions:
  - \\bbad\\b
  say_phrase: false
- name: Block Spam
  description: Blocks spam
  regular_expressions:
  - spam
  say_phrase: true
"""
        base_path = "."
        yaml_path = os.path.join(base_path, "voice", "response_control", "phrase_filtering.yaml")

        def exists_pf(p):
            return yaml_path in str(p) or os.path.exists(p)

        def isfile_pf(p):
            return yaml_path in str(p) or os.path.isfile(p)

        def getmtime_pf(p):
            return 1.0 if yaml_path in str(p) else os.path.getmtime(p)

        with mock_read_from_file({yaml_path: yaml_content}):
            with unittest.mock.patch(
                "poly.resources.phrase_filter.os.path.exists", side_effect=exists_pf
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.exists", side_effect=exists_pf
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.isfile", side_effect=isfile_pf
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.getmtime", side_effect=getmtime_pf
            ):
                discovered = PhraseFilter.discover_resources(base_path)
        self.assertEqual(len(discovered), 2)
        self.assertIn("Block_Profanity", discovered[0])
        self.assertIn("Block_Spam", discovered[1])


class PronunciationTests(unittest.TestCase):
    def setUp(self):
        MultiResourceYamlResource._file_cache.clear()

    def test_init_to_yaml_dict_from_yaml_dict_roundtrip(self):
        """Init from kwargs, to_yaml_dict, from_yaml_dict roundtrip preserves all fields."""
        p = Pronunciation(
            resource_id="pr-1",
            name="Dr replacement",
            regex=r"\bDr\.",
            replacement="Doctor",
            case_sensitive=True,
            language_code="en-GB",
            description="Replace Dr. with Doctor",
            position=0,
        )
        d = p.to_yaml_dict()
        self.assertNotIn("name", d)
        self.assertEqual(d["regex"], r"\bDr\.")
        self.assertEqual(d["replacement"], "Doctor")
        self.assertTrue(d["case_sensitive"])
        p2 = Pronunciation.from_yaml_dict(d, resource_id="pr-1", name="", position=0)
        self.assertEqual(p2.regex, p.regex)
        self.assertEqual(p2.replacement, p.replacement)
        self.assertEqual(p2.case_sensitive, p.case_sensitive)
        self.assertEqual(p2.description, p.description)

    def test_to_yaml_dict_omits_empty_strings(self):
        """Fields with empty string values are excluded from the YAML dict."""
        p = Pronunciation(
            resource_id="pr-2",
            regex=r"test",
            replacement="result",
            case_sensitive=True,
        )
        d = p.to_yaml_dict()
        self.assertNotIn("language_code", d)
        self.assertNotIn("name", d)
        self.assertNotIn("description", d)

    def test_validate_missing_regex_raises(self):
        """validate raises ValueError when regex is empty."""
        p = Pronunciation(resource_id="pr-1", regex="", replacement="x")
        with self.assertRaises(ValueError) as cm:
            p.validate()
        self.assertIn("Regex pattern is required", str(cm.exception))

    def test_validate_passes_with_regex(self):
        """validate succeeds when regex is provided."""
        p = Pronunciation(resource_id="pr-1", regex=r"\bword\b", replacement="x")
        p.validate()

    def test_build_protos(self):
        """build_create_proto, build_update_proto, build_delete_proto set fields correctly."""
        p = Pronunciation(
            resource_id="pr-id",
            name="Rule 1",
            regex=r"\bDr\.",
            replacement="Doctor",
            case_sensitive=True,
            language_code="en-US",
            description="Dr to Doctor",
            position=2,
        )
        create = p.build_create_proto()
        update = p.build_update_proto()
        delete = p.build_delete_proto()
        self.assertEqual(create.id, "pr-id")
        self.assertEqual(create.regex, r"\bDr\.")
        self.assertEqual(create.replacement, "Doctor")
        self.assertTrue(create.case_sensitive)
        self.assertEqual(create.position, 2)
        self.assertEqual(create.name, "Rule 1")
        self.assertEqual(update.id, "pr-id")
        self.assertEqual(update.description, "Dr to Doctor")
        self.assertEqual(delete.id, "pr-id")

    def test_discover_resources_nonexistent_path(self):
        """discover_resources returns empty list when YAML file doesn't exist."""
        self.assertEqual(Pronunciation.discover_resources("/nonexistent"), [])

    def test_discover_resources_with_file(self):
        """discover_resources returns index-based paths for each pronunciation."""
        yaml_content = """pronunciations:
- regex: \\bDr\\.
  replacement: Doctor
  case_sensitive: true
- regex: \\bMr\\.
  replacement: Mister
  case_sensitive: false
- regex: \\bSt\\.
  replacement: Street
  case_sensitive: false
"""
        base_path = "."
        yaml_path = os.path.join(base_path, "voice", "response_control", "pronunciations.yaml")

        def exists_pr(p):
            return yaml_path in str(p) or os.path.exists(p)

        def isfile_pr(p):
            return yaml_path in str(p) or os.path.isfile(p)

        def getmtime_pr(p):
            return 1.0 if yaml_path in str(p) else os.path.getmtime(p)

        with mock_read_from_file({yaml_path: yaml_content}):
            with unittest.mock.patch(
                "poly.resources.pronunciation.os.path.exists", side_effect=exists_pr
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.exists", side_effect=exists_pr
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.isfile", side_effect=isfile_pr
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.getmtime", side_effect=getmtime_pr
            ):
                discovered = Pronunciation.discover_resources(base_path)
        self.assertEqual(len(discovered), 3)
        self.assertIn("0", discovered[0])
        self.assertIn("1", discovered[1])
        self.assertIn("2", discovered[2])

    def test_read_local_resource(self):
        """read_local_resource correctly parses a pronunciation from the multi-resource YAML."""
        yaml_content = """pronunciations:
- regex: \\bDr\\.
  replacement: Doctor
  case_sensitive: true
  language_code: en-GB
  description: Replace Dr. abbreviation
- regex: \\bMr\\.
  replacement: Mister
  case_sensitive: false
"""

        def exists_pr(path):
            return True if "pronunciations.yaml" in str(path) else os.path.exists(path)

        def isfile_pr(path):
            return True if "pronunciations.yaml" in str(path) else os.path.isfile(path)

        def getmtime_pr(path):
            return 1.0 if "pronunciations.yaml" in str(path) else os.path.getmtime(path)

        with mock_read_from_file(yaml_content):
            with unittest.mock.patch(
                "poly.resources.resource.os.path.exists", side_effect=exists_pr
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.isfile", side_effect=isfile_pr
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.getmtime", side_effect=getmtime_pr
            ):
                result = Pronunciation.read_local_resource(
                    file_path="voice/response_control/pronunciations.yaml/pronunciations/0",
                    resource_id="pr-123",
                    resource_name="",
                )
        self.assertEqual(result.resource_id, "pr-123")
        self.assertEqual(result.regex, r"\bDr\.")
        self.assertEqual(result.replacement, "Doctor")
        self.assertTrue(result.case_sensitive)
        self.assertEqual(result.position, 0)


class AsrSettingsTests(unittest.TestCase):
    """Tests for AsrSettings resource."""

    def test_init_to_yaml_dict_from_yaml_dict_roundtrip(self):
        """Init from kwargs, to_yaml_dict, from_yaml_dict roundtrip preserves fields."""
        a = AsrSettings(
            resource_id="asr-1",
            name="asr_settings",
            barge_in=True,
            interaction_style="swift",
        )
        d = a.to_yaml_dict()
        self.assertTrue(d["barge_in"])
        self.assertEqual(d["interaction_style"], "swift")
        a2 = AsrSettings.from_yaml_dict(d, resource_id="asr-1", name="asr_settings")
        self.assertEqual(a2.barge_in, a.barge_in)
        self.assertEqual(a2.interaction_style, a.interaction_style)

    def test_from_yaml_dict_turbo_maps_to_sonic(self):
        """turbo interaction_style in YAML is mapped to sonic."""
        a = AsrSettings.from_yaml_dict(
            {"barge_in": False, "interaction_style": "turbo"},
            resource_id="asr-1",
            name="asr_settings",
        )
        self.assertEqual(a.interaction_style, "sonic")

    def test_validate_invalid_interaction_style_raises(self):
        """validate raises ValueError for invalid interaction_style."""
        a = AsrSettings(
            resource_id="asr-1",
            name="asr_settings",
            barge_in=False,
            interaction_style="invalid",
        )
        with self.assertRaises(ValueError) as cm:
            a.validate()
        self.assertIn("Invalid interaction_style", str(cm.exception))

    def test_validate_passes_with_valid_style(self):
        """validate succeeds with valid interaction_style."""
        a = AsrSettings(
            resource_id="asr-1",
            name="asr_settings",
            barge_in=True,
            interaction_style="balanced",
        )
        a.validate()

    def test_read_local_resource(self):
        """read_local_resource correctly parses asr_settings from YAML file."""
        yaml_content = "barge_in: true\ninteraction_style: precise\n"

        def exists_asr(path):
            return "asr_settings.yaml" in str(path) or os.path.exists(path)

        def isfile_asr(path):
            return "asr_settings.yaml" in str(path) or os.path.isfile(path)

        with mock_read_from_file(yaml_content):
            with unittest.mock.patch(
                "poly.resources.resource.os.path.exists", side_effect=exists_asr
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.isfile", side_effect=isfile_asr
            ):
                result = AsrSettings.read_local_resource(
                    file_path="voice/speech_recognition/asr_settings.yaml",
                    resource_id="asr-123",
                    resource_name="asr_settings",
                )
        self.assertEqual(result.resource_id, "asr-123")
        self.assertTrue(result.barge_in)
        self.assertEqual(result.interaction_style, "precise")


class KeyphraseBoostingTests(unittest.TestCase):
    """Tests for KeyphraseBoosting resource."""

    def setUp(self):
        MultiResourceYamlResource._file_cache.clear()

    def test_init_to_yaml_dict_from_yaml_dict_roundtrip(self):
        """Init from kwargs, to_yaml_dict, from_yaml_dict roundtrip preserves fields."""
        k = KeyphraseBoosting(
            resource_id="kp-1",
            name="PolyAI",
            keyphrase="PolyAI",
            level="maximum",
        )
        d = k.to_yaml_dict()
        self.assertEqual(d["keyphrase"], "PolyAI")
        self.assertEqual(d["level"], "maximum")
        k2 = KeyphraseBoosting.from_yaml_dict(d, resource_id="kp-1", name="PolyAI")
        self.assertEqual(k2.keyphrase, k.keyphrase)
        self.assertEqual(k2.level, k.level)

    def test_from_yaml_dict_normalizes_level_to_lowercase(self):
        """level is normalized to lowercase."""
        k = KeyphraseBoosting.from_yaml_dict(
            {"keyphrase": "test", "level": "BOOSTED"},
            resource_id="kp-1",
            name="test",
        )
        self.assertEqual(k.level, "boosted")

    def test_validate_missing_keyphrase_raises(self):
        """validate raises ValueError when keyphrase is empty."""
        k = KeyphraseBoosting(resource_id="kp-1", name="", keyphrase="", level="default")
        with self.assertRaises(ValueError) as cm:
            k.validate()
        self.assertIn("Keyphrase is required", str(cm.exception))

    def test_validate_invalid_level_raises(self):
        """validate raises ValueError for invalid level."""
        k = KeyphraseBoosting(
            resource_id="kp-1",
            name="test",
            keyphrase="test",
            level="invalid",
        )
        with self.assertRaises(ValueError) as cm:
            k.validate()
        self.assertIn("Invalid level", str(cm.exception))

    def test_validate_passes_with_valid_data(self):
        """validate succeeds with valid keyphrase and level."""
        k = KeyphraseBoosting(
            resource_id="kp-1",
            name="test",
            keyphrase="reservation",
            level="boosted",
        )
        k.validate()

    def test_read_local_resource(self):
        """read_local_resource correctly parses a keyphrase from the multi-resource YAML."""
        yaml_content = """keyphrases:
  - keyphrase: PolyAI
    level: maximum
  - keyphrase: reservation
    level: boosted
"""

        def exists_kp(path):
            return True if "keyphrase_boosting.yaml" in str(path) else os.path.exists(path)

        def isfile_kp(path):
            return True if "keyphrase_boosting.yaml" in str(path) else os.path.isfile(path)

        def getmtime_kp(path):
            return (
                1.0
                if "keyphrase_boosting.yaml" in str(path)
                else os.path.getmtime(path)
            )

        with mock_read_from_file(yaml_content):
            with unittest.mock.patch(
                "poly.resources.resource.os.path.exists", side_effect=exists_kp
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.isfile", side_effect=isfile_kp
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.getmtime", side_effect=getmtime_kp
            ):
                result = KeyphraseBoosting.read_local_resource(
                    file_path="voice/speech_recognition/keyphrase_boosting.yaml/keyphrases/PolyAI",
                    resource_id="kp-123",
                    resource_name="PolyAI",
                )
        self.assertEqual(result.resource_id, "kp-123")
        self.assertEqual(result.keyphrase, "PolyAI")
        self.assertEqual(result.level, "maximum")


class TranscriptCorrectionTests(unittest.TestCase):
    """Tests for TranscriptCorrection and RegularExpressionRule."""

    def setUp(self):
        MultiResourceYamlResource._file_cache.clear()

    def test_regular_expression_rule_from_yaml_dict_substring_maps_to_partial(self):
        """replacement_type 'substring' in YAML is mapped to 'partial'."""
        rule = RegularExpressionRule.from_yaml_dict(
            {
                "regular_expression": r"\d+",
                "replacement": "X",
                "replacement_type": "substring",
            }
        )
        self.assertEqual(rule.replacement_type, "partial")

    def test_init_to_yaml_dict_from_yaml_dict_roundtrip(self):
        """Init from kwargs, to_yaml_dict, from_yaml_dict roundtrip preserves fields."""
        tc = TranscriptCorrection(
            resource_id="tc-1",
            name="Email domain fix",
            description="Correct email domain misrecognitions",
            regular_expressions=[
                RegularExpressionRule(
                    regular_expression="at gmail dot com",
                    replacement="@gmail.com",
                    replacement_type="full",
                ),
            ],
        )
        d = tc.to_yaml_dict()
        self.assertEqual(d["name"], "Email domain fix")
        self.assertEqual(d["description"], "Correct email domain misrecognitions")
        self.assertEqual(len(d["regular_expressions"]), 1)
        self.assertEqual(d["regular_expressions"][0]["regular_expression"], "at gmail dot com")
        tc2 = TranscriptCorrection.from_yaml_dict(d, resource_id="tc-1", name="Email domain fix")
        self.assertEqual(tc2.name, tc.name)
        self.assertEqual(tc2.description, tc.description)
        self.assertEqual(len(tc2.regular_expressions), 1)
        self.assertEqual(
            tc2.regular_expressions[0].regular_expression,
            tc.regular_expressions[0].regular_expression,
        )

    def test_validate_missing_name_raises(self):
        """validate raises ValueError when name is empty."""
        tc = TranscriptCorrection(
            resource_id="tc-1",
            name="",
            description="desc",
            regular_expressions=[
                RegularExpressionRule(
                    regular_expression="x",
                    replacement="y",
                    replacement_type="full",
                ),
            ],
        )
        with self.assertRaises(ValueError) as cm:
            tc.validate()
        self.assertIn("Correction name is required", str(cm.exception))

    def test_validate_empty_regular_expressions_raises(self):
        """validate raises ValueError when regular_expressions is empty."""
        tc = TranscriptCorrection(
            resource_id="tc-1",
            name="test",
            description="desc",
            regular_expressions=[],
        )
        with self.assertRaises(ValueError) as cm:
            tc.validate()
        self.assertIn("At least one regular expression rule is required", str(cm.exception))

    def test_validate_invalid_replacement_type_raises(self):
        """validate raises ValueError for invalid replacement_type in rule."""
        tc = TranscriptCorrection(
            resource_id="tc-1",
            name="test",
            description="desc",
            regular_expressions=[
                RegularExpressionRule(
                    regular_expression="x",
                    replacement="y",
                    replacement_type="invalid",
                ),
            ],
        )
        with self.assertRaises(ValueError) as cm:
            tc.validate()
        self.assertIn("Invalid replacement_type", str(cm.exception))

    def test_validate_passes_with_valid_data(self):
        """validate succeeds with valid name and rules."""
        tc = TranscriptCorrection(
            resource_id="tc-1",
            name="test",
            description="desc",
            regular_expressions=[
                RegularExpressionRule(
                    regular_expression=r"\b(\d)\b",
                    replacement=r"\1",
                    replacement_type="partial",
                ),
            ],
        )
        tc.validate()

    def test_read_local_resource(self):
        """read_local_resource correctly parses a transcript correction from the multi-resource YAML."""
        yaml_content = """corrections:
  - name: Email domain fix
    description: Correct email domain misrecognitions
    regular_expressions:
      - regular_expression: at gmail dot com
        replacement: "@gmail.com"
        replacement_type: full
"""

        def exists_tc(path):
            return (
                True
                if "transcript_corrections.yaml" in str(path)
                else os.path.exists(path)
            )

        def isfile_tc(path):
            return (
                True
                if "transcript_corrections.yaml" in str(path)
                else os.path.isfile(path)
            )

        def getmtime_tc(path):
            return (
                1.0
                if "transcript_corrections.yaml" in str(path)
                else os.path.getmtime(path)
            )

        with mock_read_from_file(yaml_content):
            with unittest.mock.patch(
                "poly.resources.resource.os.path.exists", side_effect=exists_tc
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.isfile", side_effect=isfile_tc
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.getmtime", side_effect=getmtime_tc
            ):
                result = TranscriptCorrection.read_local_resource(
                    file_path="voice/speech_recognition/transcript_corrections.yaml/corrections/Email_domain_fix",
                    resource_id="tc-123",
                    resource_name="Email domain fix",
                )
        self.assertEqual(result.resource_id, "tc-123")
        self.assertEqual(result.name, "Email domain fix")
        self.assertEqual(len(result.regular_expressions), 1)
        self.assertEqual(
            result.regular_expressions[0].regular_expression,
            "at gmail dot com",
        )


class TestApiIntegrationValidate(unittest.TestCase):
    """Tests for ApiIntegration.validate()."""

    def _make_integration(self, **kwargs):
        """Helper to build an ApiIntegration with sensible defaults."""
        defaults = {
            "resource_id": "int-1",
            "name": "my_api",
            "description": "A valid description",
            "operations": [
                ApiIntegrationOperation(
                    resource_id="op-1", name="list_users", method="GET", resource="/users"
                ),
            ],
        }
        defaults.update(kwargs)
        return ApiIntegration(**defaults)

    def test_valid_integration_does_not_raise(self):
        """A fully valid integration passes validation without error."""
        integration = self._make_integration()
        integration.validate()

    def test_empty_environments_defaults_to_none_auth_type(self):
        """An integration with no environments set defaults without raising."""
        integration = self._make_integration(environments=None)
        integration.validate()  # should not raise; defaults fill in auth_type="none"

    def test_environment_with_missing_auth_type_defaults_to_none(self):
        """auth_type missing from YAML is coerced to 'none' by from_dict."""
        env = ApiIntegrationEnvironments.from_dict(
            {"sandbox": {"base_url": "https://sb.example.com"}}
        )
        self.assertEqual(env.sandbox.auth_type, "none")

    def test_environment_with_empty_auth_type_defaults_to_none(self):
        """auth_type set to empty string in YAML is coerced to 'none' by from_dict."""
        env = ApiIntegrationEnvironments.from_dict(
            {"sandbox": {"base_url": "https://sb.example.com", "auth_type": ""}}
        )
        self.assertEqual(env.sandbox.auth_type, "none")

    def test_environment_with_invalid_auth_type_raises_value_error(self):
        """Validation rejects an environment whose auth_type is not in AVAILABLE_AUTH_TYPES."""
        integration = self._make_integration(
            environments=ApiIntegrationEnvironments.from_dict(
                {"sandbox": {"base_url": "https://sb.example.com", "auth_type": "bearer"}}
            )
        )
        with self.assertRaises(ValueError) as ctx:
            integration.validate()
        self.assertIn("bearer", str(ctx.exception))
        self.assertIn("must be one of", str(ctx.exception))
        for auth_type in AVAILABLE_AUTH_TYPES:
            self.assertIn(auth_type, str(ctx.exception))

    def test_environment_with_invalid_base_url_raises_value_error(self):
        """Validation rejects an environment whose base_url is not a valid URL."""
        integration = self._make_integration(
            environments=ApiIntegrationEnvironments.from_dict(
                {"sandbox": {"base_url": "not-a-url", "auth_type": "none"}}
            )
        )
        with self.assertRaises(ValueError) as ctx:
            integration.validate()
        self.assertIn("not a valid URL path", str(ctx.exception))
        self.assertIn("sandbox", str(ctx.exception))

    def test_environment_with_empty_base_url_is_valid(self):
        """An empty base_url is allowed when auth_type is 'none'."""
        integration = self._make_integration(
            environments=ApiIntegrationEnvironments.from_dict(
                {"sandbox": {"base_url": "", "auth_type": "none"}}
            )
        )
        integration.validate()  # should not raise

    def test_environment_with_empty_base_url_and_non_none_auth_type_raises(self):
        """An empty base_url is invalid when auth_type is set to something other than 'none'."""
        integration = self._make_integration(
            environments=ApiIntegrationEnvironments.from_dict(
                {"sandbox": {"base_url": "", "auth_type": "oauth2"}}
            )
        )
        with self.assertRaises(ValueError) as ctx:
            integration.validate()
        self.assertIn("base_url cannot be empty", str(ctx.exception))
        self.assertIn("sandbox", str(ctx.exception))

    def test_url_pattern_accepts_http_and_https(self):
        """URL_PATTERN matches valid http and https base URLs."""
        self.assertTrue(URL_PATTERN.fullmatch("https://api.example.com"))
        self.assertTrue(URL_PATTERN.fullmatch("http://api.example.com/v1"))
        self.assertTrue(URL_PATTERN.fullmatch(""))
        self.assertFalse(URL_PATTERN.fullmatch("not-a-url"))
        self.assertFalse(URL_PATTERN.fullmatch("ftp://api.example.com"))

    def test_empty_name_raises_value_error(self):
        """Validation rejects an integration whose name is empty."""
        integration = self._make_integration(name="")
        with self.assertRaises(ValueError, msg="Name cannot be empty."):
            integration.validate()

    def test_operation_with_empty_name_raises_value_error(self):
        """Validation rejects an operation whose name is empty."""
        integration = self._make_integration(
            operations=[
                ApiIntegrationOperation(resource_id="op-1", name="", method="GET", resource="/x"),
            ]
        )
        with self.assertRaises(ValueError, msg="Operation name cannot be empty."):
            integration.validate()

    def test_operation_method_is_normalised_to_uppercase(self):
        """Lowercase method in YAML is normalised to uppercase and accepted."""
        integration = self._make_integration(
            operations=[{"name": "list_users", "method": "get", "resource": "/users"}]
        )
        integration.validate()  # should not raise
        op = ApiIntegrationOperation.from_dict({"name": "list_users", "method": "post", "resource": "/users"})
        self.assertEqual(op.method, "POST")

    def test_operation_with_empty_method_raises_value_error(self):
        """Validation rejects an operation whose method is empty."""
        integration = self._make_integration(
            operations=[
                ApiIntegrationOperation(
                    resource_id="op-1", name="get_users", method="", resource="/users"
                ),
            ]
        )
        with self.assertRaises(ValueError) as ctx:
            integration.validate()
        self.assertIn("method cannot be empty", str(ctx.exception))
        self.assertIn("get_users", str(ctx.exception))

    def test_operation_with_invalid_method_raises_value_error(self):
        """Validation rejects an operation whose method is not in AVAILABLE_OPERATIONS."""
        integration = self._make_integration(
            operations=[
                ApiIntegrationOperation(
                    resource_id="op-1", name="get_users", method="INVALID", resource="/users"
                ),
            ]
        )
        with self.assertRaises(ValueError) as ctx:
            integration.validate()
        self.assertIn("INVALID", str(ctx.exception))
        self.assertIn("must be one of", str(ctx.exception))
        for method in AVAILABLE_OPERATIONS:
            self.assertIn(method, str(ctx.exception))

    def test_operation_with_empty_resource_raises_value_error(self):
        """Validation rejects an operation whose resource is empty."""
        integration = self._make_integration(
            operations=[
                ApiIntegrationOperation(
                    resource_id="op-1", name="get_users", method="GET", resource=""
                ),
            ]
        )
        with self.assertRaises(ValueError) as ctx:
            integration.validate()
        self.assertIn("resource cannot be empty", str(ctx.exception))
        self.assertIn("get_users", str(ctx.exception))

    def test_operation_with_invalid_resource_raises_value_error(self):
        """Validation rejects an operation whose resource is not a valid URL path."""
        integration = self._make_integration(
            operations=[
                ApiIntegrationOperation(
                    resource_id="op-1", name="get_users", method="GET", resource="users"
                ),
            ]
        )
        with self.assertRaises(ValueError) as ctx:
            integration.validate()
        self.assertIn("not a valid URL path", str(ctx.exception))
        self.assertIn("get_users", str(ctx.exception))

    def test_operation_resource_with_path_params_is_valid(self):
        """Validation accepts resources with {param} placeholders."""
        integration = self._make_integration(
            operations=[
                ApiIntegrationOperation(
                    resource_id="op-1", name="get_user", method="GET", resource="/users/{user_id}"
                ),
            ]
        )
        integration.validate()  # should not raise

    def test_operation_resource_with_query_string_is_valid(self):
        """Validation accepts resources with an optional ?query (e.g. fixed query params)."""
        integration = self._make_integration(
            operations=[
                ApiIntegrationOperation(
                    resource_id="op-1",
                    name="create_patient",
                    method="POST",
                    resource="/Patient/Create?locationId={location_id}",
                ),
            ]
        )
        integration.validate()  # should not raise

    def test_duplicate_operation_name_and_method_raises_value_error(self):
        """Validation rejects two operations that share the same name and method."""
        integration = self._make_integration(
            operations=[
                ApiIntegrationOperation(
                    resource_id="op-1", name="get_users", method="GET", resource="/users"
                ),
                ApiIntegrationOperation(
                    resource_id="op-2", name="get_users", method="GET", resource="/users/list"
                ),
            ]
        )
        with self.assertRaises(ValueError) as ctx:
            integration.validate()
        self.assertIn("Duplicate operation", str(ctx.exception))
        self.assertIn("get_users", str(ctx.exception))
        self.assertIn("GET", str(ctx.exception))

    def test_same_name_different_method_is_allowed(self):
        """Two operations with the same name but different methods are valid."""
        integration = self._make_integration(
            operations=[
                ApiIntegrationOperation(
                    resource_id="op-1", name="get_users", method="GET", resource="/users"
                ),
                ApiIntegrationOperation(
                    resource_id="op-2", name="get_users", method="POST", resource="/users"
                ),
            ]
        )
        integration.validate()  # should not raise

    def test_multiple_valid_operations_pass(self):
        """An integration with multiple distinct, complete operations is valid."""
        integration = self._make_integration(
            operations=[
                ApiIntegrationOperation(
                    resource_id="op-1", name="list_users", method="GET", resource="/users"
                ),
                ApiIntegrationOperation(
                    resource_id="op-2", name="create_user", method="POST", resource="/users"
                ),
            ]
        )
        integration.validate()

    def test_no_operations_is_valid(self):
        """An integration with zero operations passes validation."""
        integration = self._make_integration(operations=[])
        integration.validate()

    def test_operation_as_dict_is_normalized(self):
        """Validation handles operations stored as raw dicts (via _normalize_op)."""
        integration = self._make_integration(
            operations=[{"name": "get_users", "method": "GET", "resource": "/users"}]
        )
        integration.validate()

    def test_operation_dict_with_empty_name_raises(self):
        """Validation catches empty name even when the operation is a raw dict."""
        integration = self._make_integration(
            operations=[{"name": "", "method": "GET", "resource": "/users"}]
        )
        with self.assertRaises(ValueError, msg="Operation name cannot be empty."):
            integration.validate()


class SafetyFiltersTests(unittest.TestCase):
    """Tests for SafetyFilters and VoiceSafetyFilters resources."""

    _SAMPLE_YAML = (
        "enabled: true\n"
        "type: azure\n"
        "categories:\n"
        "  violence:\n"
        "    enabled: true\n"
        "    level: strict\n"
        "  hate:\n"
        "    enabled: false\n"
        "    level: medium\n"
        "  sexual:\n"
        "    enabled: false\n"
        "    level: lenient\n"
        "  self_harm:\n"
        "    enabled: true\n"
        "    level: strict\n"
    )

    def test_from_yaml_dict_roundtrip(self):
        """to_yaml_dict -> from_yaml_dict roundtrip preserves all fields."""
        sf = SafetyFilters(
            resource_id="sf-1",
            name="safety_filters",
            enabled=True,
            filter_type="azure",
            categories={
                "violence": _SafetyFilterCategory(enabled=True, precision="STRICT"),
                "hate": _SafetyFilterCategory(enabled=False, precision="MEDIUM"),
                "sexual": _SafetyFilterCategory(enabled=False, precision="LOOSE"),
                "self_harm": _SafetyFilterCategory(enabled=True, precision="STRICT"),
            },
        )
        d = sf.to_yaml_dict()
        sf2 = SafetyFilters.from_yaml_dict(d, resource_id="sf-1", name="safety_filters")

        self.assertEqual(sf2.enabled, sf.enabled)
        self.assertEqual(sf2.filter_type, sf.filter_type)
        for cat in ("violence", "hate", "sexual", "self_harm"):
            self.assertEqual(sf2.categories[cat].enabled, sf.categories[cat].enabled)
            self.assertEqual(sf2.categories[cat].precision, sf.categories[cat].precision)
        self.assertEqual(d["categories"]["sexual"]["level"], "lenient")
        self.assertNotIn("precision", d["categories"]["sexual"])

    def test_from_yaml_dict_defaults(self):
        """Missing optional fields fall back to defaults."""
        sf = SafetyFilters.from_yaml_dict({}, resource_id="sf-1", name="safety_filters")
        self.assertTrue(sf.enabled)
        self.assertEqual(sf.filter_type, "azure")
        for cat in ("violence", "hate", "sexual", "self_harm"):
            self.assertFalse(sf.categories[cat].enabled)
            # Internal representation uses backend format (UPPERCASE)
            self.assertEqual(sf.categories[cat].precision, "MEDIUM")

    def test_read_local_resource(self):
        """read_local_resource parses safety_filters from YAML correctly."""

        def exists_sf(path):
            return "safety_filters.yaml" in str(path) or os.path.exists(path)

        def isfile_sf(path):
            return "safety_filters.yaml" in str(path) or os.path.isfile(path)

        with mock_read_from_file(self._SAMPLE_YAML):
            with unittest.mock.patch(
                "poly.resources.resource.os.path.exists", side_effect=exists_sf
            ), unittest.mock.patch(
                "poly.resources.resource.os.path.isfile", side_effect=isfile_sf
            ):
                result = SafetyFilters.read_local_resource(
                    file_path="agent_settings/safety_filters.yaml",
                    resource_id="sf-1",
                    resource_name="safety_filters",
                )

        self.assertEqual(result.resource_id, "sf-1")
        self.assertTrue(result.enabled)
        self.assertEqual(result.filter_type, "azure")
        self.assertTrue(result.categories["violence"].enabled)
        self.assertEqual(result.categories["violence"].precision, "STRICT")
        self.assertFalse(result.categories["hate"].enabled)
        self.assertEqual(result.categories["sexual"].precision, "LOOSE")

    def test_build_update_proto_general(self):
        """SafetyFilters.build_update_proto returns correct protobuf message."""
        sf = SafetyFilters(
            resource_id="sf-1",
            name="safety_filters",
            enabled=False,
            filter_type="azure",
            categories={
                "violence": _SafetyFilterCategory(enabled=True, precision="STRICT"),
                "hate": _SafetyFilterCategory(enabled=False, precision="MEDIUM"),
                "sexual": _SafetyFilterCategory(enabled=False, precision="LOOSE"),
                "self_harm": _SafetyFilterCategory(enabled=True, precision="MEDIUM"),
            },
        )
        proto = sf.build_update_proto()

        self.assertTrue(proto.disabled)
        self.assertEqual(proto.type, "azure")
        self.assertTrue(proto.azure_config.violence.is_active)
        self.assertEqual(proto.azure_config.violence.precision, "STRICT")
        self.assertFalse(proto.azure_config.hate.is_active)
        self.assertEqual(proto.azure_config.sexual.precision, "LOOSE")

    def test_build_update_proto_voice_channel(self):
        """VoiceSafetyFilters.build_update_proto wraps in Channel_UpdateSafetyFilters."""
        from poly.handlers.protobuf.channels_pb2 import VOICE

        vsf = VoiceSafetyFilters(
            resource_id="vsf-1",
            name="voice_safety_filters",
            enabled=True,
            filter_type="azure",
            categories={
                "violence": _SafetyFilterCategory(enabled=True, precision="MEDIUM"),
                "hate": _SafetyFilterCategory(enabled=False, precision="MEDIUM"),
                "sexual": _SafetyFilterCategory(enabled=False, precision="MEDIUM"),
                "self_harm": _SafetyFilterCategory(enabled=False, precision="MEDIUM"),
            },
        )
        proto = vsf.build_update_proto()

        self.assertEqual(proto.channel_type, VOICE)
        self.assertFalse(proto.safety_filters.disabled)
        self.assertTrue(proto.safety_filters.azure_config.violence.is_active)
        self.assertEqual(proto.safety_filters.azure_config.violence.precision, "MEDIUM")

    def _make_content_filter_projection(
        self
    ) -> dict:
        return {
            "disabled": False,
            "type": "azure",
            "azureConfig": {
                "violence": {"isActive": True, "precision": "STRICT"},
                "hate": {"isActive": False, "precision": "MEDIUM"},
                "sexual": {"isActive": False, "precision": "LOOSE"},
                "selfHarm": {"isActive": True, "precision": "STRICT"},
            },
        }

    def test_read_safety_filters_from_projection(self):
        """_read_safety_filters_from_projection parses a full projection correctly."""
        projection = {"contentFilterSettings": self._make_content_filter_projection()}
        result = SyncClientHandler._read_safety_filters_from_projection(projection)

        self.assertIn("safety_filters", result)
        sf = result["safety_filters"]
        self.assertIsInstance(sf, SafetyFilters)
        self.assertTrue(sf.enabled)
        self.assertEqual(sf.filter_type, "azure")
        self.assertTrue(sf.categories["violence"].enabled)
        self.assertEqual(sf.categories["violence"].precision, "STRICT")
        self.assertFalse(sf.categories["hate"].enabled)
        self.assertTrue(sf.categories["self_harm"].enabled)

    def test_read_safety_filters_from_projection_empty(self):
        """_read_safety_filters_from_projection returns {} when key absent."""
        result = SyncClientHandler._read_safety_filters_from_projection({})
        self.assertEqual(result, {})

    def test_read_voice_safety_filters_from_channel_settings_projection(self):
        """_read_channel_settings_from_projection parses voice channel safety filters."""
        projection = {
            "channels": {
                "voice": {
                    "config": {
                        "safetyFilters": self._make_content_filter_projection()
                    }
                }
            }
        }
        result = SyncClientHandler._read_channel_settings_from_projection(projection)

        self.assertIn(VoiceSafetyFilters, result)
        self.assertIn("voice_safety_filters", result[VoiceSafetyFilters])
        vsf = result[VoiceSafetyFilters]["voice_safety_filters"]
        self.assertIsInstance(vsf, VoiceSafetyFilters)
        self.assertTrue(vsf.enabled)  # disabled=False in projection → enabled=True
        self.assertTrue(vsf.categories["self_harm"].enabled)
        self.assertEqual(vsf.categories["self_harm"].precision, "STRICT")

    def test_read_voice_safety_filters_from_channel_settings_projection_empty(self):
        """_read_channel_settings_from_projection returns {} when channels are absent."""
        result = SyncClientHandler._read_channel_settings_from_projection({})
        self.assertEqual(result, {})

    def test_projection_precision_is_converted_to_yaml_level(self):
        """Projection precision values  are converted to YAML level."""
        projection = {"contentFilterSettings": self._make_content_filter_projection()}
        sf = SyncClientHandler._read_safety_filters_from_projection(projection)["safety_filters"]
        # Internal precision stays in backend format (UPPERCASE)
        self.assertEqual(sf.categories["violence"].precision, "STRICT")
        self.assertEqual(sf.categories["sexual"].precision, "LOOSE")
        # YAML output converts to lowercase level terminology
        self.assertEqual(sf.to_yaml_dict()["categories"]["violence"]["level"], "strict")
        self.assertEqual(sf.to_yaml_dict()["categories"]["sexual"]["level"], "lenient")
        self.assertEqual(sf.to_yaml_dict()["categories"]["sexual"]["level"], "lenient")

    def test_validate_invalid_precision_raises(self):
        """validate raises ValueError for an invalid precision value."""
        sf = SafetyFilters(
            resource_id="sf-1",
            name="safety_filters",
            categories={
                "violence": _SafetyFilterCategory(enabled=True, precision="INVALID"),
                "hate": _SafetyFilterCategory(enabled=False, precision="MEDIUM"),
                "sexual": _SafetyFilterCategory(enabled=False, precision="MEDIUM"),
                "self_harm": _SafetyFilterCategory(enabled=False, precision="MEDIUM"),
            },
        )
        with self.assertRaises(ValueError) as cm:
            sf.validate()
        self.assertIn("Invalid level", str(cm.exception))
        self.assertIn("violence", str(cm.exception))

    def test_validate_passes_with_all_valid_precisions(self):
        """validate passes for each valid precision value (backend format)."""
        for precision in ("LOOSE", "MEDIUM", "STRICT"):
            sf = SafetyFilters(
                resource_id="sf-1",
                name="safety_filters",
                categories={
                    cat: _SafetyFilterCategory(enabled=False, precision=precision)
                    for cat in ("violence", "hate", "sexual", "self_harm")
                },
            )
            sf.validate()  # should not raise

    def test_command_types(self):
        """command_type and update_command_type return expected strings."""
        sf = SafetyFilters(resource_id="sf-1", name="safety_filters")
        self.assertEqual(sf.command_type, "content_filter_settings")
        self.assertEqual(sf.update_command_type, "update_content_filter_settings")

        vsf = VoiceSafetyFilters(resource_id="vsf-1", name="voice_safety_filters")
        self.assertEqual(vsf.command_type, "voice_safety_filters")
        self.assertEqual(vsf.update_command_type, "channel_update_safety_filters")

        csf = ChatSafetyFilters(resource_id="csf-1", name="chat_safety_filters")
        self.assertEqual(csf.command_type, "chat_safety_filters")
        self.assertEqual(csf.update_command_type, "channel_update_safety_filters")

    def test_build_update_proto_chat_channel(self):
        """ChatSafetyFilters.build_update_proto wraps in Channel_UpdateSafetyFilters with WEB_CHAT."""
        from poly.handlers.protobuf.channels_pb2 import WEB_CHAT

        csf = ChatSafetyFilters(
            resource_id="csf-1",
            name="chat_safety_filters",
            enabled=True,
            filter_type="azure",
            categories={
                "violence": _SafetyFilterCategory(enabled=True, precision="MEDIUM"),
                "hate": _SafetyFilterCategory(enabled=False, precision="MEDIUM"),
                "sexual": _SafetyFilterCategory(enabled=False, precision="MEDIUM"),
                "self_harm": _SafetyFilterCategory(enabled=False, precision="MEDIUM"),
            },
        )
        proto = csf.build_update_proto()

        self.assertEqual(proto.channel_type, WEB_CHAT)
        self.assertFalse(proto.safety_filters.disabled)
        self.assertTrue(proto.safety_filters.azure_config.violence.is_active)
        self.assertEqual(proto.safety_filters.azure_config.violence.precision, "MEDIUM")

    def test_read_chat_safety_filters_from_channel_settings_projection(self):
        """_read_channel_settings_from_projection parses chat channel safety filters."""
        projection = {
            "channels": {
                "webChat": {
                    "status": True,
                    "config": {"safetyFilters": self._make_content_filter_projection()},
                }
            }
        }
        result = SyncClientHandler._read_channel_settings_from_projection(projection)

        self.assertIn(ChatSafetyFilters, result)
        self.assertIn("chat_safety_filters", result[ChatSafetyFilters])
        csf = result[ChatSafetyFilters]["chat_safety_filters"]
        self.assertIsInstance(csf, ChatSafetyFilters)
        self.assertTrue(csf.enabled)
        self.assertTrue(csf.categories["self_harm"].enabled)
        self.assertEqual(csf.categories["self_harm"].precision, "STRICT")

    def test_read_chat_safety_filters_skipped_when_webchat_status_false(self):
        """_read_channel_settings_from_projection skips chat filters when webChat status is False."""
        projection = {
            "channels": {
                "webChat": {
                    "status": False,
                    "config": {"safetyFilters": self._make_content_filter_projection()},
                }
            }
        }
        result = SyncClientHandler._read_channel_settings_from_projection(projection)

        self.assertNotIn(ChatSafetyFilters, result)

    def test_chat_safety_filters_file_path(self):
        """ChatSafetyFilters.file_path returns the chat subdirectory path."""
        csf = ChatSafetyFilters(resource_id="csf", name="chat_safety_filters")
        self.assertEqual(csf.file_path, os.path.join("chat", "safety_filters.yaml"))

    def test_chat_safety_filters_command_types(self):
        """ChatSafetyFilters returns correct command_type and update_command_type."""
        csf = ChatSafetyFilters(resource_id="csf-1", name="chat_safety_filters")
        self.assertEqual(csf.command_type, "chat_safety_filters")
        self.assertEqual(csf.update_command_type, "channel_update_safety_filters")

    def test_parse_categories_from_azure_config_chat(self):
        """parse_categories_from_azure_config + direct construction produces correct resource."""
        data = self._make_content_filter_projection()
        azure = data.get("azureConfig", {})
        csf = ChatSafetyFilters(
            resource_id="chat_safety_filters",
            name="chat_safety_filters",
            enabled=not data.get("disabled", False),
            filter_type=data.get("type", "azure"),
            categories=parse_categories_from_azure_config(azure),
        )

        self.assertEqual(csf.resource_id, "chat_safety_filters")
        self.assertEqual(csf.name, "chat_safety_filters")
        self.assertTrue(csf.enabled)
        self.assertEqual(csf.filter_type, "azure")
        self.assertTrue(csf.categories["violence"].enabled)
        self.assertEqual(csf.categories["violence"].precision, "STRICT")
        self.assertFalse(csf.categories["hate"].enabled)
        self.assertTrue(csf.categories["self_harm"].enabled)
        self.assertEqual(csf.categories["self_harm"].precision, "STRICT")

    def test_parse_categories_from_azure_config_disabled(self):
        """Direct construction handles disabled=True correctly."""
        data = {
            "disabled": True,
            "type": "azure",
            "azureConfig": {
                "violence": {"isActive": False, "precision": "MEDIUM"},
                "hate": {"isActive": False, "precision": "MEDIUM"},
                "sexual": {"isActive": False, "precision": "MEDIUM"},
                "selfHarm": {"isActive": False, "precision": "MEDIUM"},
            },
        }
        azure = data.get("azureConfig", {})
        csf = ChatSafetyFilters(
            resource_id="chat_safety_filters",
            name="chat_safety_filters",
            enabled=not data.get("disabled", False),
            filter_type=data.get("type", "azure"),
            categories=parse_categories_from_azure_config(azure),
        )

        self.assertFalse(csf.enabled)
        self.assertEqual(csf.resource_id, "chat_safety_filters")

    def test_from_yaml_dict_roundtrip_chat(self):
        """ChatSafetyFilters constructed from azure config produces correct YAML output."""
        data = self._make_content_filter_projection()
        azure = data.get("azureConfig", {})
        csf = ChatSafetyFilters(
            resource_id="chat_safety_filters",
            name="chat_safety_filters",
            enabled=not data.get("disabled", False),
            filter_type=data.get("type", "azure"),
            categories=parse_categories_from_azure_config(azure),
        )
        yaml_out = csf.to_yaml_dict()

        self.assertTrue(yaml_out["enabled"])
        self.assertEqual(yaml_out["type"], "azure")
        self.assertEqual(yaml_out["categories"]["violence"]["enabled"], True)
        self.assertEqual(yaml_out["categories"]["violence"]["level"], "strict")
        self.assertEqual(yaml_out["categories"]["hate"]["enabled"], False)
        self.assertEqual(yaml_out["categories"]["sexual"]["level"], "lenient")
        self.assertEqual(yaml_out["categories"]["self_harm"]["enabled"], True)
        self.assertEqual(yaml_out["categories"]["self_harm"]["level"], "strict")


if __name__ == "__main__":
    unittest.main()
