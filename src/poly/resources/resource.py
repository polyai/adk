"""Base class for Agent Studio Resource

Copyright PolyAI Limited
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from typing import ClassVar, Optional, TypeAlias

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
    flow_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert the mapping to a JSON serializable dictionary.

        resource_type is stored by its registered name, as the class itself
        cannot be serialized.
        """
        return {
            "resource_id": self.resource_id,
            "resource_type": RESOURCE_CLASS_TO_NAME[self.resource_type],
            "resource_name": self.resource_name,
            "file_path": self.file_path,
            "flow_name": self.flow_name,
            "resource_prefix": self.resource_prefix,
            "flow_id": self.flow_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Optional["ResourceMapping"]:
        """Rebuild a mapping from its serialized form.

        Args:
            data: A dictionary as produced by to_dict().

        Returns:
            The mapping, or None if the resource type is no longer registered or
            the data does not fit the mapping shape. The status file outlives any
            one ADK version, so unknown data is dropped rather than raised on.
        """
        field_names = {f.name for f in fields(cls)}
        # Ignore keys a newer ADK (or a hand edit) may have added.
        mapping_data = {key: value for key, value in data.items() if key in field_names}
        resource_type = mapping_data.get("resource_type")
        if isinstance(resource_type, str):
            resource_type = RESOURCE_NAME_TO_CLASS.get(resource_type)
        if resource_type is None:
            return None
        mapping_data["resource_type"] = resource_type
        try:
            return cls(**mapping_data)
        except TypeError:
            # Missing required fields - drop the one mapping, not the command.
            return None


@dataclass
class BaseResource(ABC):
    """Abstract base class for resources in the Agent Studio."""

    resource_id: str

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
    slim: bool = field(default=False, repr=False, init=False)

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

    @classmethod
    @abstractmethod
    def from_pretty(cls, contents: str, **kwargs) -> str:
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
        if utils.contains_merge_conflict(contents):
            raise utils.MergeConflictError(file_path)
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

    def is_modified(self, other_hash: str) -> bool:
        """

        Args:
            other_hash (str): The other resource hash to compare to.

        Returns:
            bool: True if the resource has changed locally, False otherwise.
        """
        current_hash = self.compute_hash()
        modified = other_hash != current_hash
        return modified

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
            file_path (str): The file path to read the resource from.
            resource_id (str): The ID of the resource.
            resource_name (str): The name of the resource.

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

    @classmethod
    @abstractmethod
    def from_projection(cls, projection: dict) -> dict[str, "Resource"]:
        """Create a dictionary of resources from a projection.

        Args:
            projection (dict): The projection containing resource data.
        Returns:
            dict[str, Resource]: A dictionary mapping resource IDs to Resource instances.
        """
        pass


@dataclass
class SubResource(BaseResource, ABC):
    """Abstract base class for subresources that are displayed
    within other resources but require their own protos.
    """

    name: str


def _strip_strings(data):
    """Recursively strip leading/trailing whitespace from all string values."""
    if isinstance(data, dict):
        return {k: _strip_strings(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_strip_strings(item) for item in data]
    if isinstance(data, str):
        return data.strip()
    return data


class YamlResource(Resource, ABC):
    """Abstract base class for YAML resources in the Agent Studio."""

    @property
    def raw(self) -> str:
        """Serialize the resource into a YAML string representation."""
        return utils.dump_yaml(_strip_strings(self.to_yaml_dict()))

    def compute_hash(self) -> str:
        """Compute a hash from the dict representation (avoids YAML serialization)."""
        return utils.compute_hash_from_dict(_strip_strings(self.to_yaml_dict()))

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
        return utils.dump_yaml(self.to_pretty_dict(_strip_strings(self.to_yaml_dict()), **merged))

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

    @classmethod
    def from_pretty_dict(
        cls, yaml_dict: dict, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> dict:
        """Replace resource names with IDs in a parsed YAML dict, returning a new dict."""
        return utils.replace_resource_names_with_ids_in_data(yaml_dict, resource_mappings or [])

    @classmethod
    def from_pretty(
        cls, contents: str, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> str:
        """Replace resource names with resource IDs in the provided contents."""
        contents = utils.replace_resource_names_with_ids(contents, resource_mappings or [])
        try:
            yaml_dict = utils.load_yaml(contents) or {}
        except Exception:
            return contents
        yaml_dict = cls.from_pretty_dict(yaml_dict, resource_mappings=resource_mappings, **kwargs)
        return utils.dump_yaml(yaml_dict)

    @classmethod
    def _read_yaml_dict(cls, file_path: str) -> dict:
        """Read and parse the resource's YAML file into a dict."""
        contents = cls.read_from_file(file_path)
        if utils.contains_merge_conflict(contents):
            raise utils.MergeConflictError(file_path)
        try:
            return utils.load_yaml(contents) or {}
        except Exception as e:
            raise ValueError(f"Error loading YAML file: {file_path}") from e

    @classmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "YamlResource":
        """Read a local YAML resource from the given file path."""
        resource_mappings = kwargs.pop("resource_mappings", None)
        yaml_dict = cls._read_yaml_dict(file_path)
        yaml_dict = cls.from_pretty_dict(
            yaml_dict,
            resource_mappings=resource_mappings,
            resource_name=resource_name,
            file_path=file_path,
            **kwargs,
        )
        instance = cls.from_yaml_dict(
            yaml_dict,
            resource_id=resource_id,
            name=resource_name,
            resource_mappings=resource_mappings,
            **kwargs,
        )
        utils.check_yaml_field_types(instance)
        return instance

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
    # On Windows, os.path.join('C:', 'foo') produces 'C:foo' (drive-relative),
    # so append os.sep to bare drive letters.
    base_parts = parts[: yaml_idx + 1]
    if base_parts[0].endswith(":"):
        base_parts[0] += os.sep
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
    resource_key: ClassVar[str] = "name"

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
        if utils.contains_merge_conflict(contents):
            raise utils.MergeConflictError(true_file_path)
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
    def _get_matching(cls, file_path: str) -> dict:
        """Return the parsed sub-dict for a single resource from its multi-resource file.

        This is the single read seam: read_from_file dumps it to a string and _read_yaml_dict
        returns it directly. Subclasses whose on-disk format is not a standard sub-dict (e.g.
        a bare scalar) override this to reshape it into a dict.
        """
        true_file_path, segments = _parse_multi_resource_path(file_path)
        top_level_name = segments[0]
        top_level_yaml_dict = cls._get_top_level_data(true_file_path)

        if cls._singleton:
            yaml_dict = top_level_yaml_dict.get(top_level_name, {})
            if not isinstance(yaml_dict, dict):
                raise ValueError(f"Top level YAML data is not a dict: {top_level_yaml_dict}")
            if not yaml_dict:
                raise FileNotFoundError(f"Resource not found in {true_file_path}")
            return yaml_dict

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
        return matching_resource

    @classmethod
    def read_from_file(cls, file_path: str) -> str:
        """Read a single resource's contents from its multi-resource file, as YAML."""
        return utils.dump_yaml(cls._get_matching(file_path))

    @classmethod
    def _read_yaml_dict(cls, file_path: str) -> dict:
        """Return the single resource's parsed sub-dict from the multi-resource file."""
        return cls._get_matching(file_path)

    @classmethod
    def _find_matching(cls, yaml_list, resource_clean_name) -> Optional[dict]:
        return next(
            (
                r
                for r in yaml_list
                if utils.clean_name(r.get(cls.resource_key) or "", lowercase=False)
                == resource_clean_name
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


# ---------------------------------------------------------------------------
# Resource registry
# ---------------------------------------------------------------------------

RESOURCE_NAME_TO_CLASS: dict[str, type[Resource]] = {}
RESOURCE_CLASS_TO_NAME: dict[type[Resource], str] = {}
PROJECTION_REGISTRY: list[type[Resource]] = []


ResourceType: TypeAlias = type[Resource]
ResourceMap: TypeAlias = dict[ResourceType, dict[str, Resource]]
SubResourceType: TypeAlias = type[SubResource]
SubResourceMap: TypeAlias = dict[SubResourceType, dict[str, SubResource]]


def register_resource(name: str) -> callable:
    """Class decorator to register a resource type.

    Registers the class in both the name mapping (for YAML discovery and
    serialization) and the projection registry (for parsing API projections).

    Args:
        name: The string key for this resource type (e.g. "topics", "functions").
    """

    def decorator(cls: type[Resource]) -> type[Resource]:
        RESOURCE_NAME_TO_CLASS[name] = cls
        RESOURCE_CLASS_TO_NAME[cls] = name
        PROJECTION_REGISTRY.append(cls)
        return cls

    return decorator


def _filter_slim_resources(all_resources: ResourceMap) -> tuple[ResourceMap, list[ResourceMapping]]:
    # Imported here: both modules import from this one at module level.
    from poly.resources.function import Function
    from poly.resources.variable import Variable

    slim_resources: list[ResourceMapping] = []
    resources: ResourceMap = {}

    # Variables are slim whenever functions are. Variables have no file of their
    # own - they exist as a reference graph derived from function code - and
    # variableUpdate is gated on jupiter_flows rather than functions, so the API
    # would accept a graph rebuilt from functions the user cannot read.
    functions_slim = any(r.slim for r in all_resources.get(Function, {}).values())

    for resources_dict in all_resources.values():
        for resource in resources_dict.values():
            if isinstance(resource, Variable):
                resource.slim = functions_slim

            if not resource.slim:
                resources.setdefault(type(resource), {})[resource.resource_id] = resource
                continue
            slim_resources.append(
                ResourceMapping(
                    resource_id=resource.resource_id,
                    resource_type=type(resource),
                    resource_name=resource.name,
                    file_path=resource.file_path,
                    flow_name=getattr(resource, "flow_name", None),
                    resource_prefix=resource.get_resource_prefix(file_path=resource.file_path),
                    flow_id=getattr(resource, "flow_id", None),
                )
            )
    return resources, slim_resources


def load_resources_from_projection(
    projection: dict,
) -> tuple[ResourceMap, list[ResourceMapping]]:
    """Parse a projection dict into typed Resources.

    Iterates all registered resource classes and calls their from_projection()
    classmethod. No API dependency — works fully offline.

    Args:
        projection: Raw projection dict from the Sourcerer API or a local file.

    Returns:
        A tuple containing:
        1. A dictionary mapping resource types to {resource_id: Resource}.
        2. A list of ResourceMapping objects for slim resources.
    """
    result: dict[type[Resource], dict[str, Resource]] = {}
    for resource_cls in PROJECTION_REGISTRY:
        resources = resource_cls.from_projection(projection)
        if resources:
            result[resource_cls] = resources

    filtered_resources, slim_resources = _filter_slim_resources(result)

    return filtered_resources, slim_resources
