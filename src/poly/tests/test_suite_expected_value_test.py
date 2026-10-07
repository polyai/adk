"""Regression tests for YAML 1.1-safe scalar quoting.

ruamel emits YAML 1.2. Anything the ADK writes may be read by a YAML 1.1 parser,
so a string the dumper leaves bare can come back as a different type entirely.
"""

import yaml as pyyaml

from poly.resources.resource_utils import dump_yaml
from poly.resources.test_suite import FunctionCallArgumentAssertion


class TestYaml11SafeQuoting:
    """The dumper must not emit a string a YAML 1.1 reader would retype."""

    def test_sexagesimal_time_is_quoted(self):
        # Unquoted 19:00 is 19*60 = 1140 to a YAML 1.1 parser.
        assert dump_yaml({"time": "19:00"}).strip() == "time: '19:00'"

    def test_yes_no_are_quoted(self):
        assert dump_yaml({"a": "yes"}).strip() == "a: 'yes'"
        assert dump_yaml({"a": "off"}).strip() == "a: 'off'"

    def test_numeric_string_is_quoted(self):
        assert dump_yaml({"id": "12348"}).strip() == "id: '12348'"

    def test_date_like_string_is_quoted(self):
        # Unquoted 2027-09-08 is a date object to a YAML 1.1 parser -- the same
        # retyping parse_simulated_at() already has to defend against on read.
        assert dump_yaml({"date": "2027-09-08"}).strip() == "date: '2027-09-08'"

    def test_single_letter_booleans_are_quoted(self):
        # y/n/Y/N are booleans under YAML 1.1 but plain strings under 1.2.
        for value in ("y", "n", "Y", "N"):
            assert dump_yaml({"a": value}).strip() == f"a: '{value}'"

    def test_special_floats_are_quoted(self):
        for value in (".inf", "-.inf", ".nan", "1e3"):
            assert dump_yaml({"a": value}).strip() == f"a: '{value}'"

    def test_ordinary_string_is_not_quoted(self):
        assert dump_yaml({"name": "hello"}).strip() == "name: hello"
        assert dump_yaml({"name": "a:b"}).strip() == "name: a:b"

    def test_round_trips_through_a_yaml_1_1_reader(self):
        data = {
            "time": "19:00",
            "flag": "yes",
            "id": "12348",
            "date": "2027-09-08",
            "short": "y",
            "inf": ".inf",
            "name": "hello",
        }
        assert pyyaml.safe_load(dump_yaml(data)) == data


class TestExpectedValueWireEncoding:
    """Pulled native values must re-encode to the string the platform decodes.

    Agent Studio decodes expected_value by value_type (parseInt / parseFloat /
    raw === "true"), so these assert the inverse of that decoder.
    """

    def test_integer_encodes_for_parseint(self):
        assert FunctionCallArgumentAssertion("party_size", 15, "integer").expected_value == "15"

    def test_float_encodes_for_parsefloat(self):
        assert FunctionCallArgumentAssertion("total", 12.5, "float").expected_value == "12.5"

    def test_booleans_encode_lowercase(self):
        # "True" would decode to false on the platform side.
        assert FunctionCallArgumentAssertion("ok", True, "boolean").expected_value == "true"
        assert FunctionCallArgumentAssertion("ok", False, "boolean").expected_value == "false"

    def test_strings_and_none_are_untouched(self):
        assert FunctionCallArgumentAssertion("t", "19:00", "string").expected_value == "19:00"
        assert FunctionCallArgumentAssertion("t", None, "string").expected_value is None

    def test_pulled_native_value_survives_to_proto(self):
        proto = FunctionCallArgumentAssertion("party_size", 15, "integer").to_proto()
        assert proto.expected_value == "15"

    def test_round_trip_is_stable_in_yaml(self):
        arg = FunctionCallArgumentAssertion("party_size", 15, "integer")
        assert dump_yaml(arg.to_yaml_dict()).splitlines()[0] == "parameter_name: party_size"
        assert "expected_value: '15'" in dump_yaml(arg.to_yaml_dict())
