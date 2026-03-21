"""Variable resource for ADK

Variables are a special resource type that does not exist as files on the
filesystem. Instead they are stored in-memory and are used for referencing in
topics and functions.

Copyright PolyAI Limited
"""

import logging
import os
from dataclasses import dataclass
from typing import ClassVar

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.variables_pb2 import (
    Variable_Create,
    Variable_Delete,
    Variable_Update,
)
from poly.resources.function import Function
from poly.resources.resource import Resource, ResourceMapping

logger = logging.getLogger(__name__)


@dataclass
class Variable(Resource):
    """A variable resource.

    Variables do not have a corresponding file on disk.

    They are tracked via resource mapping and are denoted through the vrbl suffix.
    """

    projection_path: ClassVar[list[str]] = ["variables", "variables", "entities", "{id}"]

    resource_id: str
    name: str
    references: dict | None = None

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        references: dict | None = None,
    ):
        self.resource_id = resource_id
        self.name = name
        self.references = references

    @staticmethod
    def get_resource_prefix(**kwargs) -> str:
        return "vrbl"

    @property
    def file_path(self) -> str:
        """File path for the resource."""
        return os.path.join("variables", self.name)

    @classmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "Variable":
        return cls(resource_id=resource_id, name=resource_name)

    @property
    def raw(self) -> str:
        return f"vrbl:{self.name}"

    def save(self, base_path: str, **kwargs) -> None:
        """Variables are not saved to disk."""
        pass

    @classmethod
    def read_from_file(cls, file_path: str) -> str:
        file_name = os.path.basename(file_path)
        return f"vrbl:{file_name}"

    @classmethod
    def delete_resource(cls, file_path: str, **kwargs) -> None:
        """Variables have no file to delete."""
        pass

    @staticmethod
    def make_pretty(
        contents: str, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> str:
        """Replace resource IDs with resource names in the provided contents."""
        return contents

    @staticmethod
    def from_pretty(
        contents: str, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> str:
        """Replace resource names with resource IDs in the provided contents."""
        return contents

    @property
    def command_type(self) -> str:
        return "variable"

    @property
    def delete_command_type(self) -> str:
        return "variable_delete"

    @property
    def create_command_type(self) -> str:
        return "variable_create"

    @property
    def update_command_type(self) -> str:
        return "variable_update"

    def build_create_proto(self) -> Variable_Create:
        return Variable_Create(
            id=self.resource_id,
            name=self.name,
        )

    def build_update_proto(self) -> Variable_Update:
        return Variable_Update(
            id=self.resource_id,
            name=self.name,
            references=self.references,
        )

    def build_delete_proto(self) -> Variable_Delete:
        return Variable_Delete(id=self.resource_id)

    def validate(self, **kwargs) -> None:
        pass

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Variables are not discovered from the filesystem."""
        # Get all function files in project
        functions_files = []
        global_functions_files = os.path.join(base_path, "functions")
        if os.path.exists(global_functions_files):
            functions_files.extend(
                [
                    os.path.join(global_functions_files, file_name)
                    for file_name in os.listdir(global_functions_files)
                    if file_name.endswith(".py")
                ]
            )
        flows_path = os.path.join(base_path, "flows")
        if os.path.exists(flows_path):
            for flow_name in os.listdir(flows_path):
                flow_functions_files = os.path.join(base_path, "flows", flow_name, "functions")
                if os.path.exists(flow_functions_files):
                    functions_files.extend(
                        [
                            os.path.join(flow_functions_files, file_name)
                            for file_name in os.listdir(flow_functions_files)
                            if file_name.endswith(".py")
                        ]
                    )
                function_step_files = os.path.join(base_path, "flows", flow_name, "function_steps")
                if os.path.exists(function_step_files):
                    functions_files.extend(
                        [
                            os.path.join(function_step_files, file_name)
                            for file_name in os.listdir(function_step_files)
                            if file_name.endswith(".py")
                        ]
                    )

        if not functions_files:
            return []

        variable_paths = set()
        for function_file in functions_files:
            function_code = Function.read_from_file(function_file)
            for variable in utils.extract_variable_names_from_code(function_code):
                variable_paths.add(os.path.join(base_path, "variables", variable))
        return list(variable_paths)
