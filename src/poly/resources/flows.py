"""Handling and managing an Agent Studio Flows

Copyright PolyAI Limited
"""

import os
import re
import uuid
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from typing import ClassVar, Optional

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
    Flow_UpdateStepAsrConfig,
    Flow_UpdateStepDtmfConfig,
    FunctionStepCondition,
    NoCodeStepCondition,
    StepAsrConfig,
    StepAsrConfigUpdate,
    StepDtmfConfig,
    StepDtmfConfigUpdate,
    StepPosition,
    UpdateAdvancedStep,
    UpdateAsrKeywords,
    UpdateFunctionStep,
    UpdateFunctionStepDefinition,
    UpdateNoCodeCondition,
    UpdateNoCodeStep,
    UpdateStep,
)
from poly.resources.entities import Entity
from poly.resources.function import Function, FunctionType
from poly.resources.resource import (
    ResourceMapping,
    SubResource,
    YamlResource,
)

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


@dataclass
class FlowConfig(YamlResource):
    """Flow configuration resource."""

    projection_path: ClassVar[list[str]] = ["flows", "flows", "entities", "{id}"]
    projection_update_id_field: ClassVar[Optional[str]] = "flow_id"

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
                    and resource.resource_id.removeprefix(resource.flow_name + "_") == start_step_id
                ):
                    d["start_step"] = resource.resource_name
                    break
        return d

    @staticmethod
    def from_pretty(
        contents: str,
        resource_name: str = None,
        resource_mappings: list[ResourceMapping] = None,
        **kwargs,
    ) -> str:
        """Replace resource names with resource IDs in the provided contents."""
        # Replace start_step name with ID if step from same flow
        try:
            yaml_dict = utils.load_yaml(contents) or {}
        except Exception as e:
            raise ValueError(f"Error loading YAML content for {resource_name}") from e

        start_step_name = yaml_dict.get("start_step")
        if start_step_name:
            for resource in resource_mappings or []:
                if (
                    issubclass(resource.resource_type, BaseFlowStep)
                    and resource.flow_name == resource_name
                    and resource.resource_name == start_step_name
                ):
                    yaml_dict["start_step"] = resource.resource_id.removeprefix(
                        resource.flow_name + "_"
                    )
                    break
        return utils.dump_yaml(yaml_dict)

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs):
        """Validate the flow config resource."""
        if not self.start_step:
            raise ValueError("Start step cannot be empty.")

        # Check flow step exists in resource mappings
        found_step = False
        expected_step_resource_id = f"{self.name}_{self.start_step}"
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


@dataclass
class FlowStep(BaseFlowStep, YamlResource):
    """Flow step resource."""

    projection_path: ClassVar[list[str]] = [
        "flows",
        "flows",
        "entities",
        "{flow_id}",
        "steps",
        "entities",
        "{id}",
    ]
    projection_parent_id_field: ClassVar[Optional[str]] = "flow_id"

    asr_biasing: Optional["ASRBiasing"]
    dtmf_config: Optional["DTMFConfig"]
    conditions: Optional[list["Condition"]]
    extracted_entities: Optional[list[str]]
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
        asr_biasing: Optional["ASRBiasing | dict"] = None,
        dtmf_config: Optional["DTMFConfig | dict"] = None,
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

        if isinstance(asr_biasing, ASRBiasing):
            self.asr_biasing = asr_biasing
        elif asr_biasing is not None:
            # resource_id and name are set internally by ASRBiasing.__init__;
            asr_biasing = {k: v for k, v in asr_biasing.items() if k not in ("resource_id", "name")}
            asr_biasing["step_id"] = self.step_id
            asr_biasing["flow_id"] = self.flow_id
            self.asr_biasing = ASRBiasing(**asr_biasing)
        else:
            self.asr_biasing = None

        if isinstance(dtmf_config, DTMFConfig):
            self.dtmf_config = dtmf_config
        elif dtmf_config is not None:
            # resource_id and name are set internally by DTMFConfig.__init__;
            dtmf_config = {k: v for k, v in dtmf_config.items() if k not in ("resource_id", "name")}
            dtmf_config["step_id"] = self.step_id
            dtmf_config["flow_id"] = self.flow_id
            self.dtmf_config = DTMFConfig(**dtmf_config)
        else:
            self.dtmf_config = None

        self.extracted_entities = extracted_entities or []
        self.conditions = [
            Condition(**condition) if not isinstance(condition, Condition) else condition
            for condition in (conditions or [])
        ]
        self.prompt = prompt
        self.position = position or {}

    def to_yaml_dict(self) -> dict:
        """Return a dictionary suitable for YAML serialization."""
        output = {
            "step_type": self.step_type.value,
            "name": self.name,
        }
        if self.step_type == StepType.ADVANCED_STEP:
            output["asr_biasing"] = self.asr_biasing.to_yaml_dict() if self.asr_biasing else {}
            output["dtmf_config"] = self.dtmf_config.to_yaml_dict() if self.dtmf_config else {}

        if self.step_type == StepType.DEFAULT_STEP:
            output["conditions"] = [condition.to_yaml_dict() for condition in self.conditions]
            output["extracted_entities"] = self.extracted_entities

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

        step_id = resource_id.removeprefix(f"{flow_name}_")

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
                        and resource.resource_id.removeprefix(f"{flow_name}_") == child_step_id
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
        asr_biasing = yaml_dict.get("asr_biasing", {})
        dtmf_config = yaml_dict.get("dtmf_config", {})
        extracted_entities = yaml_dict.get("extracted_entities", [])
        if step_type == StepType.DEFAULT_STEP:
            # ASR and DTMF not applicable
            asr_biasing = {}
            dtmf_config = {}
        elif step_type == StepType.ADVANCED_STEP:
            # Conditions not applicable
            conditions = []

        return cls(
            resource_id=resource_id,
            step_id=step_id,
            name=yaml_dict.get("name"),
            flow_id=flow_id,
            flow_name=flow_name,
            step_type=step_type,
            asr_biasing=asr_biasing,
            dtmf_config=dtmf_config,
            prompt=yaml_dict.get("prompt"),
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
                            and flow_folder_name in resource.file_path.split(os.sep)
                            and resource.resource_id.removeprefix(resource.flow_name + "_")
                            == child_step_id
                        ):
                            condition["child_step"] = resource.resource_name
                            break

                if required_entities := condition.get("required_entities"):
                    condition["required_entities"] = [
                        entity_mappings.get(entity_id, entity_id) for entity_id in required_entities
                    ]
        return d

    @staticmethod
    def from_pretty(
        contents: str,
        file_path: str = None,
        resource_mappings: list[ResourceMapping] = None,
        **kwargs,
    ) -> str:
        """Replace resource names with resource IDs in the provided contents."""
        flow_folder_name = utils.get_flow_name_from_path(file_path)

        if not flow_folder_name:
            raise ValueError("flow_name could not be determined from file_path")

        try:
            yaml_dict = utils.load_yaml(contents) or {}
        except Exception as e:
            raise ValueError(f"Error loading YAML content for {file_path}") from e

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
                            and flow_folder_name in resource.file_path.split(os.sep)
                            and resource.resource_name == child_step_name
                        ):
                            condition["child_step"] = resource.resource_id.removeprefix(
                                resource.flow_name + "_"
                            )
                            break

                if required_entities := condition.get("required_entities"):
                    new_required_entities = [
                        entity_mappings.get(entity_name, entity_name)
                        for entity_name in required_entities
                    ]
                    condition["required_entities"] = new_required_entities

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

        content = cls.read_to_raw(
            file_path,
            resource_mappings=resource_mappings,
            flow_name=flow_name,
            **kwargs,
        )
        try:
            yaml_dict = utils.load_yaml(content) or {}
        except Exception as e:
            raise ValueError(f"Error loading YAML file: {file_path}") from e

        # Get file name from file_path
        file_name = os.path.splitext(os.path.basename(file_path))[0]

        return cls.from_yaml_dict(
            yaml_dict,
            resource_id=resource_id,
            file_name=file_name,
            flow_id=flow_id,
            flow_name=flow_name,
            known_conditions=known_conditions,
            known_position=known_position,
            resource_mappings=resource_mappings,
        )

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
                    asr_biasing=self.asr_biasing.build_create_proto(),
                    dtmf_config=self.dtmf_config.build_create_proto(),
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
        if self.step_type == StepType.ADVANCED_STEP and old_resource:
            if (
                self.asr_biasing
                and old_resource
                and (not old_resource.asr_biasing or self.asr_biasing != old_resource.asr_biasing)
            ):
                updated.append(self.asr_biasing)
            if self.dtmf_config and (
                not old_resource.dtmf_config or self.dtmf_config != old_resource.dtmf_config
            ):
                updated.append(self.dtmf_config)

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
class ASRBiasing(SubResource):
    """ASR Biasing configuration."""

    projection_path: ClassVar[list[str]] = []

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
    step_id: str
    flow_id: str

    def __init__(
        self,
        step_id: str,
        flow_id: str,
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
        self.name = "asr"
        self.step_id = step_id
        self.flow_id = flow_id
        self.resource_id = f"{flow_id}.{step_id}"
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

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        return "flow_step_asr_config"

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

    def build_update_proto(self) -> Flow_UpdateStepAsrConfig:
        """Create a proto for updating the ASR biasing configuration."""
        return Flow_UpdateStepAsrConfig(
            flow_id=self.flow_id,
            step_id=self.step_id,
            asr_biasing=StepAsrConfigUpdate(
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
                custom_keywords=UpdateAsrKeywords(
                    custom_keywords=self.custom_keywords,
                ),
                is_enabled=self.is_enabled,
            ),
        )

    def build_delete_proto(self):
        """Create a proto for deleting the ASR biasing configuration."""
        raise NotImplementedError("ASR Biasing config does not support deletion.")

    def build_create_proto(self) -> StepAsrConfig:
        """Create a proto for creating the ASR biasing configuration."""
        return StepAsrConfig(
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
            is_enabled=self.is_enabled,
        )


@dataclass
class DTMFConfig(SubResource):
    """DTMF Configuration."""

    projection_path: ClassVar[list[str]] = []

    is_enabled: bool
    inter_digit_timeout: int
    max_digits: int
    end_key: str
    collect_while_agent_speaking: bool
    is_pii: bool
    step_id: str
    flow_id: str

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

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        return "flow_step_dtmf_config"

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

    def build_update_proto(self) -> Flow_UpdateStepDtmfConfig:
        """Create a proto for updating the DTMF configuration."""
        return Flow_UpdateStepDtmfConfig(
            flow_id=self.flow_id,
            step_id=self.step_id,
            dtmf_config=StepDtmfConfigUpdate(
                is_enabled=self.is_enabled,
                inter_digit_timeout=self.inter_digit_timeout,
                max_digits=self.max_digits,
                end_key=self.end_key,
                collect_while_agent_speaking=self.collect_while_agent_speaking,
                is_pii=self.is_pii,
            ),
        )

    def build_delete_proto(self):
        """Create a proto for deleting the DTMF configuration."""
        raise NotImplementedError("DTMF config deletion not implemented.")

    def build_create_proto(self) -> StepDtmfConfig:
        """Create a proto for creating the DTMF configuration."""
        return StepDtmfConfig(
            is_enabled=self.is_enabled,
            inter_digit_timeout=self.inter_digit_timeout,
            max_digits=self.max_digits,
            end_key=self.end_key,
            collect_while_agent_speaking=self.collect_while_agent_speaking,
            is_pii=self.is_pii,
        )


class ConditionType(str, Enum):
    """Enum for condition types."""

    EXIT_FLOW = "exit_flow_condition"
    STEP = "step_condition"
    NO_CODE_STEP = "no_code_step_condition"
    FUNCTION_STEP = "function_step_condition"


@dataclass
class Condition(SubResource):
    """Conditions for no code steps"""

    projection_path: ClassVar[list[str]] = [
        "flows",
        "flows",
        "entities",
        "{flow_id}",
        "steps",
        "entities",
        "{id}",
    ]
    projection_parent_id_field: ClassVar[Optional[str]] = "flow_id"

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
                and resource.resource_id.removeprefix(resource.flow_name + "_") == self.child_step
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


@dataclass(init=False)
class FunctionStep(Function, BaseFlowStep):
    """Dataclass representing a function step"""

    projection_path: ClassVar[list[str]] = [
        "flows",
        "flows",
        "entities",
        "{flow_id}",
        "steps",
        "entities",
        "{id}",
    ]
    projection_id_field: ClassVar[str] = "step_id"
    projection_parent_id_field: ClassVar[Optional[str]] = "flow_id"

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
        parts = file_path.split(os.sep)
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

        step_id = resource_id.removeprefix(f"{flow_name}_")

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
