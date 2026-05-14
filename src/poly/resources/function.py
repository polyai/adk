"""Handling and managing an Agent Studio Function

Copyright PolyAI Limited
"""

import ast
import logging
import os
import re
import typing as ty
import uuid
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from typing import Literal, Optional, Union

from google.protobuf.message import Message

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.end_function_pb2 import (
    EndFunction_Create,
    EndFunction_Delete,
    EndFunction_Update,
)
from poly.handlers.protobuf.flows_pb2 import (
    Flow_CreateTransitionFunction,
    Flow_DeleteTransitionFunction,
    Flow_UpdateTransitionFunction,
    Flow_UpdateTransitionFunctionLatencyControl,
    TransitionFunction_CreateTransitionFunction,
    TransitionFunction_UpdateTransitionFunction,
)
from poly.handlers.protobuf.functions_pb2 import (
    DelayResponsesUpdate,
    DelayResponseUpdate,
    Function_CreateFunction,
    Function_DeleteFunction,
    Function_UpdateFunction,
    Function_UpdateLatencyControl,
    FunctionCreateLatencyControl,
    FunctionParameterUpdate,
    ParametersUpdate,
)
from poly.handlers.protobuf.functions_pb2 import (
    FunctionDelayResponse as FunctionDelayResponseProto,
)
from poly.handlers.protobuf.start_function_pb2 import (
    StartFunction_Create,
    StartFunction_Delete,
    StartFunction_Update,
)
from poly.resources.resource import Resource, ResourceMapping, SubResource

logger = logging.getLogger(__name__)

FUNCTION_HEADER = "from _gen import *  # <AUTO GENERATED>\n"
LEGACY_FUNCTION_HEADER = "from imports import *  # <AUTO GENERATED>\n"

SchemaType = Literal["string", "integer", "number", "boolean"]

PY_TO_SCHEMA: dict[str, SchemaType] = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
}

SCHEMA_TO_PY = {v: k for k, v in PY_TO_SCHEMA.items()}


class FunctionType(str, Enum):
    """Enum representing the type of function"""

    START = "start"
    END = "end"
    TRANSITION = "transition"
    GLOBAL = "global"
    FUNCTION_STEP = "function_step"


@dataclass
class FunctionParameters:
    """Dataclass representing a function parameter"""

    name: str
    type: SchemaType
    description: str
    id: Optional[str] = None


@dataclass
class FunctionDelayResponse:
    """Dataclass representing a single delay response message"""

    message: str
    duration: int
    id: Optional[str] = None


@dataclass
class FunctionLatencyControl:
    """Dataclass representing latency control settings"""

    enabled: bool = False
    initial_delay: int = 0
    interval: int = 0
    delay_responses: list[FunctionDelayResponse] = field(default_factory=list)

    def __post_init__(self):
        self.delay_responses = [
            FunctionDelayResponse(**delay_response)
            if isinstance(delay_response, dict)
            else delay_response
            for delay_response in self.delay_responses
        ]


@dataclass
class LatencyControl(SubResource):
    """Wrapper for Latency Control protos"""

    function_id: str
    latency_control: FunctionLatencyControl
    flow_id: Optional[str] = None

    def __init__(
        self,
        *,
        function_id: str,
        latency_control: FunctionLatencyControl,
        flow_id: Optional[str] = None,
    ):
        self.name = "latency_control"
        self.resource_id = function_id
        self.function_id = function_id
        self.latency_control = latency_control
        self.flow_id = flow_id

    @property
    def command_type(self) -> str:
        return "flow_transition_function_latency_control" if self.flow_id else "latency_control"

    def to_proto(self, enabled_override: Optional[bool] = None) -> Function_UpdateLatencyControl:
        enabled = self.latency_control.enabled if enabled_override is None else enabled_override
        delay_responses = DelayResponsesUpdate(
            delay_responses=[
                DelayResponseUpdate(
                    id=dr.id or f"DELAY-{uuid.uuid4().hex[:8]}",
                    message=dr.message,
                    duration=dr.duration,
                )
                for dr in self.latency_control.delay_responses
            ]
        )
        return Function_UpdateLatencyControl(
            function_id=self.function_id,
            enabled=enabled,
            delay_responses=delay_responses,
            initial_delay=self.latency_control.initial_delay if enabled else 0,
            interval=self.latency_control.interval if enabled else 0,
        )

    def build_update_proto(self) -> Message:
        proto = self.to_proto()
        if self.flow_id:
            return Flow_UpdateTransitionFunctionLatencyControl(
                flow_id=self.flow_id, latency_control=proto
            )
        return proto

    def build_create_proto(self) -> Message:
        return self.build_update_proto()

    def build_delete_proto(self) -> Message:
        raise NotImplementedError("Latency Control does not support deletion")


@dataclass
class Function(Resource):
    """Dataclass representing an Agent Studio function"""

    description: str
    code: str
    parameters: list[FunctionParameters]
    latency_control: FunctionLatencyControl
    flow_id: Optional[str] = None
    flow_name: Optional[str] = None
    function_type: Optional[FunctionType] = None
    variable_references: Optional[dict] = None

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        description: str,
        code: str,
        parameters: list[FunctionParameters],
        latency_control: dict | FunctionLatencyControl,
        function_type: FunctionType,
        flow_id: str | None = None,
        flow_name: str | None = None,
        variable_references: dict | None = None,
    ):
        self.resource_id = resource_id
        self.name = name
        self.description = description
        self.code = code
        self.parameters = [
            FunctionParameters(**p) if isinstance(p, dict) else p for p in (parameters or [])
        ]
        self.latency_control = self._parse_latency_control(latency_control)
        self.flow_id = flow_id
        self.flow_name = flow_name
        self.function_type = function_type
        self.variable_references = variable_references

    @staticmethod
    def _parse_latency_control(value) -> FunctionLatencyControl:
        if value is None or value == {}:
            return FunctionLatencyControl()

        if isinstance(value, FunctionLatencyControl):
            return value

        if isinstance(value, dict):
            return FunctionLatencyControl(
                enabled=value.get("enabled", False),
                initial_delay=value.get("initial_delay", value.get("initialDelay", 0)),
                interval=value.get("interval", 0),
                delay_responses=value.get("delay_responses", []),
            )
        return FunctionLatencyControl()

    @staticmethod
    def get_function_type(file_path: str) -> Optional[FunctionType]:
        """Get the function type from the file path and function name.

        Args:
            file_path (str): The file path of the function.

        Returns:
            Optional[FunctionType]: The function type.
        """
        parts = os.path.normpath(file_path).split(os.sep)
        function_name = os.path.splitext(parts[-1])[0]
        if len(parts) >= 4 and parts[-4] == "flows":
            if parts[-2] == "function_steps":
                return FunctionType.FUNCTION_STEP
            elif parts[-2] == "functions":
                return FunctionType.TRANSITION
        elif function_name == "start_function":
            return FunctionType.START
        elif function_name == "end_function":
            return FunctionType.END
        else:
            return FunctionType.GLOBAL

    @staticmethod
    def get_resource_prefix(file_path: str) -> str:
        """Get the resource prefix for the resource based on file path.

        Args:
            file_path (str): The file path of the resource.

        Returns:
            str: The resource prefix.
        """
        function_type = Function.get_function_type(file_path)
        if function_type == FunctionType.TRANSITION:
            return "ft"
        if function_type in (FunctionType.START, FunctionType.END, FunctionType.FUNCTION_STEP):
            return None
        return "fn"

    @cached_property
    def file_path(self) -> str:
        """File path for the resource."""
        file_name = f"{self.name}.py"
        if self.flow_name:
            flow_name = utils.clean_name(self.flow_name)
            return os.path.join("flows", flow_name, "functions", file_name)
        return os.path.join("functions", file_name)

    def _generate_raw_output(
        self,
        add_description: bool = True,
        add_parameters: bool = True,
        add_latency_control: bool = True,
    ) -> str:
        """Generate the pretty code for the function."""
        code = self.code

        try:
            target = self._get_target_function(code, self.name)
        except SyntaxError as e:
            logger.error(f"Syntax error while reading function {self.name!r} e={e!r}")
            return code

        has_decorators = (
            (self.parameters and add_parameters)
            or (self.description and add_description)
            or (self.latency_control and self.latency_control.enabled and add_latency_control)
        )
        if not has_decorators or not target:
            return code

        try:
            lines = code.splitlines(True)
            # Insert above the top-most decorator in the decorator block.
            insert_at = target.lineno - 1
            while insert_at > 0 and lines[insert_at - 1].lstrip().startswith("@"):
                insert_at -= 1
            indent = re.match(r"^([ \t]*)", lines[target.lineno - 1]).group(1)
            decorator_block = []
            if add_description:
                decorator_block.append(f"{indent}@func_description({self.description!r})\n")
            if add_parameters:
                decorator_block.extend(
                    f"{indent}@func_parameter({p.name!r}, {p.description!r})\n"
                    for p in self.parameters
                )
            if add_latency_control and self.latency_control and self.latency_control.enabled:
                decorator_block.append(
                    self._render_latency_control_decorator(self.latency_control, indent)
                )
            if decorator_block:
                lines.insert(insert_at, "".join(decorator_block))
            return "".join(lines)
        except SyntaxError as e:
            logger.error(f"error while converting function to raw format e={e!r}")
            return code  # return original code without injection if invalid

    @property
    def raw(self) -> str:
        """Convert the resource to raw format."""

        return self._generate_raw_output(
            add_description=True, add_parameters=True, add_latency_control=True
        )

    @staticmethod
    def make_pretty(contents: str, resource_mappings: list[ResourceMapping], **kwargs) -> str:
        """Format the raw representation of the resource."""
        # Removing leading newlines
        contents = contents.lstrip("\n")

        # Check if contents starts with a module-level docstring
        docstring_end = None
        if contents.startswith('"""') or contents.startswith("'''"):
            quote_type = contents[:3]
            # Find the closing quote
            end_pos = contents.find(quote_type, 3)
            if end_pos != -1:
                docstring_end = end_pos + 3

        # If there's a docstring, insert FUNCTION_HEADER after it
        if docstring_end is not None:
            before_docstring = contents[:docstring_end]
            after_docstring = contents[docstring_end:].lstrip("\n")

            # Add header after docstring with appropriate spacing
            if after_docstring and (
                after_docstring.startswith("from ") or after_docstring.startswith("import ")
            ):
                # There are imports right after, add header with single newline
                code = before_docstring + "\n" + FUNCTION_HEADER + after_docstring
            else:
                # No imports right after, add header with two newlines
                code = before_docstring + "\n" + FUNCTION_HEADER + "\n" + after_docstring
        else:
            # No docstring, add header at the top
            # If there are no imports, add two newlines after the header
            if not contents.startswith(("from ", "import ")):
                code = FUNCTION_HEADER + "\n\n" + contents
            else:
                code = FUNCTION_HEADER + contents

        # Convert `functions.{flow_id}` to `flows.{flow_name}.functions`
        for resource in resource_mappings:
            if resource.resource_type.__name__ == "FlowConfig":
                code = code.replace(
                    f"functions.{utils.clean_name(resource.resource_id)}",
                    f"flows.{utils.clean_name(resource.resource_name)}.functions",
                )

        return code

    @staticmethod
    def from_pretty(
        contents: str, resource_mappings: list[ResourceMapping], resource_name: str = None, **kwargs
    ) -> str:
        """Undo formatting or changes made to the local resource."""
        # Remove typing import if it exists
        code = contents

        if not code:
            return code

        if FUNCTION_HEADER in code:
            code = code.replace(FUNCTION_HEADER, "")
        if LEGACY_FUNCTION_HEADER in code:
            code = code.replace(LEGACY_FUNCTION_HEADER, "")

        # Remove leading newlines
        code = code.lstrip("\n")

        # Convert `flows.{flow_name}.functions` to `functions.{flow_id}`
        for resource in resource_mappings:
            if resource.resource_type.__name__ == "FlowConfig":
                code = code.replace(
                    f"flows.{utils.clean_name(resource.resource_name)}.functions",
                    f"functions.{utils.clean_name(resource.resource_id)}",
                )

        code = utils.restore_function_def_line(code, resource_name)

        return code

    @staticmethod
    def _param_def_string(parameter: FunctionParameters):
        """Get the def string for the parameter"""
        return f"{parameter.name}: {SCHEMA_TO_PY.get(parameter.type, 'str')}"

    @staticmethod
    def _render_latency_control_decorator(lc: FunctionLatencyControl, indent: str) -> str:
        parts = [
            f"delay_before_responses_start={lc.initial_delay!r}",
            f"silence_after_each_response={lc.interval!r}",
        ]
        if lc.delay_responses:
            dr_items = ", ".join(f"({dr.message!r}, {dr.duration!r})" for dr in lc.delay_responses)
            parts.append(f"delay_responses=[{dr_items}]")
        return f"{indent}@func_latency_control({', '.join(parts)})\n"

    def validate(self, **kwargs) -> None:
        """Validate the resource.

        Raises:
            ValidationError: If the resource is not valid.
        """
        # Check for syntax errors
        try:
            compile(self.code, self.name, "exec")
        except SyntaxError as e:
            logger.debug(f"Syntax error validating code={self.code!r}")
            raise ValueError(f"Syntax error in function code: {e}")

        # Check function def exists in code
        default_params = ["conv: Conversation"]
        if self.function_type in (FunctionType.TRANSITION, FunctionType.FUNCTION_STEP):
            default_params.append("flow: Flow")
        params = default_params + [self._param_def_string(p) for p in self.parameters]
        function_def = f"def {self.name}({', '.join(params)})"

        if function_def not in self.code:
            raise ValueError(f"Function definition '{function_def}' not found in code.")

        # Ensure description exists
        if not self.description and self.function_type not in [
            FunctionType.START,
            FunctionType.END,
            FunctionType.FUNCTION_STEP,
        ]:
            raise ValueError("Function description cannot be empty.")

        if self.description and self.description != self.description.strip():
            raise ValueError("Description cannot contain leading or trailing whitespace.")

        # Ensure flow_id is set for transition functions
        if self.function_type == FunctionType.TRANSITION and not self.flow_id:
            raise ValueError("Can't find flow_id for transition function.")

        # Validate latency control settings
        if self.latency_control and self.latency_control.enabled:
            if not (0 <= self.latency_control.initial_delay <= 10):
                raise ValueError(
                    "delay_before_responses_start must be between 0 and 10, "
                    f"got {self.latency_control.initial_delay}."
                )
            if not (0 <= self.latency_control.interval <= 10):
                raise ValueError(
                    "silence_after_each_response must be between 0 and 10, "
                    f"got {self.latency_control.interval}."
                )
            if not self.latency_control.delay_responses:
                raise ValueError("delay_responses cannot be empty.")

        for line in self.code.splitlines():
            if line.strip().startswith("#"):
                continue
            if (
                line.startswith("@func_description")
                or line.startswith("@func_parameter")
                or line.startswith("@func_latency_control")
            ):
                raise ValueError(
                    "ADK decorators found in raw code. This might be because of a parameter mismatch."
                )

        resource_mappings = kwargs.get("resource_mappings") or []
        code_for_validation = utils.remove_comments_from_code(self.code)

        if self.flow_name and resource_mappings:
            valid_step_names = {
                r.resource_name
                for r in resource_mappings
                if r.resource_type.__name__ in ("FlowStep", "FunctionStep")
                and r.flow_name == self.flow_name
            }
            if valid_step_names:
                for match in re.finditer(
                    r'flow\.goto_step\(\s*"((?:[^"\\]|\\.)*)"'
                    r"|flow\.goto_step\(\s*'((?:[^'\\]|\\.)*)'",
                    code_for_validation,
                ):
                    target_step = match.group(1) or match.group(2)
                    if target_step not in valid_step_names:
                        raise ValueError(
                            f"flow.goto_step('{target_step}') references a step that does not exist "
                            f"in flow '{self.flow_name}'."
                        )

        if resource_mappings:
            valid_flow_names = {
                r.resource_name
                for r in resource_mappings
                if r.resource_type.__name__ == "FlowConfig"
            }
            if valid_flow_names:
                for match in re.finditer(
                    r'conv\.goto_flow\(\s*"((?:[^"\\]|\\.)*)"'
                    r"|conv\.goto_flow\(\s*'((?:[^'\\]|\\.)*)'",
                    code_for_validation,
                ):
                    target_flow = match.group(1) or match.group(2)
                    if target_flow not in valid_flow_names:
                        raise ValueError(
                            f"conv.goto_flow('{target_flow}') references a flow that does not exist."
                        )

    @staticmethod
    def _get_target_function(
        code: str, function_name: str
    ) -> Optional[Union[ast.FunctionDef, ast.AsyncFunctionDef]]:
        module = ast.parse(code)
        return next(
            (
                f
                for f in ast.walk(module)
                if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))
                and f.name == function_name
            ),
            None,
        )

    @staticmethod
    def _extract_decorators(
        code: str,
        function_name: str,
        known_parameters: list[FunctionParameters],
        known_latency_control: Optional[FunctionLatencyControl] = None,
    ) -> tuple[str, list[FunctionParameters], Optional[str], FunctionLatencyControl]:
        """Extract decorators from the function code.

        Args:
            code (str): The function code.

        Returns:
            tuple: The cleaned code, list of parameters, and description.
        """
        parameters: list[FunctionParameters] = []
        description: str = None
        latency_control = FunctionLatencyControl()
        target = Function._get_target_function(code, function_name)
        if target:
            removable_lines: set[int] = set()
            for decorator in target.decorator_list:
                if not (hasattr(decorator, "func") and hasattr(decorator.func, "id")):
                    continue

                decorator_name = decorator.func.id

                if decorator_name == "func_parameter" and len(decorator.args) == 2:
                    name, desc = (arg.value for arg in decorator.args)
                    matched_arg = next((arg for arg in target.args.args if arg.arg == name), None)
                    if matched_arg is None or matched_arg.annotation is None:
                        raise ValueError(
                            f"Parameter {name!r} has no type annotation. "
                            f"Supported types: str, int, float, bool."
                        )
                    if not hasattr(matched_arg.annotation, "id"):
                        raise ValueError(
                            f"Parameter {name!r} has an unsupported type annotation. "
                            f"Supported types: str, int, float, bool."
                        )
                    _type = matched_arg.annotation.id

                    _id = next(
                        (param.id for param in known_parameters if param.name == name),
                        f"PARAMETER-{uuid.uuid4().hex[:8]}",
                    )

                    if _type in PY_TO_SCHEMA:
                        parameters.append(
                            FunctionParameters(
                                id=_id,
                                name=name,
                                description=desc,
                                type=PY_TO_SCHEMA[_type],
                            )
                        )
                        removable_lines.update(range(decorator.lineno - 1, decorator.end_lineno))
                elif decorator_name == "func_description" and len(decorator.args) == 1:
                    description = (decorator.args[0].value).strip()
                    removable_lines.update(range(decorator.lineno - 1, decorator.end_lineno))

                elif decorator_name == "func_latency_control":
                    latency_control = Function._parse_latency_control_decorator(
                        decorator, known_latency_control
                    )
                    removable_lines.update(range(decorator.lineno - 1, decorator.end_lineno))

            if removable_lines:
                lines = code.splitlines(True)
                code = "".join(line for idx, line in enumerate(lines) if idx not in removable_lines)
        return code, parameters, description, latency_control

    @staticmethod
    def _parse_latency_control_decorator(
        decorator: ast.Call,
        known_latency_control: Optional[FunctionLatencyControl] = None,
    ) -> FunctionLatencyControl:
        """Parse @func_latency_control into FunctionLatencyControl dataclass."""

        initial_delay = 0
        interval = 0
        delay_responses: list[FunctionDelayResponse] = []
        used_delay_response_ids: set[str] = set()

        for kw in decorator.keywords:
            if kw.arg == "delay_before_responses_start" and isinstance(kw.value, ast.Constant):
                initial_delay = kw.value.value
            elif kw.arg == "silence_after_each_response" and isinstance(kw.value, ast.Constant):
                interval = kw.value.value
            elif kw.arg == "delay_responses" and isinstance(kw.value, ast.List):
                for elt in kw.value.elts:
                    if isinstance(elt, ast.Tuple) and len(elt.elts) == 2:
                        msg = elt.elts[0].value if isinstance(elt.elts[0], ast.Constant) else ""
                        dur = elt.elts[1].value if isinstance(elt.elts[1], ast.Constant) else 0
                        # Preserve existing ID when the message text matches.
                        existing_id = None
                        if known_latency_control and known_latency_control.delay_responses:
                            existing_id = next(
                                (
                                    dr.id
                                    for dr in known_latency_control.delay_responses
                                    if dr.message == msg and dr.id not in used_delay_response_ids
                                ),
                                None,
                            )
                        if existing_id:
                            used_delay_response_ids.add(existing_id)
                        delay_responses.append(
                            FunctionDelayResponse(
                                id=existing_id or f"DELAY-{uuid.uuid4().hex[:8]}",
                                message=msg,
                                duration=dur,
                            )
                        )

        return FunctionLatencyControl(
            enabled=True,  # if decorator exists, implies enabled = True
            initial_delay=initial_delay,
            interval=interval,
            delay_responses=delay_responses,
        )

    @staticmethod
    def _extract_variable_references(code: str, resource_mappings: list[ResourceMapping]) -> dict:
        """Extract variable references from code."""
        variable_references = {}
        variable_names = utils.extract_variable_names_from_code(code)

        if variable_names:
            # Swap variable names for ids:
            known_variables = {
                v.resource_name: v.resource_id
                for v in resource_mappings
                if v.resource_type.__name__ == "Variable"
            }
            for name in variable_names:
                if name not in known_variables:
                    logger.warning(
                        f"Variable {name} not found in resource mappings, will be added in the next push"
                    )
                    continue
                variable_references[known_variables[name]] = True
        return variable_references

    @classmethod
    def read_local_resource(
        cls,
        file_path: str,
        resource_id: str,
        resource_name: str,
        resource_mappings: list[ResourceMapping],
        known_parameters: list[FunctionParameters],
        known_latency_control: FunctionLatencyControl = None,
        **kwargs,
    ) -> "Function":
        """Read a local YAML resource from the given file path."""

        code = cls.read_to_raw(
            file_path, resource_mappings=resource_mappings, resource_name=resource_name, **kwargs
        )

        if known_latency_control is None:
            known_latency_control = FunctionLatencyControl()

        # Extract description, parameters, latency_control from code
        code, parameters, description, latency_control = cls._extract_decorators(
            code, resource_name, known_parameters, known_latency_control
        )

        # flow_name can be inferred from file path
        # e.g. flows/{flow_name}/functions/{function_name}.py
        parts = os.path.normpath(file_path).split(os.sep)
        if len(parts) >= 4 and parts[-4] == "flows":
            flow_folder_name = parts[-3]
        else:
            flow_folder_name = None

        # Search for flow_id in resource mappings
        flow_id = None
        flow_name = None
        if flow_folder_name:
            flow_id, flow_name = utils.get_flow_id_from_flow_name(
                flow_folder_name, resource_mappings
            )

        # function_type can be inferred from file path
        function_type = cls.get_function_type(file_path)

        # Read references from code
        variable_references = cls._extract_variable_references(code, resource_mappings)

        return Function(
            resource_id=resource_id,
            name=resource_name,
            description=description,
            code=code,
            parameters=parameters,
            latency_control=latency_control,
            flow_id=flow_id,
            flow_name=flow_name,
            function_type=function_type,
            variable_references=variable_references,
        )

    @staticmethod
    def _create_function_param_updates(
        parameters: list[FunctionParameters],
    ) -> FunctionParameterUpdate:
        """Create parameter updates for the function."""
        return [
            FunctionParameterUpdate(
                id=p.id,
                name=p.name,
                description=p.description,
                type=p.type,
            )
            for p in parameters
        ]

    def build_update_proto(
        self,
    ) -> ty.Union[
        StartFunction_Update,
        EndFunction_Update,
        Flow_UpdateTransitionFunction,
        Function_UpdateFunction,
    ]:
        """Create a proto for updating the resource."""

        params_update = ParametersUpdate(
            parameters=self._create_function_param_updates(self.parameters)
        )

        fn_proto = {
            "id": self.resource_id,
            "code": self.code,
            "description": self.description,
        }
        if self.function_type in (FunctionType.GLOBAL, FunctionType.TRANSITION):
            fn_proto["parameters"] = params_update

        if self.function_type != FunctionType.TRANSITION:
            fn_proto["references"] = {
                "variables": self.variable_references or {},
            }

        if self.function_type == FunctionType.START:
            return StartFunction_Update(**fn_proto)
        elif self.function_type == FunctionType.END:
            return EndFunction_Update(**fn_proto)
        elif self.function_type == FunctionType.TRANSITION:
            return Flow_UpdateTransitionFunction(
                flow_id=self.flow_id,
                transition_function=TransitionFunction_UpdateTransitionFunction(**fn_proto),
            )

        return Function_UpdateFunction(**fn_proto)

    def _build_create_latency_control_proto(self) -> FunctionCreateLatencyControl:
        delay_responses = [
            FunctionDelayResponseProto(
                id=dr.id or f"DELAY-{uuid.uuid4().hex[:8]}",
                message=dr.message,
                duration=dr.duration,
            )
            for dr in self.latency_control.delay_responses
        ]
        return FunctionCreateLatencyControl(
            enabled=self.latency_control.enabled,
            delay_responses=delay_responses,
            initial_delay=self.latency_control.initial_delay,
            interval=self.latency_control.interval,
        )

    def build_create_proto(self) -> Message:
        """Create a proto for creating the resource."""
        if self.parameters:
            params_update = self._create_function_param_updates(self.parameters)
        else:
            params_update = None

        fn_proto = {
            "id": self.resource_id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
        }
        if params_update is not None:
            fn_proto["parameters"] = params_update

        fn_proto["references"] = {
            "variables": self.variable_references or {},
        }

        if self.function_type == FunctionType.START:
            return StartFunction_Create(**fn_proto)
        elif self.function_type == FunctionType.END:
            return EndFunction_Create(**fn_proto)
        elif self.function_type == FunctionType.TRANSITION:
            fn_proto["references"]["flow_steps"] = {}
            return Flow_CreateTransitionFunction(
                flow_id=self.flow_id,
                transition_function=TransitionFunction_CreateTransitionFunction(**fn_proto),
            )

        if self.latency_control and self.latency_control.enabled:
            fn_proto["latency_control"] = self._build_create_latency_control_proto()

        return Function_CreateFunction(**fn_proto)

    def build_delete_proto(self) -> Message:
        """Create a proto for deleting the resource."""
        if self.function_type == FunctionType.START:
            return StartFunction_Delete(id=self.resource_id)
        elif self.function_type == FunctionType.END:
            return EndFunction_Delete(id=self.resource_id)
        elif self.function_type == FunctionType.TRANSITION:
            return Flow_DeleteTransitionFunction(
                flow_id=self.flow_id,
                function_id=self.resource_id,
            )
        return Function_DeleteFunction(id=self.resource_id)

    def get_new_updated_deleted_subresources(
        self, old_resource: ty.Optional["Function"] = None
    ) -> tuple[list[SubResource], list[SubResource], list[SubResource]]:
        """Detect latency-control changes that need their own command."""
        new: list[SubResource] = []
        updated: list[SubResource] = []

        new_lc = self.latency_control
        old_lc = old_resource.latency_control if old_resource else FunctionLatencyControl()

        if new_lc != old_lc:
            sub = LatencyControl(
                function_id=self.resource_id,
                latency_control=new_lc,
                flow_id=self.flow_id if self.function_type == FunctionType.TRANSITION else None,
            )
            updated.append(sub)

        return new, updated, []

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        if self.function_type == FunctionType.START:
            return "start_function"
        elif self.function_type == FunctionType.END:
            return "end_function"
        elif self.function_type == FunctionType.TRANSITION:
            return "flow_transition_function"
        elif self.function_type == FunctionType.GLOBAL:
            return "function"

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover resources of this type in the given base path.

        Args:
            base_path (str): The base path to search for resources.

        Returns:
            list[str]: A list of file paths of discovered resources.
        """
        discovered_functions: list[str] = []

        # Find all transition functions in flows/*/functions/
        functions_path = os.path.join(base_path, "flows")
        discovered_flow_functions: list[str] = []
        if os.path.exists(functions_path):
            discovered_flow_functions = os.listdir(functions_path)
        for flow_name in discovered_flow_functions:
            flow_functions_path = os.path.join(functions_path, flow_name, "functions")
            if not os.path.exists(flow_functions_path):
                continue

            discovered_functions.extend(
                [
                    os.path.join(flow_functions_path, file_name)
                    for file_name in os.listdir(flow_functions_path)
                    if file_name.endswith(".py")
                ]
            )

        # Find all global functions in functions/
        functions_path = os.path.join(base_path, "functions")
        if not os.path.exists(functions_path):
            return discovered_functions

        discovered_functions.extend(
            [
                os.path.join(functions_path, file_name)
                for file_name in os.listdir(functions_path)
                if file_name.endswith(".py")
            ]
        )

        return discovered_functions

    @staticmethod
    def format_resource(content, file_name: str) -> str:
        """Format the resource code using ruff."""
        return utils.format_code_with_ruff(content, file_name)
