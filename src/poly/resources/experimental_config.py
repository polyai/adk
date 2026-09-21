"""Handling and managing an Agent Studio Experimental Config

Copyright PolyAI Limited
"""

import json
import logging
import os
from dataclasses import dataclass, field

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.experimental_config_pb2 import ExperimentalConfig_UpdateConfig
from poly.resources.resource import Resource, register_resource

logger = logging.getLogger(__name__)


@register_resource("experimental_config")
@dataclass
class ExperimentalConfig(Resource):
    """ExperimentalConfig resource"""

    config: dict = field(default_factory=dict)

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "ExperimentalConfig"]:
        """Parse experimental config from a projection dict."""
        experimental_configs = (
            projection.get("experimentalConfig", {})
            .get("experimentalConfigs", {})
            .get("entities", {})
        )
        # "features" is optional in the API schema, so it can't distinguish an
        # auth-filtered config from one with no features set. "active" always is.
        if "experimentalConfig" not in projection or any(
            "active" not in config for config in experimental_configs.values()
        ):
            logger.debug("No read access to experimental config - it will not be pulled.")
            return {}

        config_id, config_data = (
            next(iter(experimental_configs.items()), ("default", {}))
            if experimental_configs
            else ("default", {})
        )
        return {
            config_id: cls(
                resource_id=config_id,
                name="experimental_config",
                config=config_data.get("features", {}),
            )
        }

    @property
    def file_path(self) -> str:
        return os.path.join("agent_settings", "experimental_config.json")

    @property
    def raw(self) -> str:
        return json.dumps(self.config, indent=2, sort_keys=True, ensure_ascii=False)

    @staticmethod
    def format_resource(content: str, file_name: str = None, **kwargs) -> str:
        """Format the resource content using in-process JSON formatting."""
        return utils.format_json(content)

    @staticmethod
    def make_pretty(contents: str, **kwargs) -> str:
        return contents

    @classmethod
    def from_pretty(cls, contents: str, **kwargs) -> str:
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
        import jsonschema

        # Validate against schema
        schema_path = os.environ.get("ADK_EXPERIMENTAL_CONFIG_SCHEMA_PATH") or os.path.join(
            os.path.dirname(__file__), "experimental_config_schema.yaml"
        )

        with open(schema_path, encoding="utf-8") as schema_file:
            openapi_schema = utils.load_yaml(schema_file.read())

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
