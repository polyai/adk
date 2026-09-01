"""Handling and managing an Agent Studio Flows

Copyright PolyAI Limited
"""

import logging
import math
import os
import re
import uuid
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from typing import Optional

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.flows_pb2 import (
    AdvancedStepCondition,
    ConditionDetails,
    CreateAdvancedStep,
    CreateFunctionStep,
    CreateFunctionStepDefinition,
    CreateNoCodeCondition,
    CreateNoCodeStep,
    CreateStep,
    DeleteNoCodeCondition,
    DeleteNoCodeStep,
    DeleteStep,
    ExitFlowCondition,
    Flow_CreateFlow,
    Flow_CreateStep,
    Flow_DeleteFlow,
    Flow_DeleteStep,
    Flow_UpdateFlow,
    Flow_UpdateStep,
    Flow_UpdateStepSettings,
    FlowASRConfig,
    FlowBargeInConfig,
    FlowLLMConfig,
    FlowStepSettings,
    FlowVADConfig,
    FunctionStepCondition,
    NoCodeStepCondition,
    StepAsrConfig,
    StepDtmfConfig,
    StepPosition,
    UpdateAdvancedStep,
    UpdateFunctionStep,
    UpdateFunctionStepDefinition,
    UpdateNoCodeCondition,
    UpdateNoCodeStep,
    UpdateStep,
)
from poly.resources.entities import Entity
from poly.resources.function import Function, FunctionType, parse_latency_control
from poly.resources.resource import (
    ResourceMapping,
    SubResource,
    YamlResource,
    register_resource,
)

logger = logging.getLogger(__name__)


FUNCTION_REGEX = re.compile(r"{{f[nt]:([\w-]+)}}")
# Flow step names: alphanumeric, extended Latin (C0–024F, 1E00–1EFF), and _ &,/.-
FLOW_STEP_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9\u00C0-\u024F\u1E00-\u1EFF_ &,/.\-]+$")
FLOW_REFERENCES = [
    "global_functions",
    "sms",
    "handoff",
    "attributes",
    "transition_functions",
    "entities",
    "variables",
]
NO_CODE_STEP_REFERENCES = [
    "attributes",
    "entities",
    "variables",
]


@register_resource("flow_config")
@dataclass
class FlowConfig(YamlResource):
    """Flow configuration resource."""

    description: str = field(default="")
    start_step: str = field(default="")

    # For creating:
    functions: list[Function] = field(default_factory=list, repr=False, init=False)
    steps: list["FlowStep"] = field(default_factory=list, repr=False, init=False)

    @cached_property
    def file_path(self) -> str:
        """File path for the resource."""
        return os.path.join("flows", utils.clean_name(self.name), "flow_config.yaml")

    def to_yaml_dict(self) -> dict:
        """Return a dictionary suitable for YAML serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "start_step": self.start_step,
        }

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "FlowConfig"]:
        """Parse flow configs from a projection dict."""
        configs = {}
        flows = projection.get("flows", {}).get("flows", {}).get("entities", {})
        if "flows" not in projection or any("startStepId" not in flow for flow in flows.values()):
            logger.debug("No read access to flows - they will not be pulled.")
            return {}

        for flow_id, flow_data in flows.items():
            configs[flow_id] = cls(
                resource_id=flow_id,
                name=flow_data["name"],
                description=flow_data.get("description", ""),
                start_step=flow_data.get("startStepId", ""),
            )
        return configs

    @classmethod
    def from_yaml_dict(cls, yaml_data: dict, resource_id: str, name: str, **kwargs) -> "FlowConfig":
        """Create an instance from YAML data and identity fields."""
        return cls(
            resource_id=resource_id,
            name=yaml_data.get("name", ""),
            description=(yaml_data.get("description") or "").strip(),
            start_step=yaml_data.get("start_step", ""),
        )

    @classmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "FlowConfig":
        """Read a local YAML resource from the given file path."""
        flow_config: FlowConfig = super().read_local_resource(
            file_path, resource_id=resource_id, resource_name=resource_name, **kwargs
        )

        # Just check flow folder name (one level up from file) matches flow name
        file_path_part_flow_folder = utils.get_flow_name_from_path(file_path)
        expected_flow_folder = utils.clean_name(flow_config.name)

        if file_path_part_flow_folder != expected_flow_folder:
            raise ValueError(
                f"Flow folder name does not match flow name in config. {file_path_part_flow_folder} != {expected_flow_folder}"
            )
        return flow_config

    @staticmethod
    def to_pretty_dict(
        d: dict,
        resource_name: str = None,
        resource_mappings: list[ResourceMapping] = None,
        **kwargs,
    ) -> dict:
        """Return dict with start_step ID replaced by name."""
        d = d.copy()
        start_step_id = d.get("start_step")
        if start_step_id:
            for resource in resource_mappings or []:
                if (
                    issubclass(resource.resource_type, BaseFlowStep)
                    and resource_name == resource.flow_name
                    and resource.resource_id.removeprefix(resource.flow_id + "_") == start_step_id
                ):
                    d["start_step"] = resource.resource_name
                    break
        return d

    @classmethod
    def from_pretty_dict(
        cls,
        yaml_dict: dict,
        resource_mappings: list[ResourceMapping] = None,
        resource_name: str = None,
        **kwargs,
    ) -> dict:
        """Replace start_step name with ID in a parsed YAML dict."""
        yaml_dict = super().from_pretty_dict(
            yaml_dict, resource_mappings=resource_mappings, resource_name=resource_name, **kwargs
        )
        start_step_name = yaml_dict.get("start_step")
        if start_step_name:
            for resource in resource_mappings or []:
                if (
                    issubclass(resource.resource_type, BaseFlowStep)
                    and resource.flow_name == resource_name
                    and resource.resource_name == start_step_name
                ):
                    yaml_dict["start_step"] = resource.resource_id.removeprefix(
                        resource.flow_id + "_"
                    )
                    break
        return yaml_dict

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs):
        """Validate the flow config resource."""
        if not self.start_step:
            raise ValueError("Start step cannot be empty.")

        # Check flow step exists in resource mappings
        found_step = False
        expected_step_resource_id = f"{self.resource_id}_{self.start_step}"
        for resource in resource_mappings or []:
            if (
                issubclass(resource.resource_type, BaseFlowStep)
                and resource.flow_name == self.name
                and resource.resource_id == expected_step_resource_id
            ):
                found_step = True
                break

        if not found_step:
            raise ValueError(f"Start step '{self.start_step}' not found.")

        # Check description exists
        if not self.description:
            raise ValueError("Description cannot be empty.")

        if self.description != self.description.strip():
            raise ValueError("Description cannot contain leading or trailing whitespace.")

    def build_update_proto(
        self,
    ) -> Flow_UpdateFlow:
        """Create a proto for updating the resource."""
        return Flow_UpdateFlow(
            flow_id=self.resource_id,
            name=self.name,
            description=self.description,
            start_step_id=self.start_step,
        )

    def build_delete_proto(self):
        """Create a proto for deleting the resource."""
        return Flow_DeleteFlow(flow_id=self.resource_id)

    def build_create_proto(self):
        """Create a proto for creating the resource."""
        functions = self.functions or []
        all_steps = self.steps or []

        transition_functions = [
            function.build_create_proto().transition_function for function in functions
        ]

        steps = [step.build_create_proto() for step in all_steps]

        return Flow_CreateFlow(
            id=self.resource_id,
            name=self.name,
            description=self.description,
            start_step_id=self.start_step,
            transition_functions=transition_functions,
            no_code_steps=[step for step in steps if isinstance(step, CreateNoCodeStep)],
            steps=[step.step for step in steps if isinstance(step, Flow_CreateStep)],
        )

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        return "flow"

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover resources of this type in the given base path.

        Args:
            base_path (str): The base path to search for resources.

        Returns:
            list[str]: A list of file paths of discovered resources.
        """
        flows_path = os.path.join(base_path, "flows")
        discovered_flow_configs = []
        if not os.path.exists(flows_path):
            return discovered_flow_configs

        # Find all the flow configs that match the pattern flows/<flow_name_formatted>/flow_config.yaml
        for flow_name_formatted in os.listdir(flows_path):
            flow_folder_path = os.path.join(flows_path, flow_name_formatted)

            # Skip if not a directory (e.g., files in flows/)
            if not os.path.isdir(flow_folder_path):
                continue

            for flow_config_path in os.listdir(flow_folder_path):
                if flow_config_path == "flow_config.yaml":
                    discovered_flow_configs.append(
                        os.path.join(flows_path, flow_name_formatted, flow_config_path)
                    )

        return discovered_flow_configs


class StepType(str, Enum):
    """Enum for step types."""

    ADVANCED_STEP = "advanced_step"
    DEFAULT_STEP = "default_step"
    FUNCTION_STEP = "function_step"


@dataclass
class BaseFlowStep(ABC):
    # Store step_id as not unique across flows
    step_id: str
    flow_id: str
    flow_name: str
    step_type: StepType
    position: dict[str, float]


@register_resource("flow_steps")
@dataclass
class FlowStep(BaseFlowStep, YamlResource):
    """Flow step resource."""

    conditions: Optional[list["Condition"]]
    extracted_entities: Optional[list[str]]
    settings: FlowSettings
    prompt: str

    def __init__(
        self,
        resource_id: str,
        name: str,
        step_id: str,
        flow_id: str,
        flow_name: str,
        step_type: "str | StepType",
        prompt: str,
        settings: Optional["FlowSettings | dict"] = None,
        conditions: Optional[list["Condition | dict"]] = None,
        extracted_entities: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
    ):
        self.resource_id = resource_id
        self.name = name
        self.step_id = step_id
        self.flow_id = flow_id
        self.flow_name = flow_name
        if not step_type:
            raise ValueError("step_type is required for FlowStep")
        self.step_type = StepType(step_type) if isinstance(step_type, str) else step_type

        if isinstance(settings, FlowSettings):
            self.settings = settings
        elif settings is not None:
            settings = {k: v for k, v in settings.items() if k not in ("resource_id", "name")}
            settings["step_id"] = self.step_id
            settings["flow_id"] = self.flow_id
            self.settings = FlowSettings(**settings)
        else:
            self.settings = FlowSettings(step_id=self.step_id, flow_id=self.flow_id)

        self.extracted_entities = extracted_entities or []
        self.conditions = [
            Condition(**condition) if not isinstance(condition, Condition) else condition
            for condition in (conditions or [])
        ]
        self.prompt = prompt
        self.position = position or {}

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "FlowStep"]:
        """Parse flow steps (non-function) from a projection dict."""
        steps = {}
        flows = projection.get("flows", {}).get("flows", {}).get("entities", {})
        if "flows" not in projection or any(
            "type" not in step
            for flow_data in flows.values()
            for step in flow_data.get("steps", {}).get("entities", {}).values()
        ):
            logger.debug("No read access to flow steps - they will not be pulled.")
            return {}

        for flow_id, flow_data in flows.items():
            for step_id, step in flow_data.get("steps", {}).get("entities", {}).items():
                if step.get("type") == "function_step":
                    continue

                local_resource_id = f"{flow_id}_{step_id}"
                settings = FlowSettings.from_projection(step, step_id, flow_id)

                references = step.get("references", {})
                extracted_entities = list(references.get("extractedEntities", {}).keys())

                steps[local_resource_id] = cls(
                    resource_id=local_resource_id,
                    step_id=step_id,
                    name=step["name"],
                    flow_id=flow_id,
                    flow_name=flow_data["name"],
                    step_type=step.get("type"),
                    settings=settings,
                    prompt=step.get("prompt", ""),
                    conditions=[
                        Condition(
                            resource_id=condition_data["id"],
                            name=condition_data["config"]["value"]["details"]["label"],
                            condition_type=condition_data["config"]["$case"],
                            description=condition_data["config"]["value"]["details"].get(
                                "description", ""
                            ),
                            required_entities=condition_data["config"]["value"]["details"].get(
                                "requiredEntities", []
                            ),
                            child_step=condition_data["config"]["value"].get("childStepId", ""),
                            step_id=step_id,
                            flow_id=flow_id,
                            ingress=condition_data["config"]["value"]["details"].get(
                                "ingressPosition", "top"
                            ),
                            position=condition_data["config"]["value"]["details"].get(
                                "position", {"x": 0.0, "y": 0.0}
                            ),
                            exit_flow_position=condition_data["config"]["value"].get(
                                "exitFlowPosition", None
                            ),
                        )
                        for condition_data in step.get("conditions", [])
                    ],
                    position=step.get("position"),
                    extracted_entities=extracted_entities,
                )
        return steps

    def to_yaml_dict(self) -> dict:
        """Return a dictionary suitable for YAML serialization."""
        output = {
            "step_type": self.step_type.value,
            "name": self.name,
        }
        flow_settings_dict = self.settings.to_yaml_dict() if self.settings else {}
        if flow_settings_dict:
            output.update(flow_settings_dict)

        if self.step_type == StepType.DEFAULT_STEP:
            output["conditions"] = [
                condition.to_yaml_dict()
                for condition in sorted(self.conditions, key=lambda condition: condition.name)
            ]
            output["extracted_entities"] = sorted(self.extracted_entities)

        output["prompt"] = self.prompt
        return output

    @classmethod
    def from_yaml_dict(
        cls,
        yaml_dict: dict,
        resource_id: str,
        file_name: str,
        flow_id: str,
        flow_name: str,
        name: str = "",
        known_position: dict[str, float] = None,
        known_conditions: list["Condition"] = None,
        resource_mappings: list[ResourceMapping] = None,
        **kwargs,
    ) -> "YamlResource":
        """Create an instance from YAML data and identity fields."""
        # Map conditions by name
        known_conditions = known_conditions or []
        condition_name_map = {cond.name: cond for cond in known_conditions}

        step_id = resource_id.removeprefix(f"{flow_id}_")

        conditions = []
        for condition_yaml in yaml_dict.get("conditions", []):
            condition_name = condition_yaml.get("name")
            known_condition = condition_name_map.get(condition_name)

            # Find Child Step to infer condition type if needed
            child_step_type = None
            if child_step_id := condition_yaml.get("child_step"):
                for resource in resource_mappings or []:
                    if (
                        issubclass(resource.resource_type, BaseFlowStep)
                        and resource.flow_name == flow_name
                        and resource.resource_id.removeprefix(resource.flow_id + "_")
                        == child_step_id
                    ):
                        if issubclass(resource.resource_type, FunctionStep):
                            child_step_type = StepType.FUNCTION_STEP
                            break

                        child_step_contents = cls.read_to_raw(
                            resource.file_path,
                            resource_mappings=resource_mappings,
                            flow_name=flow_name,
                        )
                        child_step_yaml = utils.load_yaml(child_step_contents)
                        child_step_type = StepType(child_step_yaml.get("step_type"))
                        break

            conditions.append(
                Condition.from_yaml_dict(
                    condition_yaml,
                    flow_id=flow_id,
                    step_id=step_id,
                    resource_id=(
                        known_condition.resource_id
                        if known_condition
                        else f"CONDITION-{uuid.uuid4().hex[:8]}"
                    ),
                    position=known_condition.position if known_condition else None,
                    ingress=known_condition.ingress if known_condition else None,
                    exit_flow_position=known_condition.exit_flow_position
                    if known_condition
                    else None,
                    child_step_type=child_step_type,
                )
            )
            if known_condition:
                del condition_name_map[condition_name]

        yaml_name = yaml_dict.get("name")

        if file_name != utils.clean_name(yaml_name):
            raise ValueError(
                f"Step name {yaml_name} in file {file_name}.yaml does not match clean version of name expected: {utils.clean_name(yaml_name)}.yaml"
            )

        step_type = StepType(yaml_dict.get("step_type"))
        extracted_entities = yaml_dict.get("extracted_entities", [])
        settings = FlowSettings.from_yaml_dict(yaml_dict, step_id=step_id, flow_id=flow_id)
        if step_type == StepType.ADVANCED_STEP:
            # Conditions not applicable
            conditions = []

        return cls(
            resource_id=resource_id,
            step_id=step_id,
            name=yaml_dict.get("name"),
            flow_id=flow_id,
            flow_name=flow_name,
            step_type=step_type,
            settings=settings,
            prompt=yaml_dict.get("prompt", "").strip(),
            conditions=conditions,
            position=known_position,
            extracted_entities=extracted_entities,
        )

    @staticmethod
    def to_pretty_dict(
        d: dict,
        file_path: str = None,
        resource_mappings: list[ResourceMapping] = None,
        **kwargs,
    ) -> dict:
        """Return dict with resource IDs replaced by names."""
        d = d.copy()
        flow_folder_name = utils.get_flow_name_from_path(file_path)

        if not flow_folder_name:
            raise ValueError(
                f"Flow folder name could not be determined from file_path: {file_path}"
            )

        if prompt := d.get("prompt"):
            d["prompt"] = utils.replace_resource_ids_with_names(
                prompt, resource_mappings or [], flow_folder_name=flow_folder_name
            )

        entity_mappings = {
            resource.resource_id: resource.resource_name
            for resource in resource_mappings or []
            if resource.resource_type == Entity
        }

        if extracted_entities := d.get("extracted_entities"):
            d["extracted_entities"] = [
                entity_mappings.get(entity_id, entity_id) for entity_id in extracted_entities
            ]

        if conditions := d.get("conditions"):
            for condition in conditions:
                if child_step_id := condition.get("child_step"):
                    for resource in resource_mappings or []:
                        if (
                            issubclass(resource.resource_type, BaseFlowStep)
                            and flow_folder_name
                            in os.path.normpath(resource.file_path).split(os.sep)
                            and resource.resource_id.removeprefix(resource.flow_id + "_")
                            == child_step_id
                        ):
                            condition["child_step"] = resource.resource_name
                            break

                if required_entities := condition.get("required_entities"):
                    condition["required_entities"] = [
                        entity_mappings.get(entity_id, entity_id) for entity_id in required_entities
                    ]
        return d

    @classmethod
    def from_pretty_dict(
        cls,
        yaml_dict: dict,
        resource_mappings: list[ResourceMapping] = None,
        file_path: str = None,
        **kwargs,
    ) -> dict:
        """Replace resource names with IDs in a parsed YAML dict."""
        flow_folder_name = utils.get_flow_name_from_path(file_path)

        if not flow_folder_name:
            raise ValueError("flow_name could not be determined from file_path")

        if prompt := yaml_dict.get("prompt"):
            yaml_dict["prompt"] = utils.replace_resource_names_with_ids(
                prompt, resource_mappings or [], flow_folder_name=flow_folder_name
            )

        entity_mappings = {
            resource.resource_name: resource.resource_id
            for resource in resource_mappings or []
            if resource.resource_type == Entity
        }

        if extracted_entities := yaml_dict.get("extracted_entities"):
            new_requested_entities = [
                entity_mappings.get(entity_name, entity_name) for entity_name in extracted_entities
            ]
            yaml_dict["extracted_entities"] = new_requested_entities

        # Replace child name with ID if step from same flow
        if conditions := yaml_dict.get("conditions"):
            for condition in conditions:
                if child_step_name := condition.get("child_step"):
                    for resource in resource_mappings or []:
                        if (
                            issubclass(resource.resource_type, BaseFlowStep)
                            and flow_folder_name
                            in os.path.normpath(resource.file_path).split(os.sep)
                            and resource.resource_name == child_step_name
                        ):
                            condition["child_step"] = resource.resource_id.removeprefix(
                                resource.flow_id + "_"
                            )
                            break

                if required_entities := condition.get("required_entities"):
                    new_required_entities = [
                        entity_mappings.get(entity_name, entity_name)
                        for entity_name in required_entities
                    ]
                    condition["required_entities"] = new_required_entities

        return yaml_dict

    @classmethod
    def from_pretty(
        cls, contents: str, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> str:
        """Replace resource names with resource IDs in the provided contents."""
        try:
            yaml_dict = utils.load_yaml(contents) or {}
        except Exception as e:
            raise ValueError("Error loading YAML content") from e
        yaml_dict = cls.from_pretty_dict(yaml_dict, resource_mappings=resource_mappings, **kwargs)
        return utils.dump_yaml(yaml_dict)

    @cached_property
    def file_path(self) -> str:
        """File path for the resource."""
        return os.path.join(
            "flows",
            utils.clean_name(self.flow_name),
            "steps",
            f"{utils.clean_name(self.name)}.yaml",
        )

    @classmethod
    def read_local_resource(
        cls,
        file_path: str,
        resource_id: str,
        resource_name: str,
        resource_mappings: list[ResourceMapping],
        known_conditions: list["Condition"] = None,
        known_position: dict[str, float] = None,
        **kwargs,
    ) -> "YamlResource":
        """Read a local YAML resource from the given file path."""
        flow_folder_name = utils.get_flow_name_from_path(file_path)

        # Extract flow_id from resource mappings
        flow_id, flow_name = utils.get_flow_id_from_flow_name(flow_folder_name, resource_mappings)

        # A step whose flow config is missing or unreadable resolves to no flow. Fall back
        # to the folder as read from disk so file_path stays usable -- discovery reads a
        # step before the flow mappings exist, and validate() reports the missing flow.
        flow_name = flow_name or flow_folder_name

        contents = cls.read_from_file(file_path)
        try:
            yaml_dict = utils.load_yaml(contents) or {}
        except Exception as e:
            raise ValueError(f"Error loading YAML file: {file_path}") from e

        yaml_dict = cls.from_pretty_dict(
            yaml_dict, resource_mappings=resource_mappings, file_path=file_path
        )

        # Get file name from file_path
        file_name = os.path.splitext(os.path.basename(file_path))[0]

        instance = cls.from_yaml_dict(
            yaml_dict,
            resource_id=resource_id,
            file_name=file_name,
            flow_id=flow_id,
            flow_name=flow_name,
            known_conditions=known_conditions,
            known_position=known_position,
            resource_mappings=resource_mappings,
        )
        utils.check_yaml_field_types(instance)
        return instance

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs):
        """Validate the flow step resource."""
        if not self.name:
            raise ValueError("Name cannot be empty.")

        if not FLOW_STEP_NAME_PATTERN.fullmatch(self.name):
            raise ValueError(
                "Name must contain only letters (including accented), numbers, and _ & , / . -"
            )

        if self.prompt is None or not self.prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        # Check flow config exists in resource mappings
        found_flow = False

        if not self.flow_id:
            raise ValueError("Flow ID cannot be empty.")

        for resource in resource_mappings or []:
            if resource.resource_type == FlowConfig and resource.resource_id == self.flow_id:
                found_flow = True
                break

        if not found_flow:
            raise ValueError("Flow config not found.")

        if self.step_type not in StepType:
            raise ValueError(
                f"Invalid step type: {self.step_type}. Valid types: {[t.value for t in StepType]}"
            )

        references = utils.get_references_from_prompt(
            self.prompt, FLOW_REFERENCES, raise_on_invalid=True
        )

        if self.step_type == StepType.DEFAULT_STEP and (
            references.get("global_functions") or references.get("transition_functions")
        ):
            function_references = []
            if references.get("global_functions"):
                function_references.extend(references.get("global_functions").keys())
            if references.get("transition_functions"):
                function_references.extend(references.get("transition_functions").keys())
            raise ValueError(
                f"Default steps cannot reference functions. "
                f"Found function references: {function_references}"
            )

        valid, invalid_references = utils.validate_references(
            references, resource_mappings, flow_name=self.flow_name
        )
        if not valid:
            raise ValueError(f"Invalid references: {invalid_references}")

        for condition in self.conditions:
            try:
                condition.validate(resource_mappings=resource_mappings)
            except Exception as e:
                raise ValueError(f"Condition '{condition.name}': {e}") from e

        entity_ids = set(
            resource.resource_id
            for resource in resource_mappings or []
            if resource.resource_type == Entity
        )
        if self.extracted_entities:
            for entity_id in self.extracted_entities:
                if entity_id not in entity_ids:
                    raise ValueError(f"Requested entity '{entity_id}' not found.")

        self.settings.validate()

    def build_update_proto(
        self,
    ) -> Flow_UpdateStep | UpdateNoCodeStep:
        """Create a proto for updating the resource."""
        if self.step_type == StepType.ADVANCED_STEP:
            references = utils.get_references_from_prompt(self.prompt, FLOW_REFERENCES)
            return Flow_UpdateStep(
                flow_id=self.flow_id,
                step=UpdateAdvancedStep(
                    id=self.step_id,
                    name=self.name,
                    prompt=self.prompt,
                    references=references,
                ),
            )

        if self.step_type == StepType.DEFAULT_STEP:
            references = utils.get_references_from_prompt(self.prompt, NO_CODE_STEP_REFERENCES)
            references["extracted_entities"] = {
                entity_name: True for entity_name in self.extracted_entities
            }
            return UpdateNoCodeStep(
                flow_id=self.flow_id,
                step_id=self.step_id,
                name=self.name,
                prompt=self.prompt,
                references=references,
            )

        raise NotImplementedError("Step type not implemented")

    def build_delete_proto(self) -> DeleteNoCodeStep | DeleteStep:
        """Create a proto for deleting the resource."""
        if self.step_type == StepType.ADVANCED_STEP:
            return Flow_DeleteStep(
                flow_id=self.flow_id,
                step_id=self.step_id,
            )

        if self.step_type == StepType.DEFAULT_STEP:
            return DeleteNoCodeStep(
                flow_id=self.flow_id,
                step_id=self.step_id,
            )

        raise NotImplementedError

    def build_create_proto(
        self,
    ) -> Flow_CreateStep | CreateNoCodeStep:
        """Create a proto for creating the resource."""
        if self.step_type == StepType.ADVANCED_STEP:
            references = utils.get_references_from_prompt(self.prompt, FLOW_REFERENCES)
            return Flow_CreateStep(
                flow_id=self.flow_id,
                step=CreateAdvancedStep(
                    id=self.step_id,
                    name=self.name,
                    prompt=self.prompt,
                    references=references,
                    position=StepPosition(
                        x=self.position.get("x", 0.0), y=self.position.get("y", 0.0)
                    ),
                ),
            )

        if self.step_type == StepType.DEFAULT_STEP:
            references = utils.get_references_from_prompt(self.prompt, NO_CODE_STEP_REFERENCES)
            references["extracted_entities"] = {
                entity_name: True for entity_name in self.extracted_entities
            }
            return CreateNoCodeStep(
                flow_id=self.flow_id,
                step_id=self.step_id,
                name=self.name,
                prompt=self.prompt,
                position=StepPosition(x=self.position.get("x", 0.0), y=self.position.get("y", 0.0)),
                references=references,
            )

        raise NotImplementedError("Step type not implemented")

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        if self.step_type == StepType.ADVANCED_STEP:
            return "flow_step"
        if self.step_type == StepType.DEFAULT_STEP:
            return "no_code_step"

        raise NotImplementedError("Step type not implemented")

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover resources of this type in the given base path.

        Args:
            base_path (str): The base path to search for resources.

        Returns:
            list[str]: A list of file paths of discovered resources.
        """
        flows_path = os.path.join(base_path, "flows")
        discovered_flow_steps = []

        if not os.path.exists(flows_path):
            return discovered_flow_steps

        # Find all the flow steps that match the pattern flows/<flow_name>/steps/<step_name>.yaml
        for flow_name in os.listdir(flows_path):
            steps_path = os.path.join(flows_path, flow_name, "steps")
            if os.path.exists(steps_path):
                for file_name in os.listdir(steps_path):
                    if file_name.endswith(".yaml"):
                        discovered_flow_steps.append(os.path.join(steps_path, file_name))

        return discovered_flow_steps

    def get_new_updated_deleted_subresources(
        self, old_resource: Optional["FlowStep"] = None
    ) -> tuple[list[SubResource], list[SubResource], list[SubResource]]:
        """Get the new, updated, and deleted subresources within this resource.

        Returns:
            tuple[
                list[SubResource],
                list[SubResource],
                list[SubResource],
            ]: A tuple containing three lists of subresources:
                - New subresources
                - Updated subresources
                - Deleted subresources
        """
        new = []
        updated = []
        deleted = []

        old_settings = (
            old_resource.settings
            if old_resource
            else FlowSettings(step_id=self.step_id, flow_id=self.flow_id)
        )
        if self.settings != old_settings:
            updated.append(self.settings)

        if self.step_type == StepType.DEFAULT_STEP:
            old_condition_ids = (
                {cond.resource_id for cond in old_resource.conditions} if old_resource else set()
            )
            new_condition_ids = {cond.resource_id for cond in self.conditions}

            for condition in self.conditions:
                if condition.resource_id not in old_condition_ids:
                    new.append(condition)
                else:
                    # Check if updated
                    old_condition = next(
                        (
                            c
                            for c in old_resource.conditions
                            if c.resource_id == condition.resource_id
                        ),
                        None,
                    )
                    if old_condition and condition != old_condition:
                        updated.append(condition)

            if old_resource:
                for condition in old_resource.conditions:
                    if condition.resource_id not in new_condition_ids:
                        deleted.append(condition)

        return new, updated, deleted


@dataclass
class ASRBiasing:
    """ASR Biasing configuration."""

    alphanumeric: bool
    name_spelling: bool
    numeric: bool
    party_size: bool
    precise_date: bool
    relative_date: bool
    single_number: bool
    time: bool
    yes_no: bool
    address: bool
    custom_keywords: list[str]
    is_enabled: bool

    def __init__(
        self,
        alphanumeric: bool = False,
        name_spelling: bool = False,
        numeric: bool = False,
        party_size: bool = False,
        precise_date: bool = False,
        relative_date: bool = False,
        single_number: bool = False,
        time: bool = False,
        yes_no: bool = False,
        address: bool = False,
        custom_keywords: list[str] | None = None,
        is_enabled: bool = False,
    ):
        self.alphanumeric = alphanumeric
        self.name_spelling = name_spelling
        self.numeric = numeric
        self.party_size = party_size
        self.precise_date = precise_date
        self.relative_date = relative_date
        self.single_number = single_number
        self.time = time
        self.yes_no = yes_no
        self.address = address
        self.custom_keywords = custom_keywords or []
        self.is_enabled = is_enabled

    def to_yaml_dict(self) -> dict:
        """Return a dictionary suitable for YAML serialization."""
        return {
            "is_enabled": self.is_enabled,
            "alphanumeric": self.alphanumeric,
            "name_spelling": self.name_spelling,
            "numeric": self.numeric,
            "party_size": self.party_size,
            "precise_date": self.precise_date,
            "relative_date": self.relative_date,
            "single_number": self.single_number,
            "time": self.time,
            "yes_no": self.yes_no,
            "address": self.address,
            "custom_keywords": self.custom_keywords,
        }

    def validate(self):
        """Validate the ASR configuration."""
        pass

    def to_proto(self) -> StepAsrConfig:
        """Convert to proto representation."""
        return StepAsrConfig(
            is_enabled=self.is_enabled,
            alphanumeric=self.alphanumeric,
            name_spelling=self.name_spelling,
            numeric=self.numeric,
            party_size=self.party_size,
            precise_date=self.precise_date,
            relative_date=self.relative_date,
            single_number=self.single_number,
            time=self.time,
            yes_no=self.yes_no,
            address=self.address,
            custom_keywords=self.custom_keywords,
        )


@dataclass
class DTMFConfig:
    """DTMF Configuration."""

    is_enabled: bool
    inter_digit_timeout: int
    max_digits: int
    end_key: str
    collect_while_agent_speaking: bool
    is_pii: bool

    def __init__(
        self,
        step_id: str,
        flow_id: str,
        is_enabled: bool = False,
        inter_digit_timeout: int = 0,
        max_digits: int = 0,
        end_key: str = "#",
        collect_while_agent_speaking: bool = False,
        is_pii: bool = False,
    ):
        self.name = "dtmf"
        self.step_id = step_id
        self.flow_id = flow_id
        self.resource_id = f"{flow_id}.{step_id}"
        self.is_enabled = is_enabled
        self.inter_digit_timeout = inter_digit_timeout
        self.max_digits = max_digits
        self.end_key = end_key
        self.collect_while_agent_speaking = collect_while_agent_speaking
        self.is_pii = is_pii

    def to_yaml_dict(self) -> dict:
        """Return a dictionary suitable for YAML serialization."""
        return {
            "is_enabled": self.is_enabled,
            "inter_digit_timeout": self.inter_digit_timeout,
            "max_digits": self.max_digits,
            "end_key": self.end_key,
            "collect_while_agent_speaking": self.collect_while_agent_speaking,
            "is_pii": self.is_pii,
        }

    def validate(self):
        """Validate the DTMF configuration."""
        for name in ("inter_digit_timeout", "max_digits"):
            if getattr(self, name) < 0:
                raise ValueError(f"DTMF {name} cannot be negative.")

    def to_proto(self) -> StepDtmfConfig:
        """Convert to proto representation."""
        return StepDtmfConfig(
            is_enabled=self.is_enabled,
            inter_digit_timeout=self.inter_digit_timeout,
            max_digits=self.max_digits,
            end_key=self.end_key,
            collect_while_agent_speaking=self.collect_while_agent_speaking,
            is_pii=self.is_pii,
        )


def _drop_unset(values: dict) -> dict:
    """Drop keys whose override was never set, so they don't surface as nulls in YAML."""
    return {key: value for key, value in values.items() if value is not None}


@dataclass
class ASRConfig:
    """ASR Configuration."""

    # Every field is an optional override, so a step may set only some of them.
    provider: Optional[str] = None
    model: Optional[str] = None

    def validate(self):
        """Validate the ASR configuration."""
        pass

    def to_yaml_dict(self) -> dict:
        """Return a dictionary suitable for YAML serialization."""
        return _drop_unset({"provider": self.provider, "model": self.model})

    def to_proto(self) -> FlowASRConfig:
        """Convert to proto representation."""
        return FlowASRConfig(provider=self.provider, model=self.model)


@dataclass
class VADConfig:
    """VAD Configuration."""

    # Every field is an optional override, so a step may set only some of them.
    provider: Optional[str] = None
    vad_start: Optional[float] = None
    vad_end: Optional[float] = None
    speech_threshold: Optional[float] = None
    silence_threshold: Optional[float] = None

    def validate(self):
        """Validate the VAD configuration."""
        for name in ("vad_start", "vad_end"):
            value = getattr(self, name)
            if value is None:
                continue
            if not math.isfinite(value):
                raise ValueError(f"VAD {name} must be a finite number.")
            if value < 0:
                raise ValueError(f"VAD {name} cannot be negative.")

    def to_yaml_dict(self) -> dict:
        """Return a dictionary suitable for YAML serialization."""
        return _drop_unset(
            {
                "provider": self.provider,
                "vad_start": self.vad_start,
                "vad_end": self.vad_end,
                "speech_threshold": self.speech_threshold,
                "silence_threshold": self.silence_threshold,
            }
        )

    def to_proto(self) -> FlowVADConfig:
        """Convert to proto representation."""
        return FlowVADConfig(
            provider=self.provider,
            vad_start=self.vad_start,
            vad_end=self.vad_end,
            speech_threshold=self.speech_threshold,
            silence_threshold=self.silence_threshold,
        )


@dataclass
class BargeInConfig:
    is_enabled: bool

    def validate(self):
        """Validate the BargeIn configuration."""
        pass

    def to_yaml_dict(self) -> dict:
        """Return a dictionary suitable for YAML serialization."""
        return {"is_enabled": self.is_enabled}

    def to_proto(self) -> FlowBargeInConfig:
        """Convert to proto representation."""
        return FlowBargeInConfig(is_enabled=self.is_enabled)


class ReasoningEffort(str, Enum):
    """Enum for reasoning effort levels."""

    UNSPECIFIED = "unspecified"
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    AUTO = "auto"


# Ordinal mapping for the proto ReasoningEffort enum, which projections send as a raw int
# rather than the string values used in YAML.
REASONING_EFFORT_FROM_PROTO_INT = {
    0: ReasoningEffort.UNSPECIFIED,
    1: ReasoningEffort.MINIMAL,
    2: ReasoningEffort.LOW,
    3: ReasoningEffort.MEDIUM,
    4: ReasoningEffort.HIGH,
    5: ReasoningEffort.AUTO,
}

REASONING_EFFORT_TO_PROTO_INT = {v: k for k, v in REASONING_EFFORT_FROM_PROTO_INT.items()}


def parse_reasoning_effort(value: "int | str | ReasoningEffort") -> ReasoningEffort:
    """Parse a reasoning effort from a projection ordinal or a YAML string."""
    if isinstance(value, ReasoningEffort):
        return value

    if isinstance(value, int) and not isinstance(value, bool):
        # Projections send the proto enum's ordinal rather than its string value.
        if value not in REASONING_EFFORT_FROM_PROTO_INT:
            raise ValueError(
                f"Unknown reasoning effort '{value}'. This project may use a newer "
                "Agent Studio feature - try upgrading polyai-adk."
            )
        return REASONING_EFFORT_FROM_PROTO_INT[value]

    try:
        return ReasoningEffort(value)
    except ValueError:
        valid = ", ".join(effort.value for effort in ReasoningEffort)
        raise ValueError(f"Invalid reasoning_effort '{value}'. Valid values: {valid}.") from None


@dataclass
class LLMConfig:
    """LLM Configuration."""

    # Both fields are optional overrides, so a step may set only one of them.
    provider_model_id: Optional[str] = None
    reasoning_effort: ReasoningEffort = ReasoningEffort.UNSPECIFIED

    def validate(self):
        """Validate the LLM configuration."""
        pass

    def to_yaml_dict(self) -> dict:
        """Return a dictionary suitable for YAML serialization."""
        return _drop_unset(
            {
                "provider_model_id": self.provider_model_id,
                "reasoning_effort": self.reasoning_effort.value,
            }
        )

    def to_proto(self) -> FlowLLMConfig:
        """Convert to proto representation."""
        return FlowLLMConfig(
            provider_model_id=self.provider_model_id,
            reasoning_effort=REASONING_EFFORT_TO_PROTO_INT[self.reasoning_effort],
        )


@dataclass
class FlowSettings(SubResource):
    """Flow settings resource"""

    step_id: str
    flow_id: str

    asr_biasing: Optional[ASRBiasing]
    dtmf: Optional[DTMFConfig]
    asr: Optional[ASRConfig]
    vad: Optional[VADConfig]
    barge_in: Optional[BargeInConfig]
    llm: Optional[LLMConfig]

    def __init__(
        self,
        asr_biasing: Optional[ASRBiasing] = None,
        dtmf: Optional[DTMFConfig] = None,
        asr: Optional[ASRConfig] = None,
        vad: Optional[VADConfig] = None,
        barge_in: Optional[BargeInConfig] = None,
        llm: Optional[LLMConfig] = None,
        step_id: str = "",
        flow_id: str = "",
    ):
        self.name = "FlowSettings"
        self.resource_id = f"{flow_id}_{step_id}_settings"
        self.step_id = step_id
        self.flow_id = flow_id

        if isinstance(asr_biasing, dict):
            asr_biasing = ASRBiasing(**asr_biasing)
        if isinstance(dtmf, dict):
            dtmf = DTMFConfig(step_id, flow_id, **dtmf)
        if isinstance(asr, dict):
            asr = ASRConfig(**asr)
        if isinstance(vad, dict):
            vad = VADConfig(**vad)
        if isinstance(barge_in, dict):
            barge_in = BargeInConfig(**barge_in)
        if isinstance(llm, dict):
            llm = dict(llm)
            llm["reasoning_effort"] = parse_reasoning_effort(
                llm.get("reasoning_effort", ReasoningEffort.UNSPECIFIED)
            )
            llm = LLMConfig(**llm)

        self.asr_biasing = asr_biasing
        self.dtmf = dtmf
        self.asr = asr
        self.vad = vad
        self.barge_in = barge_in
        self.llm = llm

    def to_yaml_dict(self) -> dict:
        """Return a dictionary suitable for YAML serialization."""
        output = {}
        if self.asr_biasing and self.asr_biasing.is_enabled:
            output["asr_biasing"] = self.asr_biasing.to_yaml_dict()
        if self.dtmf and self.dtmf.is_enabled:
            output["dtmf_config"] = self.dtmf.to_yaml_dict()
        if self.asr:
            output["asr"] = self.asr.to_yaml_dict()
        if self.vad:
            output["vad"] = self.vad.to_yaml_dict()
        if self.barge_in:
            output["barge_in"] = self.barge_in.to_yaml_dict()
        if self.llm:
            output["llm"] = self.llm.to_yaml_dict()
        return output

    @classmethod
    def from_projection(cls, step: dict, step_id: str, flow_id: str) -> "FlowSettings":
        """Parse flow step settings from a projection step dict."""
        settings_data = step.get("settings")
        if settings_data is None:
            # No settings block means this step predates it entirely, so fall back to the
            # legacy top-level fields. The backend mirrors these onto every settings update
            # but never clears them, so once a settings block exists it must not be
            # overridden by legacy fields — an empty settings block means the user cleared
            # everything.
            settings_data = {}
            legacy_asr_biasing = step.get("asrBiasing", {})
            legacy_dtmf = step.get("dtmfConfig", {})
            if legacy_asr_biasing:
                settings_data["asr_biasing"] = legacy_asr_biasing
            if legacy_dtmf:
                settings_data["dtmf"] = legacy_dtmf
        else:
            settings_data = utils.convert_keys_to_snake_case(settings_data)

        asr_biasing_data = utils.convert_keys_to_snake_case(settings_data.get("asr_biasing") or {})
        dtmf_data = utils.convert_keys_to_snake_case(settings_data.get("dtmf") or {})
        asr_data = utils.convert_keys_to_snake_case(settings_data.get("asr") or {})
        vad_data = utils.convert_keys_to_snake_case(settings_data.get("vad") or {})
        barge_in_data = utils.convert_keys_to_snake_case(settings_data.get("barge_in") or {})
        llm_data = utils.convert_keys_to_snake_case(settings_data.get("llm") or {})

        return cls(
            step_id=step_id,
            flow_id=flow_id,
            asr_biasing=asr_biasing_data or None,
            dtmf=dtmf_data or None,
            asr=asr_data or None,
            vad=vad_data or None,
            barge_in=barge_in_data or None,
            llm=llm_data or None,
        )

    @classmethod
    def from_yaml_dict(cls, yaml_dict: dict, step_id: str, flow_id: str) -> "FlowSettings":
        """Create an instance from YAML data and identity fields."""
        asr_biasing_data: dict = yaml_dict.get("asr_biasing", {})
        dtmf_data: dict = yaml_dict.get("dtmf_config", {})
        asr_data: dict = yaml_dict.get("asr", {})
        vad_data: dict = yaml_dict.get("vad", {})
        barge_in_data: dict = yaml_dict.get("barge_in", {})
        llm_data: dict = yaml_dict.get("llm", {})

        return cls(
            step_id=step_id,
            flow_id=flow_id,
            asr_biasing=ASRBiasing(**asr_biasing_data) if asr_biasing_data else None,
            dtmf=DTMFConfig(step_id, flow_id, **dtmf_data) if dtmf_data else None,
            asr=ASRConfig(**asr_data) if asr_data else None,
            vad=VADConfig(**vad_data) if vad_data else None,
            barge_in=BargeInConfig(**barge_in_data) if barge_in_data else None,
            llm=llm_data or None,
        )

    def validate(self, **kwargs):
        """Validate the flow settings resource."""
        if self.asr_biasing:
            self.asr_biasing.validate()
        if self.dtmf:
            self.dtmf.validate()
        if self.asr:
            self.asr.validate()
        if self.vad:
            self.vad.validate()
        if self.barge_in:
            self.barge_in.validate()
        if self.llm:
            self.llm.validate()

    def build_update_proto(self) -> Flow_UpdateStepSettings:
        """Create a proto for updating the flow settings."""
        return Flow_UpdateStepSettings(
            flow_id=self.flow_id,
            step_id=self.step_id,
            settings=FlowStepSettings(
                asr_biasing=self.asr_biasing.to_proto() if self.asr_biasing else None,
                dtmf=self.dtmf.to_proto() if self.dtmf else None,
                asr=self.asr.to_proto() if self.asr else None,
                vad=self.vad.to_proto() if self.vad else None,
                barge_in=self.barge_in.to_proto() if self.barge_in else None,
                llm=self.llm.to_proto() if self.llm else None,
            ),
        )

    def build_delete_proto(self):
        """Create a proto for deleting the flow settings."""
        raise NotImplementedError("Flow settings deletion is not supported.")

    def build_create_proto(self):
        """Create a proto for creating the flow settings."""
        raise NotImplementedError("Flow settings creation is not supported.")

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        return "flow_settings"

    @property
    def update_command_type(self) -> str:
        """Get the update type for updating the resource."""
        return "update_step_settings"


class ConditionType(str, Enum):
    """Enum for condition types."""

    EXIT_FLOW = "exit_flow_condition"
    STEP = "step_condition"
    NO_CODE_STEP = "no_code_step_condition"
    FUNCTION_STEP = "function_step_condition"


@dataclass
class Condition(SubResource):
    """Conditions for no code steps"""

    description: str
    required_entities: list[str]
    condition_type: ConditionType
    child_step: str
    position: dict
    exit_flow_position: dict
    ingress: str
    step_id: str
    flow_id: str

    def __init__(
        self,
        resource_id: str,
        name: str,
        condition_type: "str | ConditionType",
        step_id: str,
        flow_id: str,
        description: str = "",
        required_entities: list[str] | None = None,
        child_step: str = "",
        position: dict | None = None,
        ingress: str = "top",
        exit_flow_position: dict | None = None,
    ):
        self.resource_id = resource_id
        self.name = name
        self.description = description
        self.condition_type = (
            ConditionType(utils.to_snake_case(condition_type))
            if isinstance(condition_type, str)
            else condition_type
        )
        self.required_entities = required_entities or []
        self.child_step = child_step
        self.step_id = step_id
        self.flow_id = flow_id
        self.position = position or {}
        self.ingress = ingress
        self.exit_flow_position = exit_flow_position or {}

    def to_yaml_dict(self) -> dict:
        """Return a dictionary suitable for YAML serialization."""

        # Map ConditionType enum to YAML string
        if self.condition_type == ConditionType.EXIT_FLOW:
            condition_type = self.condition_type.value
        else:
            condition_type = "step_condition"

        yaml_dict = {
            "name": self.name,
            "condition_type": condition_type,
            "description": self.description,
        }

        if self.condition_type != ConditionType.EXIT_FLOW:
            yaml_dict["child_step"] = self.child_step

        yaml_dict["required_entities"] = self.required_entities

        return yaml_dict

    @classmethod
    def from_yaml_dict(
        cls,
        yaml_data: dict,
        resource_id: str,
        step_id: str,
        flow_id: str,
        position: dict,
        ingress: str,
        exit_flow_position: dict,
        child_step_type: Optional[StepType] = None,
    ) -> "Condition":
        """Create an instance from YAML data and identity fields."""
        if yaml_data.get("condition_type") == "step_condition":
            if child_step_type == StepType.DEFAULT_STEP:
                condition_type = ConditionType.NO_CODE_STEP
            elif child_step_type == StepType.FUNCTION_STEP:
                condition_type = ConditionType.FUNCTION_STEP
            else:
                condition_type = ConditionType.STEP
        else:
            condition_type = ConditionType.EXIT_FLOW

        return cls(
            resource_id=resource_id,
            step_id=step_id,
            flow_id=flow_id,
            position=position,
            ingress=ingress,
            exit_flow_position=exit_flow_position,
            name=yaml_data.get("name"),
            condition_type=condition_type,
            description=(yaml_data.get("description") or "").strip(),
            required_entities=yaml_data.get("required_entities", []),
            child_step=yaml_data.get("child_step", ""),
        )

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        return "no_code_condition"

    def build_update_proto(self) -> UpdateNoCodeCondition:
        """Create a proto for updating the condition."""
        return UpdateNoCodeCondition(
            flow_id=self.flow_id,
            step_id=self.step_id,
            condition_id=self.resource_id,
            **self._get_condition_type_proto(),
        )

    def build_delete_proto(self) -> DeleteNoCodeCondition:
        """Create a proto for deleting the condition."""
        return DeleteNoCodeCondition(
            flow_id=self.flow_id,
            step_id=self.step_id,
            condition_id=self.resource_id,
        )

    def build_create_proto(self) -> CreateNoCodeCondition:
        """Create a proto for creating the condition."""
        return CreateNoCodeCondition(
            flow_id=self.flow_id,
            step_id=self.step_id,
            condition_id=self.resource_id,
            **self._get_condition_type_proto(),
        )

    def _get_condition_type_proto(self) -> dict:
        """Get the condition type proto based on the condition type."""
        if self.condition_type == ConditionType.EXIT_FLOW:
            return {
                "exit_flow_condition": ExitFlowCondition(
                    details=ConditionDetails(
                        label=self.name,
                        description=self.description,
                        required_entities=self.required_entities,
                        position=self.position,
                        ingress_position=self.ingress or "top",
                    ),
                    exit_flow_position=self.exit_flow_position,
                )
            }
        elif self.condition_type == ConditionType.NO_CODE_STEP:
            return {
                "no_code_step_condition": NoCodeStepCondition(
                    details=ConditionDetails(
                        label=self.name,
                        description=self.description,
                        required_entities=self.required_entities,
                        position=self.position,
                        ingress_position=self.ingress or "top",
                    ),
                    child_step_id=self.child_step,
                )
            }
        elif self.condition_type == ConditionType.STEP:
            return {
                "step_condition": AdvancedStepCondition(
                    details=ConditionDetails(
                        label=self.name,
                        description=self.description,
                        required_entities=self.required_entities,
                        position=self.position,
                        ingress_position=self.ingress or "top",
                    ),
                    child_step_id=self.child_step,
                )
            }
        elif self.condition_type == ConditionType.FUNCTION_STEP:
            return {
                "function_step_condition": FunctionStepCondition(
                    details=ConditionDetails(
                        label=self.name,
                        description=self.description,
                        required_entities=self.required_entities,
                        position=self.position,
                        ingress_position=self.ingress or "top",
                    ),
                    child_step_id=self.child_step,
                )
            }
        else:
            raise NotImplementedError(f"Condition type {self.condition_type} not implemented.")

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs):
        """Validate the condition resource."""
        if not self.name:
            raise ValueError("Condition name cannot be empty.")

        if self.condition_type not in ConditionType:
            raise ValueError(f"Invalid condition type: {self.condition_type}")

        # Check child step exists in resource mappings
        # and also all required entities exist in resource mappings
        required_entity_ids = set(self.required_entities)
        if self.condition_type != ConditionType.EXIT_FLOW:
            found_step = False
        else:
            found_step = True
            # No child step to check for exit flow condition
        for resource in resource_mappings or []:
            if (
                not found_step
                and issubclass(resource.resource_type, BaseFlowStep)
                and resource.resource_id.removeprefix(resource.flow_id + "_") == self.child_step
            ):
                found_step = True

            if resource.resource_type == Entity and resource.resource_id in required_entity_ids:
                required_entity_ids.remove(resource.resource_id)

            if not required_entity_ids and found_step:
                break

        if not found_step:
            raise ValueError(f"Step '{self.child_step}' not found")

        if required_entity_ids:
            raise ValueError(f"Required entities not found: {required_entity_ids}")

        if self.description and self.description != self.description.strip():
            raise ValueError("Description cannot contain leading or trailing whitespace.")


@register_resource("function_steps")
@dataclass(init=False)
class FunctionStep(Function, BaseFlowStep):
    """Dataclass representing a function step"""

    function_id: str
    step_type: StepType = field(default=StepType.FUNCTION_STEP, init=False)
    function_type: FunctionType = field(default=FunctionType.FUNCTION_STEP, init=False)

    def __init__(
        self,
        resource_id: str,
        name: str,
        step_id: str,
        flow_id: str,
        flow_name: str,
        code: str,
        description: str = None,
        parameters: list = None,
        latency_control: dict = None,
        position: dict = None,
        function_id: str = None,
        variable_references: dict = None,
    ):
        self.step_id = step_id
        self.function_id = function_id
        self.step_type = StepType.FUNCTION_STEP
        self.position = position or {}
        super().__init__(
            resource_id=resource_id,
            name=name,
            description=None,
            code=code,
            parameters=parameters or [],
            latency_control=latency_control or {},
            flow_id=flow_id,
            flow_name=flow_name,
            function_type=FunctionType.FUNCTION_STEP,
            variable_references=variable_references,
        )

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "FunctionStep"]:
        """Parse function steps from a projection dict."""
        func_steps = {}
        flows = projection.get("flows", {}).get("flows", {}).get("entities", {})
        if "flows" not in projection or any(
            "type" not in step
            for flow_data in flows.values()
            for step in flow_data.get("steps", {}).get("entities", {}).values()
        ):
            logger.debug("No read access to flow steps - they will not be pulled.")
            return {}

        for flow_id, flow_data in flows.items():
            for step_id, step in flow_data.get("steps", {}).get("entities", {}).items():
                if step.get("type") != "function_step":
                    continue

                local_resource_id = f"{flow_id}_{step_id}"
                function = step.get("function", {})
                func_steps[local_resource_id] = cls(
                    resource_id=local_resource_id,
                    step_id=step_id,
                    flow_id=flow_id,
                    flow_name=flow_data["name"],
                    name=step["name"],
                    position=step.get("position"),
                    code=function.get("code", ""),
                    latency_control=parse_latency_control(
                        function.get("latencyControl", function.get("latency_control"))
                    ),
                    parameters=[],
                    function_id=function.get("id", ""),
                )
        return func_steps

    @cached_property
    def file_path(self) -> str:
        """File path for the resource."""
        file_name = f"{self.name}.py"
        flow_name = utils.clean_name(self.flow_name)
        return os.path.join("flows", flow_name, "function_steps", file_name)

    @property
    def raw(self) -> str:
        """Convert the resource to raw format."""
        return self._generate_raw_output(
            add_description=False, add_parameters=False, add_latency_control=True
        )

    def validate(self, **kwargs):
        """Validate the resource."""
        super().validate(**kwargs)

        if self.parameters:
            raise ValueError("Function steps cannot have parameters.")

    @classmethod
    def read_local_resource(
        cls,
        file_path: str,
        resource_id: str,
        resource_name: str,
        resource_mappings: list[ResourceMapping],
        known_latency_control: dict,
        known_function_id: str = None,
        known_position: dict[str, float] = None,
        **kwargs,
    ) -> "FunctionStep":
        code = cls.read_to_raw(
            file_path, resource_mappings=resource_mappings, resource_name=resource_name, **kwargs
        )

        # Parse known latency control and extract from code (e.g. @func_latency_control)
        known_lc = Function._parse_latency_control(
            known_latency_control if known_latency_control else {}
        )
        code, _parameters, _description, latency_control = Function._extract_decorators(
            code, resource_name, [], known_lc
        )

        # e.g. flows/{flow_name}/function_steps/{function_name}.py
        parts = os.path.normpath(file_path).split(os.sep)
        if len(parts) >= 4 and parts[-4] == "flows":
            flow_folder_name = parts[-3]
        else:
            flow_folder_name = None

        flow_id = None
        flow_name = None
        if flow_folder_name:
            flow_id, flow_name = utils.get_flow_id_from_flow_name(
                flow_folder_name, resource_mappings
            )

        # See FlowStep.read_local_resource: keep the folder as a fallback so file_path
        # stays usable when the flow config is missing.
        flow_name = flow_name or flow_folder_name

        step_id = resource_id.removeprefix(f"{flow_id}_")

        function_id = known_function_id or f"FUNCTION-{uuid.uuid4().hex[:8]}"

        # Read references from code
        variable_references = cls._extract_variable_references(code, resource_mappings)

        return FunctionStep(
            resource_id=resource_id,
            step_id=step_id,
            name=resource_name,
            flow_id=flow_id,
            flow_name=flow_name,
            position=known_position,
            code=code,
            latency_control=latency_control,
            parameters=[],
            function_id=function_id,
            variable_references=variable_references,
        )

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover resources of this type in the given base path.

        Args:
            base_path (str): The base path to search for resources.

        Returns:
            list[str]: A list of file paths of discovered resources.
        """
        discovered_function_steps: list[str] = []
        flows_path = os.path.join(base_path, "flows")
        if not os.path.exists(flows_path):
            return discovered_function_steps

        for flow_name in os.listdir(flows_path):
            function_steps_path = os.path.join(flows_path, flow_name, "function_steps")
            if not os.path.exists(function_steps_path):
                continue

            discovered_function_steps.extend(
                [
                    os.path.join(function_steps_path, file_name)
                    for file_name in os.listdir(function_steps_path)
                    if file_name.endswith(".py")
                ]
            )

        return discovered_function_steps

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        return "step"

    def build_update_proto(self) -> UpdateStep:
        """Create a proto for updating the resource."""
        return UpdateStep(
            flow_id=self.flow_id,
            step_id=self.step_id,
            function_step=UpdateFunctionStep(
                name=self.name,
                position=self.position,
                function=UpdateFunctionStepDefinition(
                    code=self.code,
                    latency_control=self._build_create_latency_control_proto(),
                ),
            ),
        )

    def build_delete_proto(self) -> DeleteStep:
        """Create a proto for deleting the resource."""
        return DeleteStep(
            flow_id=self.flow_id,
            step_id=self.step_id,
        )

    def build_create_proto(self) -> CreateStep:
        """Create a proto for creating the resource."""
        return CreateStep(
            flow_id=self.flow_id,
            function_step=CreateFunctionStep(
                id=self.step_id,
                name=self.name,
                position=self.position,
                function=CreateFunctionStepDefinition(
                    id=self.function_id,
                    name=self.name,
                    errors=[],
                    code=self.code,
                    latency_control=self._build_create_latency_control_proto(),
                ),
            ),
        )

    def get_new_updated_deleted_subresources(
        self, old_resource: Optional["FunctionStep"] = None
    ) -> tuple[list[SubResource], list[SubResource], list[SubResource]]:
        """LatencyControl is already included in the step update/create protos,
        so skip emitting it as a separate sub-resource command."""
        return [], [], []
