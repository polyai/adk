"""Handling and managing an Agent Studio Experimental Config

Copyright PolyAI Limited
"""

import json
import os
from dataclasses import dataclass, field

import jsonschema

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.experimental_config_pb2 import ExperimentalConfig_UpdateConfig
from poly.resources.resource import Resource


@dataclass
class ExperimentalConfig(Resource):
    """ExperimentalConfig resource"""

    config: dict = field(default_factory=dict)

    @property
    def file_path(self) -> str:
        return os.path.join("agent_settings", "experimental_config.json")

    @property
    def raw(self) -> str:
        return json.dumps(self.config, indent=2, sort_keys=True)

    @staticmethod
    def format_resource(content: str, file_name: str = None, **kwargs) -> str:
        """Format the resource content using in-process JSON formatting."""
        return utils.format_json_python(content)

    @staticmethod
    def make_pretty(contents: str, **kwargs) -> str:
        return contents

    @staticmethod
    def from_pretty(contents: str, **kwargs) -> str:
        return contents

    @classmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "ExperimentalConfig":
        content = cls.read_to_raw(file_path, **kwargs)
        content_json = json.loads(content)
        return cls(resource_id=resource_id, name=resource_name, config=content_json)

    def build_update_proto(self) -> ExperimentalConfig_UpdateConfig:
        return ExperimentalConfig_UpdateConfig(
            id=self.resource_id,
            features=self.config,
        )

    def build_delete_proto(self):
        return NotImplementedError("ExperimentalConfig does not support deletion.")

    def build_create_proto(self):
        return NotImplementedError("ExperimentalConfig does not support creation.")

    def validate(self, **kwargs):
        # Validate against schema
        openapi_schema = utils.load_yaml(
            open(
                os.path.join(os.path.dirname(__file__), "experimental_config_schema.yaml"),
                encoding="utf-8",
            )
        )
        additional_features = openapi_schema["components"]["schemas"]["additional_features"]
        resolver = jsonschema.RefResolver.from_schema(openapi_schema)

        validator = jsonschema.Draft202012Validator(additional_features, resolver=resolver)
        validator.validate(self.config)

    @property
    def command_type(self) -> str:
        return "experimental_config"

    @property
    def update_command_type(self) -> str:
        return "experimental_config_update_config"

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        file_path = os.path.join(base_path, "agent_settings", "experimental_config.json")

        if not os.path.exists(file_path):
            return []

        return [file_path]
