"""Regression tests for YAML 1.1-safe scalar quoting.

ruamel emits YAML 1.2. Anything the ADK writes may be read by a YAML 1.1 parser,
so a string the dumper leaves bare can come back as a different type entirely.
"""

import yaml as pyyaml

from poly.resources.resource_utils import dump_yaml


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
