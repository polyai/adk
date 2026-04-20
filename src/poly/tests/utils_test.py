"""Unit tests for ADK Utils

Copyright PolyAI Limited
"""

import unittest

import poly.resources.resource_utils as resource_utils
from poly import utils
from poly.resources import (
    Entity,
    FlowConfig,
    Function,
    Handoff,
    ResourceMapping,
    SMSTemplate,
    Variable,
    VariantAttribute,
)


class MergeUtilsTests(unittest.TestCase):
    """Tests for merge and conflict related utilities."""

    def test_merge_strings(self):
        original = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        updated = "Line 1 Updated\nLine 2\nLine 3 Updated\nLine 4\nLine 5"
        incoming = "Line 1\nLine 2\nLine 3 Incoming\nLine 4\nLine 5 Incoming"

        expected = [
            "Line 1 Updated",
            "Line 2",
            "<<<<<<<",
            "Line 3 Updated",
            "=======",
            "Line 3 Incoming",
            ">>>>>>>",
            "Line 4",
            "Line 5 Incoming",
        ]
        expected = "\n".join(expected)
        result = utils.merge_strings(original, updated, incoming)

        self.assertEqual(result, expected)

    def test_merge_strings_no_changes(self):
        original = "Line 1\nLine 2\nLine 3"
        result = utils.merge_strings(original, original, original)
        self.assertEqual(result, original)

    def test_merge_strings_only_updated_changes(self):
        original = "Line 1\nLine 2\nLine 3"
        updated = "Line 1 Updated\nLine 2\nLine 3"
        result = utils.merge_strings(original, updated, original)
        self.assertEqual(result, updated)

    def test_merge_strings_only_incoming_changes(self):
        original = "Line 1\nLine 2\nLine 3"
        incoming = "Line 1\nLine 2\nLine 3 Incoming"
        result = utils.merge_strings(original, original, incoming)
        self.assertEqual(result, incoming)

    def test_merge_strings_both_same_change(self):
        original = "Line 1\nLine 2\nLine 3"
        changed = "Line 1\nLine 2 Changed\nLine 3"
        result = utils.merge_strings(original, changed, changed)
        self.assertEqual(result, changed)

    def test_merge_strings_non_overlapping_changes(self):
        original = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        updated = "Line 1 Updated\nLine 2\nLine 3\nLine 4\nLine 5"
        incoming = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5 Incoming"
        result = utils.merge_strings(original, updated, incoming)
        self.assertEqual(result, "Line 1 Updated\nLine 2\nLine 3\nLine 4\nLine 5 Incoming")

    def test_merge_strings_updated_adds_lines(self):
        original = "Line 1\nLine 3"
        updated = "Line 1\nLine 2 New\nLine 3"
        result = utils.merge_strings(original, updated, original)
        self.assertEqual(result, updated)

    def test_merge_strings_incoming_adds_lines(self):
        original = "Line 1\nLine 3"
        incoming = "Line 1\nLine 2 New\nLine 3"
        result = utils.merge_strings(original, original, incoming)
        self.assertEqual(result, incoming)

    def test_merge_strings_updated_deletes_line(self):
        original = "Line 1\nLine 2\nLine 3"
        updated = "Line 1\nLine 3"
        result = utils.merge_strings(original, updated, original)
        self.assertEqual(result, updated)

    def test_merge_strings_incoming_deletes_line(self):
        original = "Line 1\nLine 2\nLine 3"
        incoming = "Line 1\nLine 3"
        result = utils.merge_strings(original, original, incoming)
        self.assertEqual(result, incoming)

    def test_merge_strings_both_delete_same_line(self):
        original = "Line 1\nLine 2\nLine 3"
        deleted = "Line 1\nLine 3"
        result = utils.merge_strings(original, deleted, deleted)
        self.assertEqual(result, deleted)

    def test_merge_strings_empty_original(self):
        result = utils.merge_strings("", "", "")
        self.assertEqual(result, "")

    def test_merge_strings_empty_original_both_add(self):
        result = utils.merge_strings("", "added by a", "added by b")
        self.assertIn("<<<<<<<", result)
        self.assertIn("added by a", result)
        self.assertIn("added by b", result)

    def test_merge_strings_multiple_conflicts(self):
        original = "A\nB\nC\nD\nE"
        updated = "A1\nB\nC1\nD\nE"
        incoming = "A2\nB\nC2\nD\nE"
        result = utils.merge_strings(original, updated, incoming)
        # Both A and C should have conflicts
        self.assertEqual(result.count("<<<<<<<"), 2)
        self.assertEqual(result.count("======="), 2)
        self.assertEqual(result.count(">>>>>>>"), 2)
        self.assertIn("A1", result)
        self.assertIn("A2", result)
        self.assertIn("C1", result)
        self.assertIn("C2", result)
        # B, D, E should be clean
        self.assertIn("B", result)
        self.assertIn("D", result)
        self.assertIn("E", result)

    def test_merge_strings_conflict_markers_in_result(self):
        """Verify conflict output has correct marker structure."""
        original = "keep\nchange me\nkeep"
        updated = "keep\nversion A\nkeep"
        incoming = "keep\nversion B\nkeep"
        result = utils.merge_strings(original, updated, incoming)
        expected = "\n".join([
            "keep",
            "<<<<<<<",
            "version A",
            "=======",
            "version B",
            ">>>>>>>",
            "keep",
        ])
        self.assertEqual(result, expected)

    def test_merge_strings_with_trailing_newlines(self):
        original = "Line 1\nLine 2\n"
        updated = "Line 1 Updated\nLine 2\n"
        incoming = "Line 1\nLine 2\n"
        result = utils.merge_strings(original, updated, incoming)
        self.assertEqual(result, "Line 1 Updated\nLine 2\n")

    def test_merge_strings_conflict_newline_before_markers(self):
        """Conflict content without trailing newlines gets a newline appended.

        When the last line in a conflict region lacks a trailing newline
        (e.g. file has no final newline), the merge must still place
        ======= and >>>>>>> on their own lines.
        """
        original = "line"
        updated = "updated"
        incoming = "incoming"
        result = utils.merge_strings(original, updated, incoming)
        # Each marker must be on its own line, not glued to content
        self.assertIn("updated\n=======\n", result)
        self.assertIn("incoming\n>>>>>>>\n", result)
        # Full structure check
        self.assertEqual(
            result,
            "<<<<<<<\nupdated\n=======\nincoming\n>>>>>>>\n",
        )

    def test_contains_merge_conflict(self):
        no_merge_conflict_code = """import random
def test_code(conv: Conversation, test_param: int):
    print(random.randint(1, test_param))
        """

        self.assertFalse(resource_utils.contains_merge_conflict(no_merge_conflict_code))

        merge_conflict_code = "\n".join(
            [
                "import random",
                "",
                "<<<<<<<",
                "def test_code(conv: Conversation, test_param: int):",
                "    print(random.randint(1, test_param))",
                "=======",
                "def test_code(conv: Conversation, diff_param: int):",
                "    print(random.randint(1, diff_param))",
                ">>>>>>>",
                "",
            ]
        )

        self.assertTrue(resource_utils.contains_merge_conflict(merge_conflict_code))

        merge_conflict_wrong_order = "\n".join(
            [
                "import random",
                "",
                "=======",
                "def test_code(conv: Conversation, test_param: int):",
                "    print(random.randint(1, test_param))",
                "<<<<<<<",
                "def test_code(conv: Conversation, diff_param: int):",
                "    print(random.randint(1, diff_param))",
                ">>>>>>>",
                "",
            ]
        )
        self.assertFalse(resource_utils.contains_merge_conflict(merge_conflict_wrong_order))


class ImportUtilsTests(unittest.TestCase):
    """Tests for import and file generation utilities."""

    def test_create_import_file_contents(self):
        """Test creating import file contents"""
        contents = utils.create_import_file_contents()

        self.assertIn("# flake8: noqa", contents)
        self.assertIn("# <AUTO GENERATED>", contents)


class CodeUtilsTests(unittest.TestCase):
    """Tests for code manipulation and formatting utilities."""

    def test_restore_function_def_line(self):
        # Test restoring function definition line
        expected_function_def_line = "def test_code(conv: Conversation, param1: str, param2: int):"

        contents = """import random
def test_code(
    conv: Conversation, param1: str, param2: int
):
    print(random.randint(1, param2))
        """

        restored_code = resource_utils.restore_function_def_line(contents, "test_code")
        self.assertIn(
            expected_function_def_line,
            restored_code,
        )

        one_line_code = """import random
def test_code(conv: Conversation, param1: str, param2: int):
    print(random.randint(1, param2))
        """

        restored_code = resource_utils.restore_function_def_line(one_line_code, "test_code")
        self.assertIn(
            expected_function_def_line,
            restored_code,
        )

        multi_line_code = """import random
def test_code(
    conv: Conversation,
    param1: str,
    param2: int
):
    print(random.randint(1, param2))
        """

        restored_code = resource_utils.restore_function_def_line(multi_line_code, "test_code")
        self.assertIn(
            expected_function_def_line,
            restored_code,
        )

        multi_line_code_comma = """import random
def test_code(
    conv: Conversation,
    param1: str,
    param2: int,
):
    print(random.randint(1, param2))
        """

        restored_code = resource_utils.restore_function_def_line(multi_line_code_comma, "test_code")
        self.assertIn(
            expected_function_def_line,
            restored_code,
        )


        with_docstring_code = """import random
def test_code(
    conv: Conversation,
    param1: str,
    param2: int
):
    \"\"\"This is a docstring.\"\"\"
    print(random.randint(1, param2))
        """

        restored_code = resource_utils.restore_function_def_line(with_docstring_code, "test_code")
        self.assertIn(
            expected_function_def_line,
            restored_code,
        )

        with_decorator_code = """import random
@decorator
def test_code(
    conv: Conversation,
    param1: str,
    param2: int
):
    print(random.randint(1, param2))
        """

        restored_code = resource_utils.restore_function_def_line(with_decorator_code, "test_code")
        self.assertIn(
            expected_function_def_line,
            restored_code,
        )

        invalid_code = """import random
def test_code(
    conv: Conversation,
    param1: str,
    param2: int
):
    print(random.randint(1, param2
        """
        restored_code = resource_utils.restore_function_def_line(invalid_code, "test_code")
        self.assertEqual(restored_code, invalid_code)


    def test_get_diff(self):
        """Test getting diff between strings"""
        original = "line1\nline2\nline3"
        updated = "line1\nmodified line2\nline3"

        diff = resource_utils.get_diff(original, updated)

        self.assertIn("line2", diff)
        self.assertIn("modified line2", diff)


class StringUtilsTests(unittest.TestCase):
    """Tests for string manipulation and formatting utilities."""

    def test_clean_name(self):
        alphanumeric = "Valid Name 123"
        self.assertEqual(resource_utils.clean_name(alphanumeric), "valid_name_123")

        punctuation = "This is a Test_Name! With@Special#Chars$ %^&*()"
        cleaned_name = resource_utils.clean_name(punctuation)
        self.assertEqual(cleaned_name, "this_is_a_test_name_with_special_chars")

        allow_uppercase = "ThisIsATestName"
        self.assertEqual(resource_utils.clean_name(allow_uppercase, lowercase=False), "ThisIsATestName")

        allow_non_english = "こんにちは"
        self.assertEqual(resource_utils.clean_name(allow_non_english, lowercase=False), "こんにちは")

    def test_to_snake_case(self):
        camel_case = "ThisIsATestName"
        self.assertEqual(resource_utils.to_snake_case(camel_case), "this_is_a_test_name")

        mixed_case = "thisIsAnotherTestName"
        self.assertEqual(resource_utils.to_snake_case(mixed_case), "this_is_another_test_name")

    def test_to_camel_case(self):
        snake_case = "this_is_a_test_name"
        self.assertEqual(resource_utils.to_camel_case(snake_case), "thisIsATestName")

        mixed_case = "this_is_another_test_name"
        self.assertEqual(resource_utils.to_camel_case(mixed_case), "thisIsAnotherTestName")


class ResourceReferenceTests(unittest.TestCase):
    """Tests for resource reference extraction and manipulation."""

    def test_get_references_from_prompt_all_types(self):
        prompt = (
            "Use the following resources:\n"
            "- {{twilio_sms:sms-id}} and {{twilio_sms:sms-id-2}}\n"
            "- {{ho:handoff-id}}\n"
            "- {{attr:attribute-id}}\n"
            "- {{ft:transition_function_id}}\n"
            "- {{fn:global_function_id}}\n"
            "- {{entity:entity_id}}\n"
            "- {{vrbl:customer_name}}\n"
            "Provide the latest weather and news updates."
        )

        references = resource_utils.get_references_from_prompt(prompt)
        expected_references = {
            "sms": {"sms-id": True, "sms-id-2": True},
            "handoff": {"handoff-id": True},
            "attributes": {"attribute-id": True},
            "transition_functions": {"transition_function_id": True},
            "global_functions": {"global_function_id": True},
            "entities": {"entity_id": True},
            "variables": {"customer_name": True},
        }
        self.assertEqual(references, expected_references)

    def test_get_references_from_prompt_subset(self):
        prompt = (
            "Use the following resources:\n"
            "- {{twilio_sms:sms-id}}\n"
            "- {{handoff:handoff-id}}\n"
            "- {{attr:attribute-id}}\n"
            "- {{ft:transition_function_id}}\n"
            "- {{fn:global_function_id}}\n"
            "- {{entity:entity_id}}\n"
            "Provide the latest weather and news updates."
        )

        subset_references = resource_utils.get_references_from_prompt(
            prompt, valid_references=["sms", "attributes", "entities"]
        )
        expected_subset = {
            "sms": {"sms-id": True},
            "attributes": {"attribute-id": True},
            "entities": {"entity_id": True},
        }
        self.assertEqual(subset_references, expected_subset)

    def test_get_references_from_prompt_no_references(self):
        no_ref_prompt = "This prompt has no resource references."
        no_references = resource_utils.get_references_from_prompt(no_ref_prompt)
        expected = {
            "attributes": {},
            "entities": {},
            "sms": {},
            "handoff": {},
            "transition_functions": {},
            "global_functions": {},
            "variables": {},
        }
        self.assertEqual(no_references, expected)

    def test_get_references_from_prompt_variables(self):
        """Test extracting {{vrbl:variable_name}} references from prompts."""
        prompt = (
            "Hello {{vrbl:customer_name}}, your order {{vrbl:order_id}} is ready. "
            "Use {{vrbl:promo_code}} for a discount."
        )
        references = resource_utils.get_references_from_prompt(prompt)
        expected = {
            "variables": {"customer_name": True, "order_id": True, "promo_code": True},
        }
        self.assertEqual(references["variables"], expected["variables"])

    def test_extract_variable_names_from_code(self):
        """Test extracting variable names from conv.state.<name> in function code."""
        code_empty = ""
        self.assertEqual(resource_utils.extract_variable_names_from_code(code_empty), set())

        code_no_vars = "def foo(conv: Conversation):\n    return 'hello'"
        self.assertEqual(resource_utils.extract_variable_names_from_code(code_no_vars), set())

        code_single = "def foo(conv: Conversation):\n    x = conv.state.customer_name"
        self.assertEqual(
            resource_utils.extract_variable_names_from_code(code_single),
            {"customer_name"},
        )

        code_multiple = """
def process(conv: Conversation):
    name = conv.state.customer_name
    order = conv.state.order_id
    return conv.state.order_id
"""
        self.assertEqual(
            resource_utils.extract_variable_names_from_code(code_multiple),
            {"customer_name", "order_id"},
        )

        code_underscore = "conv.state.my_var_name"
        self.assertEqual(
            resource_utils.extract_variable_names_from_code(code_underscore),
            {"my_var_name"},
        )


class ValidateReferencesTests(unittest.TestCase):
    """Direct unit tests for validate_references."""

    def test_validate_references_empty(self):
        """Empty references return valid."""
        valid, invalid = resource_utils.validate_references({}, [])
        self.assertTrue(valid)
        self.assertEqual(invalid, [])

        valid, invalid = resource_utils.validate_references(
            {"attributes": {}, "variables": {}}, []
        )
        self.assertTrue(valid)
        self.assertEqual(invalid, [])

    def test_validate_references_valid(self):
        """All references in mappings return valid."""
        mappings = [
            ResourceMapping(
                resource_id="attr-customer",
                resource_name="customer",
                resource_type=VariantAttribute,
                file_path="config/variant_attributes.yaml/variant_attributes/customer",
                flow_name=None,
                resource_prefix="attr",
            ),
            ResourceMapping(
                resource_id="VAR-my_var",
                resource_name="my_var",
                resource_type=Variable,
                file_path="variables/my_var",
                flow_name=None,
                resource_prefix="vrbl",
            ),
        ]
        references = {"attributes": {"attr-customer": True}, "variables": {"VAR-my_var": True}}
        valid, invalid = resource_utils.validate_references(references, mappings)
        self.assertTrue(valid)
        self.assertEqual(invalid, [])

    def test_validate_references_invalid(self):
        """Missing references return invalid list."""
        mappings = [
            ResourceMapping(
                resource_id="attr-customer",
                resource_name="customer",
                resource_type=VariantAttribute,
                file_path="config/variant_attributes.yaml/variant_attributes/customer",
                flow_name=None,
                resource_prefix="attr",
            ),
        ]
        references = {
            "attributes": {"attr-customer": True, "attr-nonexistent": True},
            "variables": {"VAR-missing": True},
        }
        valid, invalid = resource_utils.validate_references(references, mappings)
        self.assertFalse(valid)
        self.assertEqual(
            set(invalid),
            {"attributes: attr-nonexistent", "variables: VAR-missing"},
        )

    def test_validate_references_flow_name_scoping(self):
        """Flow-scoped resources only match when flow_name matches."""
        mappings = [
            ResourceMapping(
                resource_id="FUNCTION-flow_a_func",
                resource_name="flow_a_func",
                resource_type=Function,
                file_path="flows/flow_a/functions/flow_a_func.py",
                flow_name="Flow A",
                resource_prefix="ft",
            ),
        ]
        references = {"transition_functions": {"FUNCTION-flow_a_func": True}}
        valid, invalid = resource_utils.validate_references(
            references, mappings, flow_name="Flow A"
        )
        self.assertTrue(valid)
        self.assertEqual(invalid, [])

        valid, invalid = resource_utils.validate_references(
            references, mappings, flow_name="Flow B"
        )
        self.assertFalse(valid)
        self.assertIn("transition_functions: FUNCTION-flow_a_func", invalid)


class ResourceMappingTests(unittest.TestCase):
    """Tests for resource ID/name mapping utilities."""

    TEST_RESOURCE_MAPPINGS = [
        ResourceMapping(
            resource_id="function-1",
            resource_name="Function 1",
            resource_type=Function,
            file_path="functions/function_1.py",
            flow_name=None,
            resource_prefix="fn",
        ),
        ResourceMapping(
            resource_id="function-2",
            resource_name="Function 2",
            resource_type=Function,
            file_path="functions/function_2.py",
            flow_name=None,
            resource_prefix="fn",
        ),
        ResourceMapping(
            resource_id="flow-function-1",
            resource_name="Flow Function",
            resource_type=Function,
            file_path="functions/flow_1/functions/flow_function.py",
            flow_name="Flow 1",
            resource_prefix="ft",
        ),
        ResourceMapping(
            resource_id="flow-function-2",
            resource_name="Flow Function",
            resource_type=Function,
            file_path="functions/flow_2/functions/flow_function.py",
            flow_name="Flow 2",
            resource_prefix="ft",
        ),
        ResourceMapping(
            resource_id="attr-customer-name",
            resource_name="customer-name",
            resource_type=VariantAttribute,
            file_path="config/variant_attributes.yaml/variant_attributes/customer-name",
            flow_name=None,
            resource_prefix="attr",
        ),
        ResourceMapping(
            resource_id="handoff-1",
            resource_name="default",
            resource_type=Handoff,
            file_path="config/handoffs.yaml/handoffs/default",
            flow_name=None,
            resource_prefix="ho",
        ),
        ResourceMapping(
            resource_id="SMS_TEMPLATE-123",
            resource_name="test_template",
            resource_type=SMSTemplate,
            file_path="config/sms_templates.yaml/sms_templates/test_template",
            flow_name=None,
            resource_prefix="twilio_sms",
        ),
        ResourceMapping(
            resource_id="ENTITY-customer_name",
            resource_name="customer_name",
            resource_type=Entity,
            file_path="config/entities.yaml/entities/customer_name",
            flow_name=None,
            resource_prefix="entity",
        ),
        ResourceMapping(
            resource_id="VAR-customer_name",
            resource_name="customer_name",
            resource_type=Variable,
            file_path="variables/customer_name",
            flow_name=None,
            resource_prefix="vrbl",
        ),
        ResourceMapping(
            resource_id="VAR-order_id",
            resource_name="order_id",
            resource_type=Variable,
            file_path="variables/order_id",
            flow_name=None,
            resource_prefix="vrbl",
        ),
    ]

    def test_replace_resource_ids_with_names_basic(self):
        prompt = "Access {{fn:function-1}} and then call {{fn:function-2}} for processing."

        updated_prompt = resource_utils.replace_resource_ids_with_names(
            prompt, self.TEST_RESOURCE_MAPPINGS
        )

        expected_prompt = "Access {{fn:Function 1}} and then call {{fn:Function 2}} for processing."

        self.assertEqual(updated_prompt, expected_prompt)

    def test_replace_resource_ids_with_names_wrong_ids(self):
        prompt_with_wrong_ids = "Access {{fn:wrong-id-1}} and then call {{fn:wrong-id-2}}."
        updated_prompt_wrong_ids = resource_utils.replace_resource_ids_with_names(
            prompt_with_wrong_ids, self.TEST_RESOURCE_MAPPINGS
        )
        self.assertEqual(updated_prompt_wrong_ids, prompt_with_wrong_ids)

    def test_replace_resource_ids_with_names_wrong_prefixes(self):
        prompt_with_wrong_prefixes = (
            "Access {{ft:function-1}} and then call {{ft:function-2}} for processing."
        )
        updated_prompt_wrong_prefixes = resource_utils.replace_resource_ids_with_names(
            prompt_with_wrong_prefixes, self.TEST_RESOURCE_MAPPINGS
        )
        self.assertEqual(updated_prompt_wrong_prefixes, prompt_with_wrong_prefixes)

    def test_replace_resource_ids_with_names_flow_functions_no_flow(self):
        global_prompt_with_flow_functions = (
            "Access {{ft:flow-function-1}} and then call {{ft:flow-function-2}} for processing."
        )
        updated_prompt = resource_utils.replace_resource_ids_with_names(
            global_prompt_with_flow_functions, self.TEST_RESOURCE_MAPPINGS
        )
        self.assertEqual(updated_prompt, global_prompt_with_flow_functions)

    def test_replace_resource_ids_with_names_flow_functions_with_flow(self):
        prompt_with_flow_functions = "In the flow, call {{ft:flow-function-1}}, {{fn:function-1}} and then {{ft:flow-function-2}}."
        updated_prompt_flow_functions = resource_utils.replace_resource_ids_with_names(
            prompt_with_flow_functions,
            self.TEST_RESOURCE_MAPPINGS,
            flow_folder_name="flow_1",
        )
        expected_prompt_flow_functions = "In the flow, call {{ft:Flow Function}}, {{fn:Function 1}} and then {{ft:flow-function-2}}."
        self.assertEqual(updated_prompt_flow_functions, expected_prompt_flow_functions)

    def test_replace_resource_names_with_ids(self):
        prompt = "Access {{fn:Function 1}} and then call {{fn:Function 2}} for processing."

        updated_prompt = resource_utils.replace_resource_names_with_ids(
            prompt, self.TEST_RESOURCE_MAPPINGS
        )

        expected_prompt = "Access {{fn:function-1}} and then call {{fn:function-2}} for processing."

        self.assertEqual(updated_prompt, expected_prompt)

    def test_replace_resource_names_with_ids_wrong_names(self):
        prompt_with_wrong_names = "Access {{fn:Wrong Name 1}} and then call {{fn:Wrong Name 2}}."
        updated_prompt_wrong_names = resource_utils.replace_resource_names_with_ids(
            prompt_with_wrong_names, self.TEST_RESOURCE_MAPPINGS
        )
        self.assertEqual(updated_prompt_wrong_names, prompt_with_wrong_names)

    def test_replace_resource_names_with_ids_wrong_prefixes(self):
        prompt_with_wrong_prefixes = (
            "Access {{ft:Function 1}} and then call {{ft:Function 2}} for processing."
        )
        updated_prompt_wrong_prefixes = resource_utils.replace_resource_names_with_ids(
            prompt_with_wrong_prefixes, self.TEST_RESOURCE_MAPPINGS
        )
        self.assertEqual(updated_prompt_wrong_prefixes, prompt_with_wrong_prefixes)

    def test_replace_resource_names_with_ids_flow_functions_no_flow(self):
        global_prompt_with_flow_functions = (
            "Access {{ft:Flow Function}} and then call {{ft:Flow Function}} for processing."
        )
        updated_prompt = resource_utils.replace_resource_names_with_ids(
            global_prompt_with_flow_functions, self.TEST_RESOURCE_MAPPINGS
        )
        self.assertEqual(updated_prompt, global_prompt_with_flow_functions)

    def test_replace_resource_names_with_ids_flow_functions_with_flow(self):
        prompt_with_flow_functions = "In the flow, call {{ft:Flow Function}}, {{fn:Function 1}}."

        # Flow 1
        updated_prompt_flow_functions = resource_utils.replace_resource_names_with_ids(
            prompt_with_flow_functions,
            self.TEST_RESOURCE_MAPPINGS,
            flow_folder_name="flow_1",
        )
        expected_prompt_flow_functions = (
            "In the flow, call {{ft:flow-function-1}}, {{fn:function-1}}."
        )
        self.assertEqual(updated_prompt_flow_functions, expected_prompt_flow_functions)

        # Flow 2
        updated_prompt_flow_functions = resource_utils.replace_resource_names_with_ids(
            prompt_with_flow_functions,
            self.TEST_RESOURCE_MAPPINGS,
            flow_folder_name="flow_2",
        )
        expected_prompt_flow_functions = (
            "In the flow, call {{ft:flow-function-2}}, {{fn:function-1}}."
        )
        self.assertEqual(updated_prompt_flow_functions, expected_prompt_flow_functions)

    def test_replace_resource_ids_with_names_attributes_handoff_sms_entities(self):
        """Test IDs->names swap for attr, ho, twilio_sms, entity references."""
        prompt = (
            "Use {{attr:attr-customer-name}}, {{ho:handoff-1}}, "
            "{{twilio_sms:SMS_TEMPLATE-123}} and {{entity:ENTITY-customer_name}}."
        )
        updated = resource_utils.replace_resource_ids_with_names(
            prompt, self.TEST_RESOURCE_MAPPINGS
        )
        expected = (
            "Use {{attr:customer-name}}, {{ho:default}}, "
            "{{twilio_sms:test_template}} and {{entity:customer_name}}."
        )
        self.assertEqual(updated, expected)

    def test_replace_resource_names_with_ids_attributes_handoff_sms_entities(self):
        """Test names->IDs swap for attr, ho, twilio_sms, entity references."""
        prompt = (
            "Use {{attr:customer-name}}, {{ho:default}}, "
            "{{twilio_sms:test_template}} and {{entity:customer_name}}."
        )
        updated = resource_utils.replace_resource_names_with_ids(
            prompt, self.TEST_RESOURCE_MAPPINGS
        )
        expected = (
            "Use {{attr:attr-customer-name}}, {{ho:handoff-1}}, "
            "{{twilio_sms:SMS_TEMPLATE-123}} and {{entity:ENTITY-customer_name}}."
        )
        self.assertEqual(updated, expected)

    def test_replace_resource_ids_with_names_variables(self):
        """Test IDs->names swap for vrbl (variable) references."""
        prompt = "Hello {{vrbl:VAR-customer_name}}, order {{vrbl:VAR-order_id}}."
        updated = resource_utils.replace_resource_ids_with_names(
            prompt, self.TEST_RESOURCE_MAPPINGS
        )
        expected = "Hello {{vrbl:customer_name}}, order {{vrbl:order_id}}."
        self.assertEqual(updated, expected)

    def test_replace_resource_names_with_ids_variables(self):
        """Test names->IDs swap for vrbl (variable) references."""
        prompt = "Hello {{vrbl:customer_name}}, order {{vrbl:order_id}}."
        updated = resource_utils.replace_resource_names_with_ids(
            prompt, self.TEST_RESOURCE_MAPPINGS
        )
        expected = "Hello {{vrbl:VAR-customer_name}}, order {{vrbl:VAR-order_id}}."
        self.assertEqual(updated, expected)


class FlowUtilsTests(unittest.TestCase):
    """Tests for flow-related utilities."""

    def test_get_flow_id_from_flow_name(self):
        resource_mappings = [
            ResourceMapping(
                resource_id="flow-123",
                resource_name="Test Flow Name",
                resource_type=FlowConfig,
                file_path="flows/test_flow_name/flow_config.yaml",
                flow_name="Test Flow Name",
                resource_prefix=None,
            ),
            ResourceMapping(
                resource_id="flow-456",
                resource_name="Another Flow",
                resource_type=FlowConfig,
                file_path="flows/another_flow/flow_config.yaml",
                flow_name="Another Flow",
                resource_prefix=None,
            ),
        ]

        # Test find flow
        formatted_flow_name = "test_flow_name"
        flow_id, flow_name = resource_utils.get_flow_id_from_flow_name(
            formatted_flow_name, resource_mappings
        )
        self.assertEqual(flow_id, "flow-123")
        self.assertEqual(flow_name, "Test Flow Name")

        # Test flow not found
        formatted_flow_name_not_found = "non_existent_flow"
        flow_id_none, flow_name_none = resource_utils.get_flow_id_from_flow_name(
            formatted_flow_name_not_found, resource_mappings
        )
        self.assertIsNone(flow_id_none)
        self.assertIsNone(flow_name_none)

    def test_get_flow_name_from_path(self):
        path_with_flow = "flows/flow_1/functions/flow_function.py"
        flow_name = resource_utils.get_flow_name_from_path(path_with_flow)
        self.assertEqual(flow_name, "flow_1")

        path_without_flow = "functions/global_function.py"
        flow_name_none = resource_utils.get_flow_name_from_path(path_without_flow)
        self.assertIsNone(flow_name_none)

    # TODO: Test assigning positions to flow steps


if __name__ == "__main__":
    unittest.main()
