"""Base class for Agent Studio Resource

Copyright PolyAI Limited
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Optional

from google.protobuf.message import Message

import poly.resources.resource_utils as utils


@dataclass
class ResourceMapping:
    """Data class to hold resource mapping information."""

    resource_id: str
    resource_type: type["Resource"]
    resource_name: str
    file_path: Optional[str]
    flow_name: Optional[str]
    resource_prefix: Optional[str]


@dataclass
class BaseResource(ABC):
    """Abstract base class for resources in the Agent Studio."""

    resource_id: str

    # --- Projection mapping (for --proto diff) ---
    # Override in subclasses. Use {id} for entity ID, {flow_id} for parent flow ID.
    projection_path: ClassVar[list[str]] = []
    projection_id_field: ClassVar[str] = "id"
    projection_update_id_field: ClassVar[Optional[str]] = (
        None  # if update/delete use a different ID field
    )
    projection_parent_id_field: ClassVar[Optional[str]] = (
        None  # for nested resources (e.g. flow_id)
    )

    @property
    @abstractmethod
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        pass

    @property
    def delete_command_type(self) -> str:
        """Get the command type for deleting the resource."""
        return f"delete_{self.command_type}"

    @property
    def create_command_type(self) -> str:
        """Get the command type for creating the resource."""
        return f"create_{self.command_type}"

    @property
    def update_command_type(self) -> str:
        """Get the command type for updating the resource."""
        return f"update_{self.command_type}"

    @abstractmethod
    def build_update_proto(self) -> Message:
        """Create a proto for updating the resource."""
        pass

    @abstractmethod
    def build_delete_proto(self) -> Message:
        """Create a proto for deleting the resource."""
        pass

    @abstractmethod
    def build_create_proto(self) -> Message:
        """Create a proto for creating the resource."""
        pass


@dataclass
class Resource(BaseResource, ABC):
    """Abstract base class for resources in the Agent Studio."""

    resource_id: str
    name: str

    @staticmethod
    def get_resource_prefix(**kwargs) -> str:
        """
        Reference prefix for the resource type
        E.g. "fn" in {fn:id}
        """
        return None

    @property
    @abstractmethod
    def file_path(self) -> str:
        """File path for the resource."""
        pass

    def get_path(self, base_path: str = "") -> str:
        """Get the file path for the resource."""
        return os.path.join(base_path, self.file_path)

    @property
    @abstractmethod
    def raw(self) -> str:
        """Convert the resource to a raw format."""
        pass

    @staticmethod
    @abstractmethod
    def make_pretty(contents: str, **kwargs) -> str:
        """Turn the raw representation of the resource into a pretty format."""
        pass

    def to_pretty(self, **kwargs) -> str:
        """Format the raw representation of the resource."""
        return self.make_pretty(self.raw, **kwargs)

    @staticmethod
    @abstractmethod
    def from_pretty(contents: str, **kwargs) -> str:
        """Undo formatting or changes made to the local resource."""
        pass

    def save(
        self, base_path: str, format: bool = False, save_to_cache: bool = False, **kwargs
    ) -> None:
        """Save the resource to a local path."""
        content = self.to_pretty(**kwargs)
        if format:
            content = self.format_resource(content, file_name=self.name)
        file_path = self.get_path(base_path)
        self.save_to_file(content, file_path)

    @classmethod
    def delete_resource(cls, file_path: str, save_to_cache: bool = False) -> None:
        """Delete the resource from the given file path."""
        if os.path.exists(file_path):
            os.remove(file_path)

    @classmethod
    def read_to_raw(cls, file_path: str, **kwargs) -> str:
        """Read the resource from a local path."""
        contents = cls.read_from_file(file_path)
        return cls.from_pretty(contents, file_path=file_path, **kwargs)

    @abstractmethod
    def validate(self, **kwargs) -> None:
        """Validate the resource.

        Raises:
            Error: If the resource is not valid.
        """
        pass

    @classmethod
    def validate_collection(cls, resources: dict[str, "BaseResource"]) -> None:
        """Validate a collection of resources.

        Raises:
            Error: If the collection is not valid.
        """
        pass

    def get_status(self, other_hash: str) -> tuple[bool, bool]:
        """Check if the status of the resource
        Has it changed locally and if it has a merge conflict

        Args:
            other_hash (str): The other resource hash to compare to.

        Returns:
            tuple[bool, bool]: A tuple containing two booleans:
                - True if the resource has changed locally
                - True if the resource has a merge conflict
        """
        current_hash = self.compute_hash()
        modified = other_hash != current_hash
        has_conflict = utils.contains_merge_conflict(self.raw)
        return modified, has_conflict

    def get_diff(self, other_resource: "Resource") -> str:
        """Get the diff of the resource compared to the local version.

        Args:
            other_resource (Resource): The other resource to compare to.

        Returns:
            str: The diff between the original and local version of the resource.
        """
        if not other_resource:
            return utils.get_diff(self.raw, "")
        return utils.get_diff(self.raw, other_resource.raw)

    @classmethod
    @abstractmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "Resource":
        """Read a local resource from the given file path.

        Args:
            file_name (str): The name of the file.
            file_path (str): The file path to read the resource from.

        Returns:
            Resource: The resource instance.
        """
        pass

    @staticmethod
    @abstractmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover resources of this type in the given base path.

        Args:
            base_path (str): The base path to search for resources.

        Returns:
            list[str]: A list of file paths of discovered resources.
        """
        pass

    def compute_hash(self) -> str:
        """Compute a hash of the resource's raw content.

        Returns:
            str: The computed hash.
        """
        return utils.compute_hash(self.raw)

    @staticmethod
    def save_to_file(content: str, file_path: str) -> None:
        """Save the formatted content to a file."""
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(content)
        except Exception as e:
            raise ValueError(f"Error saving resource to file: {file_path}") from e

    @classmethod
    def read_from_file(cls, file_path: str) -> str:
        """Read the content from a file."""
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            raise FileNotFoundError(f"Error reading file: {file_path}") from e

    @staticmethod
    def format_resource(content: str, **kwargs) -> str:
        """Format the resource content."""
        return content

    def get_new_updated_deleted_subresources(
        self, old_resource: "Resource"
    ) -> tuple[list["SubResource"], list["SubResource"], list["SubResource"]]:
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
        return [], [], []


@dataclass
class SubResource(BaseResource, ABC):
    """Abstract base class for subresources that are displayed
    within other resources but require their own protos.
    """

    name: str


class YamlResource(Resource, ABC):
    """Abstract base class for YAML resources in the Agent Studio."""

    @property
    def raw(self) -> str:
        """Serialize the resource into a YAML string representation."""
        data = self.to_yaml_dict()
        return utils.dump_yaml(data)

    def compute_hash(self) -> str:
        """Compute a hash from the dict representation (avoids YAML serialization)."""
        return utils.compute_hash_from_dict(self.to_yaml_dict())

    @classmethod
    def to_pretty_dict(
        cls,
        d: dict,
        resource_mappings: list[ResourceMapping] = None,
        file_path: str = None,
        **kwargs,
    ) -> dict:
        """Return the pretty dictionary."""
        return d

    def to_pretty(self, **kwargs) -> str:
        """Get the pretty YAML representation: to_yaml_dict -> to_pretty_dict -> dump."""
        merged = {
            "file_path": getattr(self, "file_path", None),
            "resource_name": getattr(self, "name", None),
            **kwargs,
        }
        return utils.dump_yaml(self.to_pretty_dict(self.to_yaml_dict(), **merged))

    @classmethod
    def make_pretty(
        cls,
        contents: str,
        resource_mappings: list[ResourceMapping] = None,
        **kwargs,
    ) -> str:
        """Replace resource IDs with resource names: load -> to_pretty_dict -> dump."""
        yaml_dict = utils.load_yaml(contents) or {}
        return utils.dump_yaml(
            cls.to_pretty_dict(
                yaml_dict,
                resource_mappings=resource_mappings,
                **kwargs,
            )
        )

    @staticmethod
    def from_pretty(
        contents: str, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> str:
        """Replace resource names with resource IDs in the provided contents."""
        return utils.replace_resource_names_with_ids(contents, resource_mappings or [])

    @classmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "YamlResource":
        """Read a local YAML resource from the given file path."""
        content = cls.read_to_raw(file_path, resource_name=resource_name, **kwargs)
        try:
            yaml_dict = utils.load_yaml(content) or {}
        except Exception as e:
            raise ValueError(f"Error loading YAML file: {file_path}") from e
        return cls.from_yaml_dict(yaml_dict, resource_id=resource_id, name=resource_name, **kwargs)

    @abstractmethod
    def to_yaml_dict(self) -> dict:
        """Return a dictionary or string suitable for YAML serialization."""
        pass

    @classmethod
    @abstractmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "YamlResource":
        """Create an instance from YAML data and identity fields."""
        pass

    @staticmethod
    def format_resource(content: str, file_name: str, **kwargs) -> str:
        """Format the resource content."""
        return utils.format_yaml(content, file_name)


def _parse_multi_resource_path(file_path: str) -> tuple[str, list[str]]:
    """Parse a multi-resource path into (yaml_file_path, path_segments).

    Path format: .../file.yaml/segment1/segment2/...
    e.g. config/entities.yaml/entities/customer_name -> (config/entities.yaml, [entities, customer_name])
    e.g. channels/voice/configuration.yaml/greeting -> (channels/voice/configuration.yaml, [greeting])
    """
    path = os.path.normpath(file_path)
    parts = path.split(os.sep)
    # Find the index of the part that ends with .yaml or .yml
    yaml_idx = None
    for i, part in enumerate(parts):
        if part.endswith(".yaml"):
            yaml_idx = i
            break
    if yaml_idx is None:
        raise ValueError(f"Invalid multi-resource path (expected path to .yaml file): {file_path}")
    if yaml_idx >= len(parts) - 1:
        raise ValueError(
            f"Invalid multi-resource path (expected segments after .yaml file): {file_path}"
        )
    # Preserve leading slash for absolute paths (parts[0] is '' for /foo/bar/...)
    base_parts = parts[: yaml_idx + 1]
    yaml_file_path = (
        os.path.join(*base_parts) if base_parts[0] else os.sep + os.path.join(*base_parts[1:])
    )
    segments = parts[yaml_idx + 1 :]
    return yaml_file_path, segments


@dataclass
class MultiResourceYamlResource(YamlResource, ABC):
    """Abstract base class for a resource that is stored in a single YAML file with multiple resources."""

    # Class-level cache: true_file_path -> (mtime, top_level_yaml_dict). Invalidated on write; refreshed when mtime differs.
    _file_cache: ClassVar[dict[str, tuple[float, dict]]] = {}

    # When True, the top-level key maps to a single dict (not a list). Used for singleton resources like VoiceGreeting.
    _singleton: ClassVar[bool] = False

    top_level_name: ClassVar[str]

    @classmethod
    def _get_top_level_data(cls, true_file_path: str) -> dict:
        """Return parsed top-level YAML data for the file, using cache with mtime-based refresh."""
        cached = cls._file_cache.get(true_file_path)
        if not cached and (
            not os.path.exists(true_file_path) or not os.path.isfile(true_file_path)
        ):
            raise FileNotFoundError(f"File not found: {true_file_path}")
        try:
            current_mtime = os.path.getmtime(true_file_path)
        except OSError:
            current_mtime = 0.0
        if cached is not None and cached[0] == current_mtime:
            return cached[1]
        contents = super().read_from_file(true_file_path)
        top_level_yaml_dict = utils.load_yaml(contents) or {}
        cls._file_cache[true_file_path] = (current_mtime, top_level_yaml_dict)
        return top_level_yaml_dict

    @classmethod
    def _update_cache_after_write(cls, true_file_path: str, top_level_yaml_dict: dict) -> None:
        """Update cache after save or delete so next read sees written state."""
        try:
            new_mtime = os.path.getmtime(true_file_path)
        except OSError:
            new_mtime = 0.0
        cls._file_cache[true_file_path] = (new_mtime, top_level_yaml_dict)

    @classmethod
    def read_from_file(cls, file_path: str) -> str:
        true_file_path, segments = _parse_multi_resource_path(file_path)
        top_level_name = segments[0]
        top_level_yaml_dict = cls._get_top_level_data(true_file_path)

        if cls._singleton:
            yaml_dict = top_level_yaml_dict.get(top_level_name, {})
            if not isinstance(yaml_dict, dict):
                raise ValueError(f"Top level YAML data is not a dict: {top_level_yaml_dict}")
            if not yaml_dict:
                raise FileNotFoundError(f"Resource not found in {true_file_path}")
            return utils.dump_yaml(yaml_dict)

        resource_clean_name = segments[-1]
        yaml_list = top_level_yaml_dict.get(top_level_name, [])
        if not isinstance(yaml_list, list):
            raise ValueError(f"Top level YAML data is not a list: {top_level_yaml_dict}")

        matching_resource = cls._find_matching(
            yaml_list,
            resource_clean_name,
        )
        if not matching_resource:
            raise FileNotFoundError(
                f"Resource with name {resource_clean_name} not found in {true_file_path}"
            )
        return utils.dump_yaml(matching_resource)

    @staticmethod
    def _find_matching(yaml_list, resource_clean_name) -> Optional[dict]:
        return next(
            (
                r
                for r in yaml_list
                if utils.clean_name(r.get("name") or "", lowercase=False) == resource_clean_name
            ),
            None,
        )

    def save(
        self, base_path: str, format: bool = False, save_to_cache: bool = False, **kwargs
    ) -> None:
        """Save the resource to a local path."""
        yaml_content = self.to_pretty_dict(
            self.to_yaml_dict(),
            file_path=getattr(self, "file_path", None),
            **kwargs,
        )
        if format:
            content = self.format_resource(utils.dump_yaml(yaml_content), file_name=self.name)
            yaml_content = utils.load_yaml(content) or {}

        # Read current content of top level file
        file_path = self.get_path(base_path)
        true_file_path, _ = _parse_multi_resource_path(file_path)

        # Create empty file if it doesn't exist
        empty_value = {} if self._singleton else []
        if not os.path.exists(true_file_path):
            if not save_to_cache:
                self.save_to_file(f"{self.top_level_name}: {str(empty_value)}", true_file_path)
            else:
                self._file_cache.setdefault(
                    true_file_path, (0.0, {self.top_level_name: empty_value})
                )

        top_level_yaml_dict = self._get_top_level_data(true_file_path)

        if self._singleton:
            top_level_yaml_dict[self.top_level_name] = yaml_content
        else:
            yaml_list = top_level_yaml_dict.get(self.top_level_name, [])
            if not isinstance(yaml_list, list):
                raise ValueError(f"Top level YAML data is not a list: {top_level_yaml_dict}")
            clean_name = utils.clean_name(self.name, lowercase=False)
            matching = self._find_matching(yaml_list, clean_name)
            matching_idx = yaml_list.index(matching) if matching is not None else None
            if matching_idx is not None:
                yaml_list[matching_idx] = yaml_content
            else:
                yaml_list.append(yaml_content)
            top_level_yaml_dict[self.top_level_name] = yaml_list

        # If queue saves, write to cache instead of file
        self._update_cache_after_write(true_file_path, top_level_yaml_dict)
        if not save_to_cache:
            self.save_to_file(utils.dump_yaml(top_level_yaml_dict), true_file_path)

    @classmethod
    def write_cache_to_file(cls) -> None:
        """Write all cached YAML files to disk. No-op for resource types without a file cache."""
        for true_file_path, (mtime, top_level_yaml_dict) in list(cls._file_cache.items()):
            cls.save_to_file(utils.dump_yaml(top_level_yaml_dict), true_file_path)

    @classmethod
    def delete_resource(cls, file_path: str, save_to_cache: bool = False) -> None:
        """Delete the resource from the given file path."""
        true_file_path, segments = _parse_multi_resource_path(file_path)
        top_level_name = segments[0]
        if not os.path.exists(true_file_path):
            return
        top_level_yaml_dict = cls._get_top_level_data(true_file_path)

        if cls._singleton:
            top_level_yaml_dict[top_level_name] = {}
        else:
            resource_clean_name = segments[-1]
            yaml_list = top_level_yaml_dict.get(top_level_name, [])
            matching_resource = cls._find_matching(
                yaml_list,
                resource_clean_name,
            )
            if not matching_resource:
                return
            yaml_list.remove(matching_resource)
            top_level_yaml_dict[top_level_name] = yaml_list

        cls._update_cache_after_write(true_file_path, top_level_yaml_dict)
        if not save_to_cache:
            cls.save_to_file(utils.dump_yaml(top_level_yaml_dict), true_file_path)

    @classmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "YamlResource":
        """Read a local YAML resource from the given file path."""
        content = cls.read_to_raw(file_path, resource_name=resource_name, **kwargs)
        try:
            yaml_dict = utils.load_yaml(content) or {}
        except Exception as e:
            raise ValueError(f"Error loading YAML file: {file_path}") from e
        return cls.from_yaml_dict(yaml_dict, resource_id=resource_id, name=resource_name, **kwargs)

    @abstractmethod
    def to_yaml_dict(self) -> dict:
        """Return a dictionary or string suitable for YAML serialization."""
        pass

    @classmethod
    @abstractmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "YamlResource":
        """Create an instance from YAML data and identity fields."""
        pass

    @staticmethod
    def format_resource(content: str, file_name: str, **kwargs) -> str:
        """Format the resource content."""
        return utils.format_yaml(content, file_name)
