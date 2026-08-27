"""Handling and managing for Documents in Projection

Copyright PolyAI Limited
"""

import logging
import os
from dataclasses import dataclass
from functools import cached_property

from poly.handlers.protobuf.documents_pb2 import (
    Document_Create,
    Document_Delete,
    Document_Update,
)
from poly.resources.resource import Resource, register_resource

logger = logging.getLogger(__name__)

PLATFORM_CONTEXT_FILE = "CONTEXT.MD"


@register_resource("documents")
@dataclass
class Document(Resource):
    """Resource class for managing documents"""

    path: str
    contents: str

    @cached_property
    def file_path(self) -> str:
        """Get the file path for the Document resource."""
        return os.path.join("context", self.path)

    @property
    def raw(self) -> str:
        """Convert the resource to a raw format."""
        return self.contents

    @staticmethod
    def make_pretty(contents: str, **kwargs) -> str:
        """Replace resource IDs with resource names in the provided contents."""
        return contents

    @classmethod
    def from_pretty(cls, contents: str, **kwargs) -> str:
        """Replace resource names with resource IDs in the provided contents."""
        return contents

    def validate(self, **kwargs) -> None:
        """Validate the resource."""
        if self.path.upper() == PLATFORM_CONTEXT_FILE and self.path != PLATFORM_CONTEXT_FILE:
            raise ValueError(
                f"Document path must be {PLATFORM_CONTEXT_FILE} (case-sensitive) for the platform context file."
            )

    @classmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "Document":
        """Read a local Markdown resource from the given file path."""
        content = cls.read_to_raw(file_path, **kwargs)
        # Path is top level file name with extension
        path = os.path.basename(file_path)
        return Document(
            resource_id=resource_id,
            name=resource_name,
            path=path,
            contents=content,
        )

    def build_update_proto(self) -> Document_Update:
        """Create a proto for updating the resource."""
        return Document_Update(path=self.path, content=self.contents)

    def build_create_proto(self) -> Document_Create:
        """Create a proto for creating the resource."""
        return Document_Create(path=self.path, content=self.contents)

    def build_delete_proto(self) -> Document_Delete:
        """Create a proto for deleting the resource."""
        return Document_Delete(path=self.path)

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        return "document"

    @property
    def delete_command_type(self) -> str:
        """Get the command type for deleting the resource."""
        return "document_delete"

    @property
    def create_command_type(self) -> str:
        """Get the command type for creating the resource."""
        return "document_create"

    @property
    def update_command_type(self) -> str:
        """Get the command type for updating the resource."""
        return "document_update"

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover resources of this type in the given base path.

        Args:
            base_path (str): The base path to search for resources.

        Returns:
            list[str]: A list of file paths of discovered resources.
        """
        file_paths = []

        context_path = os.path.join(base_path, "context")

        if not os.path.exists(context_path):
            return file_paths

        for file_name in os.listdir(context_path):
            if not file_name.upper().endswith(".MD"):
                continue
            file_path = os.path.join(context_path, file_name)
            file_paths.append(file_path)

        return file_paths

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "Document"]:
        documents = {}
        documents_projection = (
            projection.get("documents", {}).get("documents", {}).get("entities", {})
        )
        # The projection carries the proto field name, "content".
        if "documents" not in projection or any(
            "content" not in doc for doc in documents_projection.values()
        ):
            logger.debug("No read access to context documents - they will not be pulled.")
            return {}

        for document_id, document_data in documents_projection.items():
            path = document_data.get("path", "") or ""
            name = path.removesuffix(".md").removesuffix(".MD")
            documents[document_id] = Document(
                resource_id=document_id,
                name=name,
                path=path,
                contents=document_data["content"],
            )
        return documents
