"""Agent Studio project management

Copyright PolyAI Limited
"""

import base64
import json
import logging
import os
import shutil
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field, fields
from datetime import datetime
from enum import Enum
from functools import cached_property
from typing import Any, Optional, TypeAlias

from google.protobuf.message import Message

import poly.resources.resource_utils as resource_utils
import poly.utils as utils
from poly.handlers.interface import (
    AgentStudioInterface,
)
from poly.migration_utils import (
    MigrationFlag,
    get_all_migration_flags,
    load_migration_flags,
    run_migrations,
)
from poly.resources import (
    BaseFlowStep,
    ChildTopic,
    Document,
    FlowConfig,
    FlowStep,
    Function,
    FunctionStep,
    MultiResourceYamlResource,
    Pronunciation,
    Resource,
    ResourceMap,
    ResourceMapping,
    ResourceType,
    SubResourceMap,
    TestCase,
    Topic,
)
from poly.resources.resource import (
    RESOURCE_CLASS_TO_NAME,
    RESOURCE_NAME_TO_CLASS,
    _parse_multi_resource_path,
    load_resources_from_projection,
)
from poly.utils import prepush
from poly.utils.commands import queue_set_default_commands

logger = logging.getLogger(__name__)


PROJECT_CONFIG_FILE = "project.yaml"
STATUS_FILE = os.path.join("_gen", ".agent_studio_config")

DECORATORS = ["func_parameter", "func_description", "func_latency_control"]

DiscoveredResourcePaths: TypeAlias = dict[ResourceType, list[str]]
ResourceUpdatePair: TypeAlias = tuple[ResourceMap, ResourceMap]


@dataclass
class ResourceChangeSet:
    new: ResourceMap
    updated: ResourceMap
    deleted: ResourceMap


@dataclass
class SubResourceChangeSet:
    new: SubResourceMap
    updated: SubResourceMap
    deleted: SubResourceMap


@dataclass
class PushPhaseChangeSet:
    main: ResourceChangeSet
    pre: ResourceChangeSet
    post: ResourceChangeSet


class DeploymentMode(Enum):
    """Deployment mode for the project"""

    SIMPLE = "simple"
    RELEASES = "releases"
    RELEASES_BRANCHES = "releases_branches"


@dataclass
class AgentStudioProject:
    """Dataclass representing an Agent Studio Project"""

    region: str
    account_id: str
    project_id: str
    root_path: str
    resources: ResourceMap
    last_updated: datetime
    slim_resources: list[ResourceMapping] = field(default_factory=list)
    branch_id: str = None
    project_name: Optional[str] = None
    account_name: Optional[str] = None
    _api_handler: AgentStudioInterface = None
    file_structure_info: dict[str, dict[str, str]] = None
    _migration_flags: set[MigrationFlag] = None
    rtc_metadata: Optional[dict[str, dict]] = None
    _deployment_mode: Optional[DeploymentMode] = None

    # Store resources that were not loaded from the status file
    # So they aren't considered locally deleted when pushing/pulling
    # before they are saved.
    _not_loaded_resources: list[ResourceType] = field(default_factory=list)

    @property
    def all_resources(self) -> list[Resource]:
        """Get all resources in the project"""
        all_resources = []
        for resources_dict in self.resources.values():
            all_resources.extend(resources_dict.values())
        return all_resources

    @property
    def api_handler(self) -> AgentStudioInterface:
        """Get the API handler for the project"""
        if self._api_handler is None:
            self._api_handler = AgentStudioInterface(
                self.region,
                self.account_id,
                self.project_id,
                self.branch_id,
            )
        self.branch_id = self._api_handler.branch_id
        if self.branch_id:
            self.save_config()  # To save branch if it changed (e.g. deleted in remote)
        return self._api_handler

    def build_project_config(self) -> dict:
        """Build the project configuration dictionary"""
        config = {
            "project_id": self.project_id,
            "account_id": self.account_id,
            "region": self.region,
        }
        if self.project_name:
            config["project_name"] = self.project_name
        if self.account_name:
            config["account_name"] = self.account_name
        return config

    @classmethod
    def _load_resources_from_status_dict(
        cls, status_dict: dict
    ) -> tuple[ResourceMap, list[ResourceType], list[ResourceMapping]]:
        resources: ResourceMap = {}
        not_loaded_resources: list[ResourceType] = []
        slim_resources: list[ResourceMapping] = []
        for resource_name, resource_class in RESOURCE_NAME_TO_CLASS.items():
            resource_dicts: Optional[dict[str, dict[str, Any]]] = status_dict.get(
                "resources", {}
            ).get(resource_name, None)
            if resource_dicts is None:
                not_loaded_resources.append(resource_class)
                resources[resource_class] = {}
                continue

            init_field_names = {f.name for f in fields(resource_class) if f.init}
            resources[resource_class] = {
                resource_id: resource_class(
                    **{k: v for k, v in resource_dict.items() if k in init_field_names}
                )
                for resource_id, resource_dict in resource_dicts.items()
            }
        for slim_resource_dict in status_dict.get("slim_resources", []):
            resource_mapping = ResourceMapping.from_dict(slim_resource_dict)
            if resource_mapping is not None:
                slim_resources.append(resource_mapping)

        return resources, not_loaded_resources, slim_resources

    @classmethod
    def from_file_path(cls, root_path: str) -> "AgentStudioProject":
        """Load project class from a file path"""
        # Load config file
        config_file_path = os.path.join(root_path, PROJECT_CONFIG_FILE)
        if not os.path.exists(config_file_path):
            raise FileNotFoundError(f"Config file not found at {config_file_path}")

        with open(config_file_path, "r", encoding="utf-8") as f:
            config_dict = resource_utils.load_yaml(f) or {}

        # Load status file
        status_file_path = os.path.join(root_path, STATUS_FILE)
        status_dict = {}
        if not os.path.exists(status_file_path):
            logger.info(
                f"Status file not found at {status_file_path}, initialising with no resources"
            )
        else:
            with open(status_file_path, "rb") as f:
                encoded = f.read()

            json_bytes = base64.b64decode(encoded)
            status_dict = json.loads(json_bytes.decode("utf-8"))

        migration_flags = load_migration_flags(status_dict.get("migration_flags", []))
        migration_flags = run_migrations(root_path, migration_flags, status_dict=status_dict)

        # Load resources
        resources, not_loaded_resources, slim_resources = cls._load_resources_from_status_dict(
            status_dict
        )

        last_updated_str = status_dict.get("last_updated")
        if last_updated_str:
            last_updated = datetime.fromisoformat(last_updated_str)
        else:
            last_updated = datetime.now()

        return cls(
            region=config_dict.get("region", ""),
            account_id=config_dict.get("account_id", ""),
            project_id=config_dict.get("project_id", ""),
            resources=resources,
            root_path=root_path,
            last_updated=last_updated,
            file_structure_info={},
            slim_resources=slim_resources,
            branch_id=status_dict.get("branch_id", "main"),
            project_name=config_dict.get("project_name") or status_dict.get("project_name"),
            account_name=config_dict.get("account_name") or status_dict.get("account_name"),
            _not_loaded_resources=not_loaded_resources,
            _migration_flags=migration_flags,
            rtc_metadata=status_dict.get("rtc_metadata"),
        )

    def to_dict(self) -> dict:
        """Convert dataclass to a dictionary for serialization"""
        return {
            "region": self.region,
            "account_id": self.account_id,
            "project_id": self.project_id,
            "resources": {
                RESOURCE_CLASS_TO_NAME[rt]: {
                    r_id: resource_utils.resource_to_dict(r) for r_id, r in rs.items()
                }
                for rt, rs in self.resources.items()
            },
            "slim_resources": [r.to_dict() for r in self.slim_resources or []],
            "last_updated": (self.last_updated.isoformat() if self.last_updated else None),
            "file_structure_info": self.file_structure_info,
            "branch_id": self.branch_id,
            "project_name": self.project_name,
            "account_name": self.account_name,
            "migration_flags": [flag.value for flag in self._migration_flags]
            if self._migration_flags
            else [],
            "rtc_metadata": self.rtc_metadata or {},
        }

    @classmethod
    def from_dict(cls, data: dict, root_path: str) -> "AgentStudioProject":
        """Load whole project class from a dictionary"""
        migration_flags = load_migration_flags(data.get("migration_flags", []))
        migration_flags = run_migrations(root_path, migration_flags, status_dict=data)

        resources, not_loaded_resources, slim_resources = cls._load_resources_from_status_dict(data)

        file_structure_info = cls.compute_file_structure_info(resources)

        return cls(
            region=data.get("region", ""),
            account_id=data.get("account_id", ""),
            project_id=data.get("project_id", ""),
            resources=resources,
            root_path=root_path,
            last_updated=datetime.fromisoformat(data.get("last_updated", "1970-01-01T00:00:00")),
            file_structure_info=file_structure_info,
            branch_id=data.get("branch_id", "main"),
            project_name=data.get("project_name"),
            account_name=data.get("account_name"),
            _migration_flags=migration_flags,
            _not_loaded_resources=not_loaded_resources,
            slim_resources=slim_resources,
            rtc_metadata=data.get("rtc_metadata"),
        )

    @staticmethod
    def compute_file_structure_info(
        resources: ResourceMap,
    ) -> dict[str, dict[str, str]]:
        """Compute file structure info for the project"""

        # For each file in the project, we want to store:
        # - file path
        # - resource type
        # - resource id
        # - resource name
        # - hash of the file contents

        file_structure_info = {}
        for resource_type, resource_dict in resources.items():
            for resource in resource_dict.values():
                file_path = resource.file_path
                file_hash = resource.compute_hash()
                file_structure_info[file_path] = {
                    "type": RESOURCE_CLASS_TO_NAME[resource_type],
                    "resource_id": resource.resource_id,
                    "resource_name": resource.name,
                    "hash": file_hash,
                }

        return file_structure_info

    @classmethod
    def init_project(
        cls,
        base_path: str,
        region: str,
        account_id: str,
        project_id: str,
        project_name: str = None,
        account_name: str = None,
        format: bool = False,
        projection_json: Optional[dict[str, Any]] = None,
        on_save: Callable[[int, int], None] | None = None,
    ) -> tuple["AgentStudioProject", dict[str, Any]]:
        """Get project from the Agent Studio Interactor

        Args:
            base_path (str): The base path where the project will be saved
            region (str): The region of the project
            account_id (str): The account ID of the project
            project_id (str): The project ID
            project_name (str): The human-readable project name
            account_name (str): The human-readable account/workspace name
            format (bool): If True, format resources after pulling
            projection_json (dict[str, Any]): A dictionary containing the projection
                If provided, the projection will be used instead of fetching it from the API.
            on_save: Optional callback invoked with (current, total)
                during the resource save loop.

        Returns:
            AgentStudioProject: An instance of AgentStudioProject with functions loaded
            dict[str, Any]: The projection data
        """

        account_path = os.path.join(base_path, account_id)
        project_path = os.path.join(account_path, project_id)

        project = cls(
            region=region,
            account_id=account_id,
            project_id=project_id,
            root_path=project_path,
            resources={},
            last_updated=datetime.now(),
            branch_id="main",
            project_name=project_name,
            account_name=account_name,
            _migration_flags=get_all_migration_flags(),
        )

        try:
            project.resources, slim_resources, projection = project.api_handler.pull_resources(
                projection_json=projection_json
            )
        except ValueError:
            if os.path.exists(project_path):
                shutil.rmtree(project_path)
            if os.path.exists(account_path) and not os.listdir(account_path):
                shutil.rmtree(account_path)
            raise

        project._check_no_duplicate_resource_paths(project.resources)

        resource_mappings: list[ResourceMapping] = (
            project._make_resource_mappings(project.resources) + slim_resources
        )

        all_resources = project.all_resources
        total = len(all_resources)

        MultiResourceYamlResource._file_cache.clear()

        for i, resource in enumerate(all_resources, 1):
            if on_save:
                on_save(i, total)
            is_multi = isinstance(resource, MultiResourceYamlResource)
            resource.save(
                project_path,
                resource_mappings=resource_mappings,
                resource_name=resource.name,
                format=format,
                save_to_cache=is_multi,
            )

        MultiResourceYamlResource.write_cache_to_file()
        MultiResourceYamlResource._file_cache.clear()

        project.save_config(write_project_yaml=True)

        utils.export_decorators(DECORATORS, project_path)
        utils.save_imports(project_path)

        return project, projection

    def save_config(self, write_project_yaml: bool = False) -> None:
        """Save the project configuration to a file

        Args:
            write_project_yaml: If True, write project.yaml file. Defaults to False.
        """
        status_file_path = os.path.join(self.root_path, STATUS_FILE)

        self.last_updated = datetime.now()
        status_dict = self.to_dict()

        json_bytes = json.dumps(status_dict).encode("utf-8")
        encoded = base64.b64encode(json_bytes)
        os.makedirs(os.path.dirname(status_file_path), exist_ok=True)

        with open(status_file_path, "wb") as f:
            f.write(encoded)

        if write_project_yaml:
            config_file_path = os.path.join(self.root_path, PROJECT_CONFIG_FILE)
            config_dict = self.build_project_config()
            with open(config_file_path, "w", encoding="utf-8") as f:
                yaml_content = resource_utils.dump_yaml(config_dict)
                f.write(yaml_content)

    def load_project(
        self,
        preserve_not_loaded_resources: bool = False,
        projection_json: Optional[dict[str, Any]] = None,
    ) -> tuple[dict[str, list["Resource"]], dict[str, Any]]:
        """Load the current state of project on Agent Studio into memory.

        Pulls resources from the API (or a projection dict), updates in-memory
        state and the status file, but does **not** touch working-tree files.

        Args:
            preserve_not_loaded_resources: If True, retain the current
                _not_loaded_resources value across the load (used when reloading
                for comparison without affecting local state).
            projection_json: If set, build resources from this projection dict
                instead of fetching from the API (same shape as a sourcerer projection).

        Returns:
            A tuple of (resources dict, projection dict).
        """
        resources, slim_resources, projection = self.api_handler.pull_resources(
            projection_json=projection_json
        )
        self._check_no_duplicate_resource_paths(resources)

        self.resources = resources
        self.slim_resources = slim_resources
        self.file_structure_info = self.compute_file_structure_info(resources)
        if not preserve_not_loaded_resources:
            self._not_loaded_resources = []

        if projection_json is None:
            self.branch_id = self.api_handler.branch_id

        self.save_config()
        return resources, projection

    def fetch_project(
        self,
        branch_name: Optional[str] = None,
        projection_json: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Fetch the latest remote state, optionally switching branch first.

        Handles branch switching then delegates to ``load_project``.

        Args:
            branch_name: If provided, switch the API context to this branch
                before fetching.  Raises ``ValueError`` if the branch does not
                exist.
            projection_json: If set, build resources from this projection dict
                instead of fetching from the API.

        Returns:
            The projection dict.
        """
        if branch_name is not None:
            branches = self.api_handler.get_branches()
            if branch_name not in branches:
                raise ValueError(f"Branch '{branch_name}' does not exist.")
            branch_id = branches[branch_name]["branchId"]
            self.branch_id = branch_id
            self.api_handler.switch_branch(branch_id)

        _, projection = self.load_project(projection_json=projection_json)
        return projection

    @staticmethod
    def list_templates(region: str) -> list[dict[str, Any]]:
        """List available template projects for a region.

        Args:
            region: The region to query.

        Returns:
            list[dict[str, Any]]: A list of template project summaries.
        """
        return AgentStudioInterface.list_template_projects(region)

    def load_template(self, region: str, template_id: str) -> None:
        """Load a template into the project.

        Writes template resources to disk without updating the tracked state,
        so the next ``poly push`` detects the template files as changes.
        """
        template_resources, template_slim_resources = AgentStudioInterface.get_template_resources(
            template_id, region
        )

        self._not_loaded_resources = []
        self.slim_resources = template_slim_resources
        self.save_config()

        # Delete only ADK-managed resource files, leaving non-ADK files intact.
        for resource_class in RESOURCE_NAME_TO_CLASS.values():
            for path in self._sort_paths_for_reverse_deletion(
                resource_class.discover_resources(self.root_path), resource_class
            ):
                resource_class.delete_resource(path)

        # Empty original_resources so all template resources are treated as new
        # and saved directly, bypassing the three-way merge.
        empty_resources: ResourceMap = {}
        self._update_pulled_resources(
            original_resources=empty_resources,
            incoming_resources=template_resources,
            force=True,
            original_slim_resources=[],
            incoming_slim_resources=template_slim_resources,
        )

    def pull_project(
        self,
        force: bool = False,
        format: bool = False,
        projection_json: Optional[dict[str, Any]] = None,
        on_save: Callable[[int, int], None] | None = None,
    ) -> tuple[list[str], dict[str, Any]]:
        """Pull the project configuration from the Agent Studio Interactor.

        If there are local changes, it will merge them with the incoming changes.
        If there are merge conflicts, it will return a list of files with conflicts.
        If force is True, it will overwrite local changes without merging and delete
            any local resources that are not in the remote project.
        If the resource does not exist locally, it will save it directly.
        If the resource has been removed from the project, it will delete the local
            file.

        Args:
            force (bool): If True, overwrite local changes.
            format (bool): If True, format the resource before saving.

        Returns:
            list[str]: A list of file names with merge conflicts.
            dict[str, Any]: The projection data
        """

        # -------
        # Pull resources
        # -------

        incoming_resources, slim_resources, projection = self.api_handler.pull_resources(
            projection_json=projection_json
        )
        # Only update branch id if we used the API to pull the resources
        if projection_json is None:
            self.branch_id = self.api_handler.branch_id

        self._check_no_duplicate_resource_paths(incoming_resources)
        # -------
        # Update resources
        # -------

        files_with_conflicts = self._update_pulled_resources(
            original_resources=self.resources,
            incoming_resources=incoming_resources,
            force=force,
            format=format,
            on_save=on_save,
            original_slim_resources=self.slim_resources,
            incoming_slim_resources=slim_resources,
        )

        # -------
        # Deal with empty flow folders
        # -------

        flow_folder = os.path.join(self.root_path, "flows")
        if os.path.exists(flow_folder):
            self._delete_empty_folders(flow_folder)

        # Save the updated project configuration
        self.resources = incoming_resources
        self.slim_resources = slim_resources

        # Update file_structure_info
        self.file_structure_info = self.compute_file_structure_info(incoming_resources)

        # Delete all new resources
        if force:
            self._delete_new_resources()

        utils.export_decorators(DECORATORS, self.root_path)
        utils.save_imports(self.root_path)
        self.save_config()

        return files_with_conflicts, projection

    def pull_project_from_env(self, env: str = "sandbox", format: bool = False) -> list[str]:
        """Pull resources from a named environment (live / pre-release / sandbox) and apply
        them as a force-overwrite, discarding any local changes.

        NB: Can potentially make more modular to avoid duplication of pull_project,
        currently leaving as is for stability.

        Raises ValueError if no active deployment exists for the requested environment.

        Args:
            env (str): Target environment name — "live", "pre-release", or "sandbox".
            format (bool): If True, format resources after writing.

        Returns:
            list[str]: Always empty (force overwrite produces no conflicts).
        """
        incoming_resources, slim_resources = self.get_remote_resources_by_name(env)
        if not incoming_resources:
            raise ValueError(f"No resources returned from environment '{env}'.")
        self.branch_id = self.api_handler.branch_id

        self._check_no_duplicate_resource_paths(incoming_resources)

        self._delete_all_local_resources()

        files_with_conflicts = self._update_pulled_resources(
            original_resources=self.resources,
            incoming_resources=incoming_resources,
            force=True,
            format=format,
            on_save=None,
            original_slim_resources=self.slim_resources,
            incoming_slim_resources=slim_resources,
        )
        self.slim_resources = slim_resources

        utils.export_decorators(DECORATORS, self.root_path)
        utils.save_imports(self.root_path)

        return files_with_conflicts

    def _delete_all_local_resources(self) -> None:
        """Delete every local resource file, leaving a clean slate."""
        discovered = self.discover_local_resources()
        pronunciations: list[str] = []
        for resource_class, file_paths in discovered.items():
            if resource_class is Pronunciation:
                pronunciations.extend(file_paths)
            else:
                for file_path in file_paths:
                    resource_class.delete_resource(file_path)

        for file_path in self._sort_paths_for_reverse_deletion(pronunciations, Pronunciation):
            Pronunciation.delete_resource(file_path)

        for entry in os.listdir(self.root_path):
            entry_path = os.path.join(self.root_path, entry)
            if os.path.isdir(entry_path) and entry not in {"_gen", ".git"}:
                self._delete_empty_folders(entry_path)

    def _delete_new_resources(self) -> None:
        """Delete locally-new resources that don't exist on the remote."""
        new_resources, _, _ = self.find_new_kept_deleted(self.discover_local_resources())
        pronunciations = []
        for resource_mapping in new_resources:
            # Pronunciation uses position as a "name" — deleting out of order
            # effectively "changes" the name, causing some resources not to be deleted.
            if resource_mapping.resource_type == Pronunciation:
                pronunciations.append(resource_mapping.file_path)
            else:
                resource_mapping.resource_type.delete_resource(resource_mapping.file_path)

        for file_path in self._sort_paths_for_reverse_deletion(pronunciations, Pronunciation):
            Pronunciation.delete_resource(file_path)

    @staticmethod
    def _delete_empty_folders(folder_path: str) -> None:
        """Delete empty flow folders in the given path recursively."""
        if not os.path.isdir(folder_path):
            return

        # Recursively delete empty subfolders
        for subfolder in os.listdir(folder_path):
            subfolder_path = os.path.join(folder_path, subfolder)
            AgentStudioProject._delete_empty_folders(subfolder_path)

        # If the folder is empty after deleting subfolders, delete it
        if not os.listdir(folder_path):
            logger.info(f"Deleting empty folder: {folder_path}")
            os.rmdir(folder_path)

    @staticmethod
    def _sort_paths_for_reverse_deletion(
        paths: set[str] | list[str], resource_type: type[Resource]
    ) -> list[str]:
        """Return paths in the order they should be deleted (highest index first).

        For Pronunciation, uses the integer position segment so indices 10, 11, ...
        come before 9. Other multi-resource types use lexicographic path order.
        """
        if resource_type is Pronunciation:
            return sorted(
                paths,
                key=lambda p: int(_parse_multi_resource_path(p)[1][-1]),
                reverse=True,
            )
        return sorted(paths, reverse=True)

    def _check_no_duplicate_resource_paths(
        self,
        resources: ResourceMap,
    ) -> None:
        """Check that there are no duplicate resource file paths in the given resources.

        Args:
            resources (ResourceMap): A dictionary mapping resource types to
                dictionaries of resource IDs and Resource instances.

        Raises:
            ValueError: If duplicate resource file paths are found.
        """
        seen_paths = set()
        for resource_type, resource_dict in resources.items():
            for resource in resource_dict.values():
                file_path = resource.get_path(self.root_path)
                if file_path in seen_paths:
                    raise ValueError(
                        f"Duplicate resource file path found: {file_path} for resource {resource.name}\nPlease rename the resource to avoid conflicts."
                    )
                seen_paths.add(file_path)

    def _update_multi_resource_yaml_resources(
        self,
        original_resources: ResourceMap,
        incoming_resources: ResourceMap,
        original_resource_mappings: list[ResourceMapping],
        incoming_resource_mappings: list[ResourceMapping],
        force: bool,
        format: bool = False,
        on_save: Callable[[int, int], None] | None = None,
        progress_offset: int = 0,
        progress_total: int = 0,
    ) -> tuple[list[str], int]:
        """Merge MultiResourceYaml resources when pulling

        As files are merged on a per file basis, we must first compute the whole file:
        - From the original resources
        - From the incoming resources
        - From what's currently on disk (read + applying formatting)
        Then perform the merge with that and the current file contents.
        """
        files_with_conflicts = []

        # Merge MultiResourceYaml:
        # Compute original file contents
        original_file_contents = {}
        local_file_paths: dict[type[Resource], list[str]] = {}
        if not force:
            # Get file for original resources
            # To do this, we simulate a revert but only in cache
            # 1. Save all original resources
            # 2. Delete local resources that are not in the original resources
            # 3. Save the cache and reset
            MultiResourceYamlResource._file_cache.clear()
            for resource_type, resources in original_resources.items():
                if not issubclass(resource_type, MultiResourceYamlResource):
                    continue

                # Find local resources
                local_resources_file_paths = resource_type.discover_resources(self.root_path)
                original_resources_file_paths = set()

                for resource in resources.values():
                    original_resources_file_paths.add(resource.get_path(self.root_path))
                    resource.save(
                        self.root_path,
                        resource_name=resource.name,
                        resource_mappings=original_resource_mappings,
                        format=format,
                        save_to_cache=True,
                    )

                # Delete local resources that are not in the original resources
                deleted_file_paths = set(local_resources_file_paths) - original_resources_file_paths
                for file_path in self._sort_paths_for_reverse_deletion(
                    deleted_file_paths, resource_type
                ):
                    resource_type.delete_resource(file_path, save_to_cache=True)

                local_file_paths[resource_type] = local_resources_file_paths

            original_file_contents = {
                file: resource_utils.dump_yaml(top_level_yaml_dict)
                for file, (_, top_level_yaml_dict) in MultiResourceYamlResource._file_cache.items()
            }

        # Compute incoming file contents
        incoming_file_contents = {}
        MultiResourceYamlResource._file_cache.clear()
        for resource_type, resources in incoming_resources.items():
            if not issubclass(resource_type, MultiResourceYamlResource):
                continue

            # If the resource was added locally but not in the original resources,
            # we need to discover the resources on disk
            if resource_type not in local_file_paths:
                local_file_paths[resource_type] = resource_type.discover_resources(self.root_path)

            incoming_file_paths = set()
            for resource in resources.values():
                file_path = resource.get_path(self.root_path)
                incoming_file_paths.add(file_path)
                resource.save(
                    self.root_path,
                    resource_name=resource.name,
                    resource_mappings=incoming_resource_mappings,
                    format=format,
                    save_to_cache=True,
                )
            if (
                self._not_loaded_resources is not None
                and resource_type in self._not_loaded_resources
            ):
                self._not_loaded_resources.remove(resource_type)

            local_resource_file_paths = set(local_file_paths.get(resource_type, []))
            deleted_file_paths = local_resource_file_paths - incoming_file_paths
            for file_path in self._sort_paths_for_reverse_deletion(
                deleted_file_paths, resource_type
            ):
                resource_type.delete_resource(file_path, save_to_cache=True)

            progress_offset += len(resources)
            if on_save:
                on_save(progress_offset, progress_total)

        incoming_file_contents = {
            file: resource_utils.dump_yaml(top_level_yaml_dict)
            for file, (_, top_level_yaml_dict) in MultiResourceYamlResource._file_cache.items()
        }

        # Normalise local resources through resource classes to ensure
        # serialization differences don't cause merge conflicts
        local_file_contents = {}
        MultiResourceYamlResource._file_cache.clear()
        if not force:
            for resource_type, resources in incoming_resources.items():
                if not issubclass(resource_type, MultiResourceYamlResource):
                    continue
                for resource in resources.values():
                    try:
                        mapping = self._make_resource_mapping(resource)
                        local_resource = self.read_local_resource(
                            resource=mapping,
                            resource_mappings=incoming_resource_mappings,
                        )
                        local_resource.save(
                            self.root_path,
                            resource_name=local_resource.name,
                            resource_mappings=incoming_resource_mappings,
                            format=format,
                            save_to_cache=True,
                        )
                    except (FileNotFoundError, ValueError, TypeError):
                        continue

            local_file_contents = {
                file: resource_utils.dump_yaml(top_level_yaml_dict)
                for file, (_, top_level_yaml_dict) in MultiResourceYamlResource._file_cache.items()
            }

            for file in incoming_file_contents:
                if file not in local_file_contents:
                    try:
                        contents = Resource.read_from_file(file)
                        if format:
                            contents = MultiResourceYamlResource.format_resource(
                                contents, file_name=file
                            )
                        local_file_contents[file] = contents
                    except FileNotFoundError:
                        local_file_contents[file] = ""

        # Save and compute merges
        for file, incoming_content in incoming_file_contents.items():
            if force:
                MultiResourceYamlResource.save_to_file(incoming_content, file)
                continue
            original_content = original_file_contents.get(file, "")
            local_content = local_file_contents.get(file, "")
            merged_contents = utils.merge_strings(original_content, local_content, incoming_content)

            if not merged_contents and os.path.exists(file):
                # Delete the file
                os.remove(file)
                continue

            if merged_contents == local_content:
                continue

            if resource_utils.contains_merge_conflict(merged_contents):
                files_with_conflicts.append(file)
            MultiResourceYamlResource.save_to_file(merged_contents, file)
        MultiResourceYamlResource._file_cache.clear()

        # Delete multi-resource types whose entire type is absent from incoming
        for resource_type, original in original_resources.items():
            if not issubclass(resource_type, MultiResourceYamlResource):
                continue
            if resource_type in incoming_resources:
                continue
            if (
                self._not_loaded_resources is not None
                and resource_type in self._not_loaded_resources
            ):
                continue
            deleted_paths = {res.get_path(self.root_path) for res in original.values()}
            for file_path in self._sort_paths_for_reverse_deletion(deleted_paths, resource_type):
                resource_type.delete_resource(file_path, save_to_cache=True)

        # The deletions above only reached the cache. Flush them, then clear: a cached
        # entry carries the pre-write mtime, so anything left behind makes every later
        # read in this process see a file state that is not on disk.
        MultiResourceYamlResource.write_cache_to_file()
        MultiResourceYamlResource._file_cache.clear()

        return files_with_conflicts, progress_offset

    def _update_pulled_resources(
        self,
        original_resources: ResourceMap,
        incoming_resources: ResourceMap,
        force: bool,
        format: bool = False,
        on_save: Callable[[int, int], None] | None = None,
        *,
        original_slim_resources: list[ResourceMapping],
        incoming_slim_resources: list[ResourceMapping],
    ) -> list[str]:
        files_with_conflicts = []

        # Generate resource mappings
        incoming_resource_mappings: list[ResourceMapping] = (
            self._make_resource_mappings(incoming_resources) + incoming_slim_resources
        )

        # If not force, compare with original and local changes
        original_resource_mappings: list[ResourceMapping] = (
            self._make_resource_mappings(original_resources) + original_slim_resources
        )

        # Merging is done on a per file basis.
        # For most resources - a resource is a single file
        # For MultiResourceYamlResources - a resource is a part of a file,
        # So first compute the whole file, then do merge process separately for each file.
        total = sum(len(res) for res in incoming_resources.values())

        multi_conflicts, current = self._update_multi_resource_yaml_resources(
            original_resources=original_resources,
            incoming_resources=incoming_resources,
            original_resource_mappings=original_resource_mappings,
            incoming_resource_mappings=incoming_resource_mappings,
            force=force,
            format=format,
            on_save=on_save,
            progress_offset=0,
            progress_total=total,
        )

        files_with_conflicts.extend(multi_conflicts)

        # For other resources, we follow the usual process
        for resource_type, incoming in incoming_resources.items():
            if issubclass(resource_type, MultiResourceYamlResource):
                continue

            for resource_id, incoming_resource in incoming.items():
                current += 1
                if on_save:
                    on_save(current, total)
                # If force is True, overwrite local changes
                # If the resource is not loaded, save it directly
                if force or (
                    self._not_loaded_resources is not None
                    and resource_type in self._not_loaded_resources
                ):
                    incoming_resource.save(
                        self.root_path,
                        resource_name=incoming_resource.name,
                        resource_mappings=incoming_resource_mappings,
                        format=format,
                    )
                    continue

                file_path = incoming_resource.get_path(self.root_path)
                original_resource = (
                    original_resources.get(resource_type, {}).get(resource_id)
                    if original_resources.get(resource_type) is not None
                    else None
                )

                if original_resource is not None:
                    # Merge the original, local, and incoming contents
                    original_content = original_resource.to_pretty(
                        resource_name=original_resource.name,
                        resource_mappings=original_resource_mappings,
                    )
                    local_file_path = original_resource.get_path(self.root_path)
                else:
                    original_content = ""
                    local_file_path = incoming_resource.get_path(self.root_path)
                try:
                    # Normalise the local resource to ensure formatting differences don't cause unnecessary merge conflicts
                    incoming_resource_mapping = self._make_resource_mapping(incoming_resource)
                    local_resource = self.read_local_resource(
                        resource=incoming_resource_mapping,
                        resource_mappings=incoming_resource_mappings,
                    )
                    local_content = local_resource.to_pretty(
                        resource_name=incoming_resource.name,
                        resource_mappings=incoming_resource_mappings,
                    )
                except FileNotFoundError:
                    # If local file doesn't exist:
                    # If no original content, save the incoming content
                    # If original, assume user deleted it and don't save anything
                    if not original_content:
                        logger.info(
                            f"Resource {incoming_resource.name} does not exist locally, "
                            "saving directly."
                        )
                        incoming_resource.save(
                            self.root_path,
                            resource_name=incoming_resource.name,
                            resource_mappings=incoming_resource_mappings,
                            format=format,
                        )
                    continue
                except Exception:
                    # If can't read file but file exists, use local version
                    local_content = resource_type.read_from_file(local_file_path)

                incoming_content = incoming_resource.to_pretty(
                    resource_name=incoming_resource.name,
                    resource_mappings=incoming_resource_mappings,
                )

                # If formatting is requested, format the original and incoming contents
                if format:
                    incoming_content = resource_type.format_resource(
                        incoming_content,
                        file_name=incoming_resource.name,
                    )
                    if original_content:
                        original_content = resource_type.format_resource(
                            original_content,
                            file_name=original_resource.name,
                        )
                    local_content = resource_type.format_resource(
                        local_content,
                        file_name=incoming_resource.name,
                    )

                merged_contents = utils.merge_strings(
                    original_content, local_content, incoming_content
                )

                if merged_contents == local_content:
                    continue

                if resource_utils.contains_merge_conflict(merged_contents):
                    files_with_conflicts.append(file_path)

                incoming_resource.save_to_file(
                    merged_contents,
                    file_path,
                )

                if (
                    original_resource is not None
                    and original_resource.get_path(self.root_path) != file_path
                ):
                    # If the file path has changed, remove the old file
                    old_file_path = original_resource.get_path(self.root_path)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)

            # Delete resources that are no longer present in the project
            original_files = {
                res.get_path(self.root_path)
                for res in original_resources.get(resource_type, {}).values()
            }
            incoming_files = {res.get_path(self.root_path) for res in incoming.values()}
            deleted_files = set(original_files) - set(incoming_files)
            for file_path in deleted_files:
                resource_type.delete_resource(file_path)

            if (
                self._not_loaded_resources is not None
                and resource_type in self._not_loaded_resources
            ):
                self._not_loaded_resources.remove(resource_type)

        # Delete resources whose entire type is absent from incoming
        for resource_type, original in original_resources.items():
            if resource_type in incoming_resources:
                continue
            if issubclass(resource_type, MultiResourceYamlResource):
                continue
            if (
                self._not_loaded_resources is not None
                and resource_type in self._not_loaded_resources
            ):
                continue
            for resource in original.values():
                resource_type.delete_resource(resource.get_path(self.root_path))

        return files_with_conflicts

    def _stage_commands(
        self,
        new_state: ResourceMap,
        new_resources: ResourceMap,
        updated_resources: ResourceMap,
        deleted_resources: ResourceMap,
    ) -> list[Message]:
        """Stage commands for the project."""

        # Group flow resources together
        # Creating flow config, group all new steps/functions under it and remove from
        # new resources
        push_changes = self._clean_resources_before_push(
            new_state,
            new_resources,
            updated_resources,
            deleted_resources,
        )
        new_resources = push_changes.main.new
        updated_resources = push_changes.main.updated
        deleted_resources = push_changes.main.deleted
        pre_changes = push_changes.pre
        post_changes = push_changes.post

        # Assign positions to new flows
        new_resources, updated_resources = self._assign_flow_positions(
            new_resources,
            updated_resources,
            new_state,
        )

        # Queue new/updated/deleted resources
        commands = self.api_handler.get_queued_commands()
        if pre_changes.new or pre_changes.deleted or pre_changes.updated:
            commands.extend(
                self.api_handler.queue_resources(
                    new_resources=pre_changes.new,
                    deleted_resources=pre_changes.deleted,
                    updated_resources=pre_changes.updated,
                )
            )

        if new_resources or deleted_resources or updated_resources:
            commands.extend(
                self.api_handler.queue_resources(
                    new_resources=new_resources,
                    deleted_resources=deleted_resources,
                    updated_resources=updated_resources,
                )
            )

        if post_changes.new or post_changes.deleted or post_changes.updated:
            commands.extend(
                self.api_handler.queue_resources(
                    new_resources=post_changes.new,
                    deleted_resources=post_changes.deleted,
                    updated_resources=post_changes.updated,
                )
            )

        queue_set_default_commands(
            new_resources,
            updated_resources,
            commands,
            queue_command=lambda command: self.api_handler.queue_command(command),
        )

        return commands

    def push_project(
        self,
        force=False,
        skip_validation=False,
        dry_run=False,
        format=False,
        projection_json: Optional[dict[str, Any]] = None,
    ) -> tuple[bool, str, list[Message]]:
        """Push the project configuration to the Agent Studio Interactor.

        Args:
            force (bool): If True, overwrite remote changes.
            skip_validation (bool): If True, skip local validation.
            dry_run (bool): If True, do not actually push changes.
            format (bool): If True, format the resource before saving.
            projection_json (dict[str, Any]): A dictionary containing the projection
                If provided, the projection will be used instead of fetching it from the API.

        Returns:
            Tuple[bool, str, list[Message]]:
                - Boolean indicating success.
                - String message.
                - List of commands serialized to protobuf.
        """

        if not dry_run:
            # If force, load latest version of the project
            # to compare against
            if force:
                self.load_project(
                    preserve_not_loaded_resources=True, projection_json=projection_json
                )
            # If not force, pull and merge latest version of the project
            else:
                files_with_conflicts, _ = self.pull_project(
                    format=format, projection_json=projection_json
                )

                if files_with_conflicts:
                    conflicts = "\n- ".join(files_with_conflicts)
                    return (
                        False,
                        f"Merge conflicts detected in the following files:\n- {conflicts}\nPlease resolve the conflicts and try again.",
                        [],
                    )

        # Push Algorithm
        # 1. Get new/kept/deleted resources
        new_resource_mappings, kept_resource_mappings, deleted_resource_mappings = (
            self.find_new_kept_deleted(self.discover_local_resources())
        )
        local_resource_mappings = new_resource_mappings + kept_resource_mappings
        # Slim resources have no file to read - they exist only so that references
        # to them still resolve to a name. Keep them out of the list we iterate,
        # and only in the list we resolve references against.
        resource_mappings = local_resource_mappings + self.slim_resources

        if format:
            # format all local resources before pushing
            self._format_resources(local_resource_mappings)

        new_resource_ids: dict[type[Resource], set[str]] = {
            rt: {rm.resource_id for rm in new_resource_mappings if rm.resource_type == rt}
            for rt in set(rm.resource_type for rm in new_resource_mappings)
        }

        # 2. Read all new/kept resources from disk
        new_state: ResourceMap = {}

        for resource_mapping in local_resource_mappings:
            local_resource = self.read_local_resource(
                resource=resource_mapping,
                resource_mappings=resource_mappings,
            )
            new_state.setdefault(resource_mapping.resource_type, {})[
                resource_mapping.resource_id
            ] = local_resource

        # 3. Work out kept resources that have changed
        new_resources: ResourceMap = {}
        updated_resources: ResourceMap = {}
        deleted_resources: ResourceMap = {}

        for resource_type, resources_dict in new_state.items():
            for resource_id, resource in resources_dict.items():
                if resource_id in new_resource_ids.get(resource_type, set()):
                    new_resources.setdefault(resource_type, {})[resource_id] = resource
                    continue

                original_resource_hash = self.file_structure_info.get(resource.file_path, {}).get(
                    "hash"
                )

                has_changed = resource.is_modified(original_resource_hash)

                if has_changed:
                    updated_resources.setdefault(resource_type, {})[resource_id] = resource

        for resource_mapping in deleted_resource_mappings:
            original_resource = self.resources.get(resource_mapping.resource_type, {}).get(
                resource_mapping.resource_id
            )
            deleted_resources.setdefault(resource_mapping.resource_type, {})[
                resource_mapping.resource_id
            ] = original_resource

        # 3.1 Check sub-resources for changes if applicable
        subresource_changes = self._get_updated_subresources(
            new_resources,
            updated_resources,
            self.resources,
        )

        new_resources.update(subresource_changes.new)
        updated_resources.update(subresource_changes.updated)
        deleted_resources.update(subresource_changes.deleted)

        if not (updated_resources or new_resources or deleted_resources):
            return False, "No changes detected", []

        # 4. Validate all resources with new state
        if not skip_validation:
            validation_errors = self.validate_resources(
                resources_dict=new_state, resource_mappings=resource_mappings
            )
            if validation_errors:
                error_messages = "\n".join(validation_errors)
                return False, f"Validation errors detected:\n{error_messages}", []

        commands = self._stage_commands(
            new_state, new_resources, updated_resources, deleted_resources
        )
        if not dry_run:
            success = self.api_handler.send_queued_commands()
            self.branch_id = self.api_handler.branch_id
        else:
            self.api_handler.clear_command_queue()
            success = True

        if not success:
            failed_resources = []
            for resource_dict in [
                new_resources,
                updated_resources,
                deleted_resources,
            ]:
                for resources in resource_dict.values():
                    failed_resources.extend([res.name for res in resources.values()])
            errors_names = "\n-".join(failed_resources)
            return False, f"Failed to push resources: \n-{errors_names}", commands

        if dry_run:
            return True, "Dry run completed. No changes were pushed.", commands
        else:
            self.resources = new_state
            self.file_structure_info = self.compute_file_structure_info(self.resources)
            self.save_config()

        return True, "Resources pushed successfully.", commands

    @staticmethod
    def _assign_flow_positions(
        new_resources: ResourceMap,
        updated_resources: ResourceMap,
        new_state: ResourceMap,
    ) -> ResourceUpdatePair:
        """Assign positions to flows with new/updated steps."""
        for flow_config in new_resources.get(FlowConfig, {}).values():
            if not isinstance(flow_config, FlowConfig):
                raise TypeError(f"Flow config is not a FlowConfig: {flow_config}")
            resource_utils.assign_flow_positions(flow_config.steps, flow_config.start_step)

        # Assign positions to flows with new/updated steps
        updated_flow_ids = set()
        for flow_step in (
            list(new_resources.get(FlowStep, {}).values())
            + list(updated_resources.get(FlowStep, {}).values())
            + list(new_resources.get(FunctionStep, {}).values())
            + list(updated_resources.get(FunctionStep, {}).values())
        ):
            if not isinstance(flow_step, BaseFlowStep):
                raise TypeError(f"Flow step is not a FlowStep: {flow_step}")
            updated_flow_ids.add(flow_step.flow_id)

        for updated_flow_id in updated_flow_ids:
            flow_config = new_state.get(FlowConfig, {}).get(updated_flow_id)
            if not flow_config:
                raise ValueError(f"Flow config not found for flow id: {updated_flow_id}")
            if not isinstance(flow_config, FlowConfig):
                raise TypeError(f"Flow config is not a FlowConfig: {flow_config}")
            flow_steps = [
                step
                for step in (
                    list(new_state.get(FlowStep, {}).values())
                    + list(new_state.get(FunctionStep, {}).values())
                )
                if isinstance(step, BaseFlowStep) and step.flow_id == updated_flow_id
            ]

            resource_utils.assign_flow_positions(flow_steps, flow_config.start_step)

        return new_resources, updated_resources

    @staticmethod
    def _get_updated_subresources(
        new_resources: ResourceMap,
        updated_resources: ResourceMap,
        original_resources: ResourceMap,
    ) -> SubResourceChangeSet:
        """Get updated subresources from new and updated resources.

        Args:
            new_resources (ResourceMap): New resources to be pushed.
            updated_resources (ResourceMap): Updated resources to be pushed.
            original_resources (ResourceMap): Original resources to be pushed.

        Returns:
            SubResourceChangeSet: New, updated, and deleted subresources grouped by type.
        """
        new_subresources: SubResourceMap = {}
        updated_subresources: SubResourceMap = {}
        deleted_subresources: SubResourceMap = {}

        for resource_type, resources_dict in updated_resources.items():
            for resource_id, resource in resources_dict.items():
                new, updated, deleted = resource.get_new_updated_deleted_subresources(
                    old_resource=original_resources[resource_type][resource_id]
                )
                for sub_resource in new:
                    new_subresources.setdefault(type(sub_resource), {})[
                        sub_resource.resource_id
                    ] = sub_resource
                for sub_resource in updated:
                    updated_subresources.setdefault(type(sub_resource), {})[
                        sub_resource.resource_id
                    ] = sub_resource
                for sub_resource in deleted:
                    deleted_subresources.setdefault(type(sub_resource), {})[
                        sub_resource.resource_id
                    ] = sub_resource

        for resource_type, resources_dict in new_resources.items():
            for resource_id, resource in resources_dict.items():
                new, updated, deleted = resource.get_new_updated_deleted_subresources(
                    old_resource=None
                )
                for sub_resource in new:
                    new_subresources.setdefault(type(sub_resource), {})[
                        sub_resource.resource_id
                    ] = sub_resource
                # A new parent can carry update-only sub-resources — e.g. a TestCase's
                # prompt_assertions/tags, applied via set_test_case_assertions (no create
                # proto). Forward updated + deleted too, or they're dropped on create.
                for sub_resource in updated:
                    updated_subresources.setdefault(type(sub_resource), {})[
                        sub_resource.resource_id
                    ] = sub_resource
                for sub_resource in deleted:
                    deleted_subresources.setdefault(type(sub_resource), {})[
                        sub_resource.resource_id
                    ] = sub_resource

        return SubResourceChangeSet(
            new=new_subresources,
            updated=updated_subresources,
            deleted=deleted_subresources,
        )

    def _clean_resources_before_push(
        self,
        state: ResourceMap,
        new_resources: ResourceMap,
        updated_resources: ResourceMap,
        deleted_resources: ResourceMap,
    ) -> PushPhaseChangeSet:
        """Clean resources before pushing to the API.

        On creating a new flow, group flow steps/functions under
        their flow config.

        If new flow has function step as start step, create referencing a dummy default step.
        Then update the flow config to use the new step.

        When deleting a flow, only send a command to delete the flow config,
        not the steps/functions.

        Remove subresource containers from updated resources.

        If a flow step has changed type, delete the old step and create a new one.
        For the start step, use a dummy workaround as we can't delete a start step
            (pre: create empty default_step, use it as start step,
            normal push: update step type and revert it as start step
            post push: delete dummy
        )

        If a function is new or updated and it references a variable, update the variable references.

        Args:
            state (ResourceMap): State of the project after pushes.
            new_resources (ResourceMap): New resources to be pushed.
            updated_resources (ResourceMap): Updated resources to be pushed.
            deleted_resources (ResourceMap): Deleted resources to be pushed.
            resource_mappings (list[ResourceMapping]): List of resource mappings.

        Returns:
            PushPhaseChangeSet: Main, pre-push, and post-push change sets.
        """
        pre_push_new_resources: ResourceMap = {}
        pre_push_updated_resources: ResourceMap = {}
        pre_push_deleted_resources: ResourceMap = {}
        post_push_new_resources: ResourceMap = {}
        post_push_updated_resources: ResourceMap = {}
        post_push_deleted_resources: ResourceMap = {}

        prepush.enable_webchat_channel(
            new_resources,
            pre_push_updated_resources,
            # Lazy lambda: only touch the api_handler property (which saves config
            # as a side effect) if a webchat command is actually queued
            queue_command=lambda command: self.api_handler.queue_command(command),
        )
        prepush.fix_orphaned_variables(
            state,
            new_resources,
            updated_resources,
            deleted_resources,
            current_resources=self.resources,
            make_resource_mappings=self._make_resource_mappings,
        )
        prepush.group_new_flow_resources(
            new_resources, updated_resources, post_push_deleted_resources
        )
        prepush.prune_cascade_deleted_flow_children(deleted_resources)
        prepush.replace_flow_steps_with_dummy_workaround(
            state,
            new_resources,
            updated_resources,
            deleted_resources,
            pre_push_new_resources,
            pre_push_updated_resources,
            post_push_deleted_resources,
            current_resources=self.resources,
        )
        prepush.default_new_variant_attributes(
            new_resources, deleted_resources, current_resources=self.resources
        )
        prepush.fix_conditions_for_deleted_steps(
            new_resources,
            updated_resources,
            deleted_resources,
            current_resources=self.resources,
        )

        prepush.clear_unused_settings_from_flow_step(
            updated_resources,
            current_resources=self.resources,
            queue_command=lambda command: self.api_handler.queue_command(command),
        )

        return PushPhaseChangeSet(
            main=ResourceChangeSet(
                new=new_resources,
                updated=updated_resources,
                deleted=deleted_resources,
            ),
            pre=ResourceChangeSet(
                new=pre_push_new_resources,
                updated=pre_push_updated_resources,
                deleted=pre_push_deleted_resources,
            ),
            post=ResourceChangeSet(
                new=post_push_new_resources,
                updated=post_push_updated_resources,
                deleted=post_push_deleted_resources,
            ),
        )

    def project_status(self) -> tuple[list[str], list[str], list[str], list[str]]:
        """Check the status of the project.

        Returns:
            tuple[list[str], list[str], list[str], list[str]]: A tuple containing four
                lists:
                - List of files with merge conflicts.
                - List of modified files.
                - List of new files.
                - List of deleted files.
        """
        files_with_conflicts: list[str] = []
        modified_files = []

        # Multi-resource files that fail to parse (conflict markers) are collected here so
        # their resources are skipped by the comparison rather than raising or being counted
        # as deleted. Single-file conflicts are caught in the kept loop below.
        new_resources_mappings, kept_resources_mappings, deleted_resources_mappings = (
            self.find_new_kept_deleted(
                self.discover_local_resources(conflict_files=files_with_conflicts),
                conflict_files=files_with_conflicts,
            )
        )

        new_files = [resource.file_path for resource in new_resources_mappings]

        deleted_files = [resource.file_path for resource in deleted_resources_mappings]

        local_resources_mappings = new_resources_mappings + kept_resources_mappings
        local_resources_mappings.extend(self.slim_resources)

        for kept_local_resource_mapping in kept_resources_mappings:
            original_hash = self.file_structure_info.get(
                os.path.relpath(kept_local_resource_mapping.file_path, self.root_path),
                {},
            ).get("hash")

            try:
                local_resource = self.read_local_resource(
                    resource=kept_local_resource_mapping,
                    resource_mappings=local_resources_mappings,
                )
            except resource_utils.MergeConflictError as e:
                files_with_conflicts.extend(e.file_paths)
                continue

            modified = local_resource.is_modified(original_hash)
            if modified:
                modified_files.append(kept_local_resource_mapping.file_path)

        # dedupe: several resources can share one conflicted multi-resource file
        files_with_conflicts = list(dict.fromkeys(files_with_conflicts))

        return files_with_conflicts, modified_files, new_files, deleted_files

    def revert_changes(self, file_paths: list[str] = None) -> list[str]:
        """Revert changes in the project.

        Args:
            file_paths (list[str]): List of specific files to revert. If None, revert all changes.
        """
        reverted_files = []
        resource_mappings = self._make_resource_mappings(self.resources)
        all_files = not file_paths
        for resource in self.all_resources:
            if not all_files and resource.get_path(self.root_path) not in file_paths:
                continue

            resource.save(self.root_path, resource_mappings=resource_mappings)
            reverted_files.append(resource.get_path(self.root_path))

        return reverted_files

    def get_diffs(self, file_paths: list[str] = None) -> dict[str, str]:
        """Get the diffs of all resources in the project.

        Args:
            file_paths (list[str]): List of specific files to get diffs for. If None, diff all.

        Returns:
            dict[str, str]: A dictionary mapping resource file names to their diffs.
        """
        diffs = {}
        conflict_files: list[str] = []
        all_files = not file_paths
        new_resources_mappings, kept_resources_mappings, deleted_resources_mappings = (
            self.find_new_kept_deleted(self.discover_local_resources())
        )
        local_resources_mappings = new_resources_mappings + kept_resources_mappings
        local_resources_mappings.extend(self.slim_resources)

        for local_resource_mapping in kept_resources_mappings:
            if not all_files and file_paths and local_resource_mapping.file_path not in file_paths:
                continue

            original_hash = self.file_structure_info.get(
                os.path.relpath(local_resource_mapping.file_path, self.root_path), {}
            ).get("hash")

            try:
                local_resource = self.read_local_resource(
                    resource=local_resource_mapping, resource_mappings=local_resources_mappings
                )
            except resource_utils.MergeConflictError as e:
                conflict_files.extend(e.file_paths)
                continue

            modified = local_resource.is_modified(original_hash)
            if not modified:
                continue

            original_resource = self.resources.get(type(local_resource), {}).get(
                local_resource.resource_id
            )
            if not original_resource:
                raise ValueError(f"Original resource not found for {local_resource.file_path}")

            if diff := original_resource.get_diff(local_resource):
                diffs[local_resource.file_path] = diff

        for resource_mapping in new_resources_mappings:
            try:
                resource = self.read_local_resource(
                    resource=resource_mapping, resource_mappings=local_resources_mappings
                )
            except resource_utils.MergeConflictError as e:
                conflict_files.extend(e.file_paths)
                continue

            diffs[resource.file_path] = resource_utils.get_diff(
                "",
                resource.read_to_raw(
                    resource.get_path(self.root_path),
                    resource_name=resource.name,
                    resource_mappings=local_resources_mappings,
                ),
            )

        resource_utils.raise_if_merge_conflicts(conflict_files)

        for resource_mapping in deleted_resources_mappings:
            if not all_files and file_paths and resource_mapping.file_path not in file_paths:
                continue

            original_resource = self.resources.get(resource_mapping.resource_type, {}).get(
                resource_mapping.resource_id
            )
            if not original_resource:
                raise ValueError(f"Original resource not found for {resource_mapping.file_path}")
            diffs[resource_mapping.file_path] = resource_utils.get_diff(original_resource.raw, "")

        return diffs

    def get_deployments(
        self, client_env: str = "sandbox"
    ) -> tuple[list[dict[str, Any]], dict[str, str]]:
        """Get the deployments for the project.
        Args:
            client_env (str): The client environment (sandbox, pre-release, live)
                defaults to sandbox
        Returns:
            tuple[list[dict[str, Any]], dict[str, str]]: A tuple containing:
                - list[dict[str, Any]]: A list of deployment information
                - dict[str, str]: A dictionary mapping environment names to deployment hashes
        """
        env_names = {"sandbox", "pre-release", "live"}
        if client_env not in env_names:
            raise ValueError(f"Invalid client environment: {client_env}")

        active_deployments = self.api_handler.get_active_deployments(
            region=self.region,
            account_id=self.account_id,
            project_id=self.project_id,
        )
        active_deployment_hashes = {
            env: deployment.get("version") for env, deployment in active_deployments.items()
        }

        deployments = self.api_handler.get_deployments(
            region=self.region,
            account_id=self.account_id,
            project_id=self.project_id,
            client_env=client_env,
        )

        return deployments, active_deployment_hashes

    def get_remote_resources_by_name(self, name: str) -> tuple[ResourceMap, list[ResourceMapping]]:
        """Resolve and fetch a remote project state by name.
        Supports:
        - **Environments**: sandbox / pre-release / live (active deployments)
        - **Branches**: branch names (event sourcing projects only)
        - **Deployment versions**: version hash prefix (first 9 chars)
        - **Local**: "local" for local resources
        """
        env_names = {"sandbox", "pre-release", "live"}

        # 1) Environment name -> active deployment
        if name in env_names:
            deployments = self.api_handler.get_active_deployments(
                region=self.region,
                account_id=self.account_id,
                project_id=self.project_id,
            )
            deployment_id = (deployments.get(name) or {}).get("deployment_id")
            if not deployment_id:
                logger.error(f"No active deployment found for environment '{name}'.")
                return {}, []
            logger.info(f"Pulling resources from deployment '{deployment_id}' ({name})...")
            return self.api_handler.pull_deployment_resources(deployment_id)

        # 2) Branch name -> branch resources (event sourcing only)
        branches = self.api_handler.get_branches()
        if name in branches:
            branch_id = branches[name]["branchId"]
            branch_api_handler = AgentStudioInterface(
                self.region, self.account_id, self.project_id, branch_id
            )
            logger.info(f"Pulling resources from branch '{name}'...")
            resources, branch_slim_resources, _ = branch_api_handler.pull_resources()
            return resources, branch_slim_resources

        # 3) Deployment version hash prefix -> deployment resources
        version_hash = (name or "")[:9].lower()
        if version_hash:
            deployments, _ = self.get_deployments()
            deployment = next(
                (d for d in deployments if (d.get("version_hash") or "")[:9] == version_hash), {}
            )
            deployment_id = deployment.get("id")
            if deployment_id:
                logger.info(
                    f"Pulling resources from deployment '{deployment_id}' (version {version_hash})..."
                )
                return self.api_handler.pull_deployment_resources(deployment_id)

        # 4) Local resources -> local resources
        if name == "local":
            new_resources_mappings, kept_resources_mappings, _ = self.find_new_kept_deleted(
                self.discover_local_resources()
            )
            local_resources_mappings = new_resources_mappings + kept_resources_mappings
            # Slim resources have no file to read - resolve references against
            # them, but never iterate them looking for one.
            resource_mappings = local_resources_mappings + self.slim_resources
            resources: ResourceMap = {}
            for resource_mapping in local_resources_mappings:
                resource = self.read_local_resource(
                    resource=resource_mapping, resource_mappings=resource_mappings
                )
                resources.setdefault(resource_mapping.resource_type, {})[
                    resource_mapping.resource_id
                ] = resource
            return resources, self.slim_resources

        logger.error(f"Name '{name}' not found in environments, branches, or deployments.")
        return {}, []

    def diff_remote_named_versions(
        self, before_name: str, after_name: str
    ) -> Optional[dict[str, str]]:
        """Compute diffs between two remote project states (branches / envs / deployments)."""
        before_resources, before_slim_resources = self.get_remote_resources_by_name(before_name)
        after_resources, after_slim_resources = self.get_remote_resources_by_name(after_name)

        if not before_resources or not after_resources:
            logger.error(
                "Could not retrieve resources for one or both specified names: "
                f"before={before_name}, after={after_name}"
            )
            return None

        diffs = self.diff_resource_maps(
            before_resources, before_slim_resources, after_resources, after_slim_resources
        )
        if diffs is None:
            logger.info(
                f"No differences detected between names '{before_name}' and '{after_name}'."
            )
        return diffs

    def diff_projections(
        self, before_projection: dict[str, Any], after_projection: dict[str, Any]
    ) -> Optional[dict[str, str]]:
        """Compute diffs between two sourcerer projections without any API calls.

        Empty projections are valid (e.g. diffing a branch against an empty main).
        """
        before_resources, before_slim_resources = load_resources_from_projection(before_projection)
        after_resources, after_slim_resources = load_resources_from_projection(after_projection)
        return self.diff_resource_maps(
            before_resources,
            before_slim_resources,
            after_resources,
            after_slim_resources,
        )

    def diff_resource_maps(
        self,
        before_resources: ResourceMap,
        before_resource_slim_mappings: list[ResourceMapping],
        after_resources: ResourceMap,
        after_resource_slim_mappings: list[ResourceMapping],
    ) -> Optional[dict[str, str]]:
        """Compute per-file diffs between two in-memory resource maps.

        Returns a mapping of file path to unified diff, or None when the two
        states render identically.
        """
        before_resources_by_path: dict[tuple[ResourceType, str], Resource] = {}
        for resource_type, resources_dict in before_resources.items():
            for resource_id, resource in resources_dict.items():
                before_resources_by_path[(resource_type, resource.file_path)] = resource

        after_resources_by_path: dict[tuple[ResourceType, str], Resource] = {}
        for resource_type, resources_dict in after_resources.items():
            for resource_id, resource in resources_dict.items():
                after_resources_by_path[(resource_type, resource.file_path)] = resource

        before_resource_mappings = (
            self._make_resource_mappings(before_resources) + before_resource_slim_mappings
        )
        after_resource_mappings = (
            self._make_resource_mappings(after_resources) + after_resource_slim_mappings
        )

        diffs: dict[str, str] = {}

        all_resource_paths = set(before_resources_by_path.keys()) | set(
            after_resources_by_path.keys()
        )

        for resource_key in all_resource_paths:
            before_resource = before_resources_by_path.get(resource_key)
            after_resource = after_resources_by_path.get(resource_key)

            if before_resource and after_resource:
                before_pretty = before_resource.to_pretty(
                    resource_mappings=before_resource_mappings
                )
                after_pretty = after_resource.to_pretty(resource_mappings=after_resource_mappings)
                if before_pretty != after_pretty:
                    diffs[before_resource.file_path] = resource_utils.get_diff(
                        before_pretty, after_pretty
                    )
            elif before_resource and not after_resource:
                before_pretty = before_resource.to_pretty(
                    resource_mappings=before_resource_mappings
                )
                diffs[before_resource.file_path] = resource_utils.get_diff(before_pretty, "")
            elif not before_resource and after_resource:
                after_pretty = after_resource.to_pretty(resource_mappings=after_resource_mappings)
                diffs[after_resource.file_path] = resource_utils.get_diff("", after_pretty)

        if not diffs:
            return None

        return diffs

    def _resolve_branch_fork_point(
        self, branch_name: Optional[str] = None
    ) -> tuple[ResourceMap, list[ResourceMapping], ResourceMap, list[ResourceMapping]]:
        """Fetch parent (at fork point) and branch (latest) resource maps.

        Args:
            branch_name: Name of the branch. Defaults to the current branch.

        Returns:
            tuple[ResourceMap, list[ResourceMapping], ResourceMap, list[ResourceMapping]]:
                A tuple containing:
                1. The parent's resources at the fork point.
                2. The parent's slim resources.
                3. The branch's latest resources.
                4. The branch's slim resources.

        Raises:
            ValueError: If on main with no branch specified, or the branch
                does not exist.
        """
        current_name, branches = self.get_branches()

        if branch_name:
            if branch_name not in branches:
                raise ValueError(f"Branch '{branch_name}' does not exist.")
            branch_meta = branches[branch_name]
        else:
            if self.branch_id == "main" or current_name is None:
                raise ValueError(
                    "Cannot diff main branch. Switch to a branch or specify a branch name."
                )
            branch_meta = branches[current_name]

        branch_id = branch_meta["branchId"]
        parent_branch_id = branch_meta.get("parentBranchId")
        parent_sequence_raw = branch_meta.get("parentSequence")

        parent_at_sequence: Optional[int] = None
        if parent_sequence_raw is not None:
            try:
                parent_at_sequence = int(parent_sequence_raw)
            except (TypeError, ValueError):
                logger.warning(
                    f"Invalid parentSequence '{parent_sequence_raw}', "
                    "falling back to latest parent projection."
                )

        if parent_at_sequence is None:
            logger.warning(
                "Fork-point sequence unavailable; comparing against latest parent state."
            )

        parent_id = parent_branch_id or "main"
        parent_resources, parent_slim_resources = self.api_handler.pull_branch_resources(
            parent_id, parent_at_sequence
        )
        branch_resources, branch_slim_resources = self.api_handler.pull_branch_resources(branch_id)

        return parent_resources, parent_slim_resources, branch_resources, branch_slim_resources

    def diff_branch(
        self,
        branch_name: Optional[str] = None,
        file_paths: Optional[list[str]] = None,
    ) -> Optional[dict[str, str]]:
        """Compute diffs showing what a branch changed relative to its fork point.

        Args:
            branch_name: Name of the branch to diff. Defaults to the current branch.
            file_paths: When provided, only include diffs for these files.

        Returns:
            A mapping of file path to unified diff text, or None when there
            are no differences.

        Raises:
            ValueError: If on main with no branch specified, or the branch
                does not exist.
        """
        parent_resources, parent_slim_resources, branch_resources, branch_slim_resources = (
            self._resolve_branch_fork_point(branch_name)
        )
        diffs = self.diff_resource_maps(
            parent_resources, parent_slim_resources, branch_resources, branch_slim_resources
        )

        if diffs and file_paths:
            diffs = {fp: d for fp, d in diffs.items() if fp in file_paths}
            if not diffs:
                return None

        return diffs

    def branch_status(
        self, branch_name: Optional[str] = None
    ) -> tuple[list[str], list[str], list[str]]:
        """Categorize files changed on a branch relative to its fork point.

        Args:
            branch_name: Name of the branch. Defaults to the current branch.

        Returns:
            (new_files, modified_files, deleted_files) — lists of file paths.

        Raises:
            ValueError: If on main with no branch specified, or the branch
                does not exist.
        """
        parent_resources, parent_slim_resources, branch_resources, branch_slim_resources = (
            self._resolve_branch_fork_point(branch_name)
        )

        parent_by_path: dict[tuple, Resource] = {}
        for resources_dict in parent_resources.values():
            for resource in resources_dict.values():
                parent_by_path[(type(resource), resource.file_path)] = resource

        branch_by_path: dict[tuple, Resource] = {}
        for resources_dict in branch_resources.values():
            for resource in resources_dict.values():
                branch_by_path[(type(resource), resource.file_path)] = resource

        before_resource_mappings = (
            self._make_resource_mappings(parent_resources) + parent_slim_resources
        )
        after_resource_mappings = (
            self._make_resource_mappings(branch_resources) + branch_slim_resources
        )

        new_files: list[str] = []
        modified_files: list[str] = []
        deleted_files: list[str] = []

        all_keys = set(parent_by_path.keys()) | set(branch_by_path.keys())
        for key in all_keys:
            parent_r = parent_by_path.get(key)
            branch_r = branch_by_path.get(key)

            if parent_r and branch_r:
                if parent_r.to_pretty(
                    resource_mappings=before_resource_mappings
                ) != branch_r.to_pretty(resource_mappings=after_resource_mappings):
                    modified_files.append(branch_r.file_path)
            elif branch_r and not parent_r:
                new_files.append(branch_r.file_path)
            elif parent_r and not branch_r:
                deleted_files.append(parent_r.file_path)

        return new_files, modified_files, deleted_files

    def discover_local_resources(
        self, conflict_files: Optional[list[str]] = None
    ) -> DiscoveredResourcePaths:
        """Return a dict of all discovered resources locally
        Using the resource name as the key

        Args:
            conflict_files (Optional[list[str]]): If provided, files whose discovery hits a
                merge conflict are appended here and that resource type is skipped instead of
                raising. If None, a MergeConflictError propagates.

        Returns:
            DiscoveredResourcePaths: A dictionary mapping resource types to
                lists of discovered resource file paths.
        """
        discovered_resources: DiscoveredResourcePaths = {}
        for resource_class in RESOURCE_NAME_TO_CLASS.values():
            try:
                discovered = resource_class.discover_resources(self.root_path)
            except resource_utils.MergeConflictError as e:
                if conflict_files is None:
                    raise
                conflict_files.extend(e.file_paths)
                continue
            discovered_resources[resource_class] = discovered or []
        return discovered_resources

    def read_local_resource(
        self,
        resource: ResourceMapping,
        resource_mappings: list[ResourceMapping],
        original_resource: Optional[Resource] = None,
    ) -> Resource:
        """Read a local resource from the given resource mapping.

        Args:
            resource (ResourceMapping): The resource mapping information.
            resource_mappings (list[ResourceMapping]): All resource mappings for reference resolution.
            original_resource (Resource): Optional. When provided (e.g. sync re-read), use for
                known_* kwargs instead of looking up by resource.resource_id. This is used to read
                ids/positions for subresources.
        Returns:
            Resource: The resource instance.
        """
        resource_class = resource.resource_type

        additional_kwargs = {}
        if original_resource is None:
            original_resource = self.resources.get(resource_class, {}).get(resource.resource_id)
        # Need to pass parameters for Function resources to extract param ids
        if resource_class == Function:
            additional_kwargs["known_parameters"] = []
            additional_kwargs["known_latency_control"] = {}

            if original_resource:
                if not isinstance(original_resource, Function):
                    raise TypeError(f"Original resource is not a Function: {original_resource}")
                additional_kwargs["known_parameters"] = original_resource.parameters
                additional_kwargs["known_latency_control"] = original_resource.latency_control

        if resource_class == FlowStep:
            additional_kwargs["known_conditions"] = []
            additional_kwargs["known_position"] = None

            if original_resource:
                if not isinstance(original_resource, FlowStep):
                    raise ValueError(f"Original resource is not a FlowStep: {original_resource}")
                additional_kwargs["known_conditions"] = original_resource.conditions
                additional_kwargs["known_position"] = original_resource.position

        if resource_class == FunctionStep:
            additional_kwargs["known_function_id"] = None
            additional_kwargs["known_position"] = None
            additional_kwargs["known_latency_control"] = {}

            if original_resource:
                if not isinstance(original_resource, FunctionStep):
                    raise ValueError(
                        f"Original resource is not a FunctionStep: {original_resource}"
                    )
                additional_kwargs["known_function_id"] = original_resource.function_id
                additional_kwargs["known_position"] = original_resource.position
                additional_kwargs["known_latency_control"] = original_resource.latency_control

        try:
            resource = resource_class.read_local_resource(
                file_path=resource.file_path,
                resource_id=resource.resource_id,
                resource_name=resource.resource_name,
                resource_mappings=resource_mappings,
                **additional_kwargs,
            )
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"File not found for resource {resource.resource_name} at {resource.file_path}"
            ) from e
        except resource_utils.MergeConflictError:
            raise
        except Exception as e:
            raise ValueError(
                f"Error reading resource {resource.resource_name} at {resource.file_path}: {str(e)}"
            ) from e

        return resource

    def find_new_kept_deleted(
        self,
        discovered_resources: dict[type[Resource], list[str]],
        conflict_files: Optional[list[str]] = None,
    ) -> tuple[
        list[ResourceMapping],
        list[ResourceMapping],
        list[ResourceMapping],
    ]:
        """Find new, kept and deleted resources compared to the current project.

        Args:
            discovered_resources (dict[type[Resource], list[str]]): The discovered
                resources to compare against.

        Returns:
            tuple[
                list[ResourceMapping],
                list[ResourceMapping],
                list[ResourceMapping],
            ]: A tuple containing three lists:
                - New resources
                - Kept resources
                - Deleted resources
        """
        deleted_resource_mappings: list[ResourceMapping] = []
        new_resource_mappings: list[ResourceMapping] = []
        kept_resource_mappings: list[ResourceMapping] = []

        # Build a map of flow config paths to flow names
        flow_configs = discovered_resources.get(FlowConfig, {})
        flow_paths_to_names: dict[str, str] = {}
        for flow_config_path in flow_configs:
            flow_config: FlowConfig = self.read_local_resource(
                ResourceMapping(
                    resource_id="temp_id",
                    resource_type=FlowConfig,
                    resource_name="flow_config",
                    file_path=flow_config_path,
                    flow_name="temp_name",
                    resource_prefix=FlowConfig.get_resource_prefix(file_path=flow_config_path),
                ),
                resource_mappings=[],
            )
            flow_paths_to_names[resource_utils.clean_name(flow_config.name)] = flow_config.name

        # Build a map of clean flow folder names to flow IDs (from existing resources)
        flow_paths_to_ids: dict[str, str] = {}
        for flow_id, flow_cfg in self.resources.get(FlowConfig, {}).items():
            flow_paths_to_ids[resource_utils.clean_name(flow_cfg.name)] = flow_id

        # Add to mapping for new flows
        for flow_path in discovered_resources.get(FlowConfig, []):
            flow_name = resource_utils.get_flow_name_from_path(flow_path)
            if resource_utils.clean_name(flow_name) not in flow_paths_to_ids:
                flow_paths_to_ids[resource_utils.clean_name(flow_name)] = self.generate_uuid(
                    FlowConfig
                )

        if not self.file_structure_info:
            self.file_structure_info = self.compute_file_structure_info(self.resources)

        known_files = set(
            os.path.join(self.root_path, file_path) for file_path in self.file_structure_info.keys()
        )
        discovered_files = set()

        for resource_type, resource_files in discovered_resources.items():
            # Build a map of resource name to resource instance for current resources
            for file_path in resource_files:
                discovered_files.add(file_path)

                # Load resource name, flow name, flow id
                resource_name = os.path.splitext(os.path.basename(file_path))[0]

                flow_name = flow_paths_to_names.get(
                    resource_utils.get_flow_name_from_path(file_path),
                )
                flow_id = flow_paths_to_ids.get(
                    resource_utils.get_flow_name_from_path(file_path),
                )

                if resource_type == FlowStep:
                    flow_step: FlowStep = self.read_local_resource(
                        ResourceMapping(
                            resource_id="temp_id",
                            resource_type=FlowStep,
                            resource_name=resource_name,
                            file_path=file_path,
                            flow_name=flow_name,
                            resource_prefix=resource_type.get_resource_prefix(file_path=file_path),
                        ),
                        resource_mappings=[],
                    )
                    resource_name = flow_step.name

                if resource_type == FlowConfig:
                    resource_name = flow_name

                # Resource name in file path is cleaned, so we need to get the original name
                if (
                    issubclass(resource_type, MultiResourceYamlResource)
                    or resource_type == Topic
                    or resource_type == ChildTopic
                ):
                    resource = self.read_local_resource(
                        ResourceMapping(
                            resource_id="temp_id",
                            resource_type=resource_type,
                            resource_name=resource_name,
                            file_path=file_path,
                            flow_name=flow_name,
                            resource_prefix=resource_type.get_resource_prefix(file_path=file_path),
                        ),
                        resource_mappings=[],
                    )
                    resource_name = resource.name

                if file_path in known_files:
                    resource_info = self.file_structure_info.get(
                        os.path.relpath(file_path, self.root_path)
                    )
                    if not resource_info:
                        raise ValueError(f"Resource info not found for {file_path}")

                    kept_resource_mappings.append(
                        ResourceMapping(
                            resource_id=resource_info["resource_id"],
                            resource_type=resource_type,
                            resource_name=resource_name,
                            file_path=file_path,
                            flow_name=flow_name,
                            resource_prefix=resource_type.get_resource_prefix(file_path=file_path),
                            flow_id=flow_id,
                        )
                    )

                else:
                    # Compute new resource ID
                    resource_id = self.generate_uuid(resource_type)

                    if resource_type == Document:
                        resource_id = os.path.basename(file_path).upper()

                    if resource_type in (FlowStep, FunctionStep):
                        resource_id = f"{flow_id}_{resource_id}"

                    if resource_type == FlowConfig:
                        resource_id = flow_id

                    new_resource_mappings.append(
                        ResourceMapping(
                            resource_id=resource_id,
                            resource_type=resource_type,
                            resource_name=resource_name,
                            file_path=file_path,
                            flow_name=flow_name,
                            flow_id=flow_id,
                            resource_prefix=resource_type.get_resource_prefix(file_path=file_path),
                        )
                    )

        # Resources belonging to a conflicted (unparseable) file can't be enumerated, so
        # they must not be counted as deleted just because discovery skipped them.
        conflict_prefixes = tuple(f"{cf}{os.sep}" for cf in (conflict_files or []))

        deleted_file_paths = known_files - discovered_files
        for file_path in deleted_file_paths:
            if file_path in (conflict_files or []) or file_path.startswith(conflict_prefixes):
                continue
            resource_info = self.file_structure_info[os.path.relpath(file_path, self.root_path)]
            if resource_info["type"] not in RESOURCE_NAME_TO_CLASS:
                continue
            resource_type = RESOURCE_NAME_TO_CLASS[resource_info["type"]]

            # Don't consider a resource "deleted" if it was not loaded from the status file.
            if (
                self._not_loaded_resources is not None
                and resource_type in self._not_loaded_resources
            ):
                continue

            resource_id = resource_info["resource_id"]
            resource_mapping = ResourceMapping(
                resource_id=resource_id,
                resource_type=resource_type,
                resource_name=os.path.splitext(os.path.basename(file_path))[0],
                flow_name=flow_paths_to_names.get(
                    resource_utils.get_flow_name_from_path(file_path),
                ),
                file_path=file_path,
                resource_prefix=resource_type.get_resource_prefix(file_path=file_path),
                flow_id=flow_paths_to_ids.get(
                    resource_utils.get_flow_name_from_path(file_path),
                ),
            )
            deleted_resource_mappings.append(resource_mapping)

        return new_resource_mappings, kept_resource_mappings, deleted_resource_mappings

    @staticmethod
    def generate_uuid(resource_type: type[Resource]) -> str:
        """Generate a new UUID for resource IDs.

        Args:
            resource_type (type[Resource]): The type of resource.

        Returns:
            str: A new UUID string.
        """
        prefix = getattr(resource_type, "resource_id_prefix", None)
        if prefix:
            return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
        return f"{RESOURCE_CLASS_TO_NAME[resource_type].upper()}-{uuid.uuid4().hex[:8]}"

    def get_branches(self) -> tuple[Optional[str], dict[str, dict[str, Any]]]:
        """Get a list of all branches in the (remote) project.

        Returns:
            The current branch name (None if the local branch no longer exists
            on the remote) and a dictionary mapping branch names to their full
            metadata dicts (each containing at least ``branchId``).
        """
        branches = self.api_handler.get_branches()
        current_branch = next(
            (name for name, meta in branches.items() if meta["branchId"] == self.branch_id),
            None,
        )
        return current_branch, branches

    def create_branch(
        self, branch_name: str = None, source_branch_name: Optional[str] = None
    ) -> str:
        """Create a new branch in the project.

        Args:
            branch_name (str): The name of the new branch
            source_branch_name (str): Name of the branch to create the new branch from.
                Defaults to the current branch.

        Returns:
            str: The ID of the newly created branch

        Raises:
            ValueError: If the branch cannot be created due to deployment mode restrictions,
                or source_branch_name does not exist.
        """
        branches = None
        if source_branch_name is not None or self.deployment_mode in (
            DeploymentMode.SIMPLE,
            DeploymentMode.RELEASES_BRANCHES,
        ):
            branches = self.api_handler.get_branches()

        if source_branch_name is not None:
            if source_branch_name not in branches:
                raise ValueError(f"Branch '{source_branch_name}' does not exist.")
            source_branch_id = branches[source_branch_name]["branchId"]
        else:
            source_branch_id = self.branch_id

        if self.deployment_mode == DeploymentMode.SIMPLE:
            if len(branches) >= 2:
                raise ValueError(
                    "Cannot create branch. Only one branch is allowed in simple deployment mode. Please delete/merge existing branches before creating a new one."
                )
        if self.deployment_mode == DeploymentMode.RELEASES:
            if source_branch_id != "main":
                raise ValueError(
                    "Cannot create branch. Branches can only be created from the main branch in releases deployment mode."
                )
        if self.deployment_mode == DeploymentMode.RELEASES_BRANCHES:
            source_branch_meta = next(
                (meta for meta in branches.values() if meta["branchId"] == source_branch_id),
                None,
            )
            if source_branch_meta is None or (
                not source_branch_id == "main"
                and source_branch_meta.get("parentBranchId") != "main"
            ):
                raise ValueError(
                    "Cannot create branch. Branches with depth above 2 are not allowed in releases-branches deployment mode."
                )

        branch_id = self.api_handler.create_branch(branch_name, source_branch_id)
        self.branch_id = branch_id
        self.save_config()
        return branch_id

    def switch_branch(
        self,
        branch_name: str,
        force: bool = False,
        format: bool = False,
        projection_json: Optional[dict[str, Any]] = None,
        on_save: Callable[[int, int], None] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """Switch to a different branch in the project.

        Args:
            branch_name (str): The name of the branch
            force (bool): If True, discard uncommitted changes when switching branches.
            format (bool): If True, format resources after switching branches.
            projection_json (dict[str, Any]): A dictionary containing the projection
                If provided, the projection will be used instead of fetching it from the API.
            on_save: Optional callback invoked with (current, total)
                during the resource save loop.

        Returns:
            bool: True if the switch was successful, False otherwise
            dict[str, Any]: The projection data
        """
        if self.get_diffs() and not force:
            raise ValueError(
                "Cannot switch branches with uncommitted changes. Use --force to switch and discard changes."
            )

        branches = self.api_handler.get_branches()
        if branch_name not in branches:
            raise ValueError(f"Branch {branch_name} does not exist.")
        branch_id = branches[branch_name]["branchId"]
        success = self.api_handler.switch_branch(branch_id)
        projection = {}
        if success:
            self.branch_id = branch_id
            _, projection = self.pull_project(
                force=True, format=format, projection_json=projection_json, on_save=on_save
            )
        return success, projection

    def get_current_branch(self) -> Optional[str]:
        """Get the current branch name.

        Returns:
            Optional[str]: The name of the current branch. None if the current branch does not exist in the remote.
        """
        return self.get_branches()[0]

    @classmethod
    def discover_docs(cls) -> list[str]:
        """Discover the documentation files in the docs directory.

        Returns:
            list[str]: A list of the documentation file names.
        """
        docs_path = os.path.join(os.path.dirname(__file__), "docs")
        if not os.path.exists(docs_path):
            return []
        return [
            file_name.removesuffix(".md")
            for file_name in os.listdir(docs_path)
            if file_name.endswith(".md") and file_name != "docs.md"
        ]

    @classmethod
    def load_docs(cls, document_name: str) -> str:
        """Load the relevant documentation '.md' file for the project."""
        docs_path = os.path.join(os.path.dirname(__file__), "docs", f"{document_name}.md")
        if not os.path.exists(docs_path):
            raise ValueError(f"Documentation file {document_name}.md not found.")

        with open(docs_path, encoding="utf-8") as f:
            content = f.read()
        return content

    # ── Chat ──────────────────────────────────────────────────────

    def create_chat_session(
        self,
        environment: str,
        channel: str,
        variant: Optional[str],
        input_lang: Optional[str] = None,
        output_lang: Optional[str] = None,
        sip_headers: Optional[dict[str, str]] = None,
    ) -> dict:
        """Create a chat session (standard or draft).

        Pass environment="draft" to start a branch draft session, which fetches
        branch deployment info from sourcerer before creating the conversation.

        Args:
            environment (str): The environment to create the chat session in: draft, sandbox, pre-release or live.
            channel (str): The channel to create the chat session in: chat.polyai or webchat.polyai.
            variant (ty.Optional[str]): The variant ID to create the chat session in.
            input_lang (str): Optional. The language code for the input messages, e.g. "en-GB" or "fr-FR".
            output_lang (str): Optional. The language code for the agent's responses, e.g. "en-GB" or "fr-FR".
            sip_headers (dict[str, str]): Optional. Simulated SIP headers exposed to
                project functions through conv.sip_headers.

        Returns:
            dict: API response with conversation_id and initial greeting.

        Raises:
            requests.HTTPError: If any API call fails.
            ValueError: If the branch chat info response is incomplete.
        """
        if environment == "draft":
            chat_info = self.api_handler.get_branch_chat_info(self.branch_id)

            artifact_version = chat_info.get("artifactVersion")
            lambda_deployment_version = chat_info.get("lambdaDeploymentVersion")
            if not artifact_version or not lambda_deployment_version:
                raise ValueError(f"Unexpected response from branch chat info: {chat_info}")

            return AgentStudioInterface.create_draft_chat(
                region=self.region,
                account_id=self.account_id,
                project_id=self.project_id,
                artifact_version=artifact_version,
                lambda_deployment_version=lambda_deployment_version,
                channel=channel,
                variant_id=variant,
                input_lang=input_lang,
                output_lang=output_lang,
                sip_headers=sip_headers,
            )

        return AgentStudioInterface.create_chat(
            region=self.region,
            account_id=self.account_id,
            project_id=self.project_id,
            environment=environment,
            variant_id=variant,
            channel=channel,
            input_lang=input_lang,
            output_lang=output_lang,
            sip_headers=sip_headers,
        )

    def send_message(
        self,
        conversation_id: str,
        text: str,
        environment: str,
        input_lang: str = None,
        output_lang: str = None,
    ) -> dict:
        """Send a message to an active chat conversation.

        Args:
            conversation_id (str): The ID of the conversation to send the message to.
            text (str): The user message text to send.
            environment (str): The environment of the conversation: draft, sandbox, pre-release or live.
            input_lang (str): Optional. The language code of the input message, e.g. "en-GB" or "fr-FR".
            output_lang (str): Optional. The language code for the agent's response, e.g. "en-GB" or "fr-FR".

        Returns:
            dict: API response with the agent's reply.

        Raises:
            requests.HTTPError: If the API call fails.
        """
        if environment == "draft":
            return AgentStudioInterface.send_draft_chat_message(
                region=self.region,
                account_id=self.account_id,
                project_id=self.project_id,
                conversation_id=conversation_id,
                text=text,
                input_lang=input_lang,
                output_lang=output_lang,
            )
        return AgentStudioInterface.send_chat_message(
            region=self.region,
            account_id=self.account_id,
            project_id=self.project_id,
            conversation_id=conversation_id,
            text=text,
            environment=environment,
            input_lang=input_lang,
            output_lang=output_lang,
        )

    def end_chat(
        self,
        conversation_id: str,
        environment: str,
    ) -> dict:
        """End a chat conversation.

        Args:
            conversation_id (str): The ID of the conversation to end.
            environment (str): The environment of the conversation: draft, sandbox, pre-release or live.

        Returns:
            dict: API response.

        Raises:
            requests.HTTPError: If the API call fails.
        """
        return AgentStudioInterface.end_chat(
            region=self.region,
            account_id=self.account_id,
            project_id=self.project_id,
            conversation_id=conversation_id,
            environment=environment,
        )

    @property
    def studio_base_url(self) -> str:
        """Base Agent Studio URL for this project's region."""
        region_link_map = {"uk-1": "uk", "euw-1": "eu", "us-1": "us", "studio": ""}
        short = region_link_map.get(self.region, self.region)
        domain = f"studio.{short}.poly.ai" if short else "studio.poly.ai"
        return f"https://{domain}/{self.account_id}/{self.project_id}"

    def get_conversation_url(self, conversation_id: str) -> str:
        """Build the Studio URL for a conversation.

        Args:
            conversation_id (str): The ID of the conversation to get the URL for.

        Returns:
            str: The URL of the conversation.
        """
        return f"{self.studio_base_url}/conversations/{conversation_id}"

    def _make_resource_mappings(self, resources: ResourceMap) -> list[ResourceMapping]:
        resource_mappings: list[ResourceMapping] = []
        for resources_dict in resources.values():
            for resource in resources_dict.values():
                resource_mappings.append(self._make_resource_mapping(resource))
        return resource_mappings

    def _make_resource_mapping(self, resource: Resource) -> ResourceMapping:
        return ResourceMapping(
            resource_id=resource.resource_id,
            resource_type=type(resource),
            resource_name=resource.name,
            file_path=resource.get_path(self.root_path),
            flow_name=(
                resource.name
                if isinstance(resource, FlowConfig)
                else getattr(resource, "flow_name", None)
            ),
            resource_prefix=resource.get_resource_prefix(file_path=resource.file_path),
            flow_id=(
                resource.resource_id
                if isinstance(resource, FlowConfig)
                else getattr(resource, "flow_id", None)
            ),
        )

    def format_files(
        self, files: list[str] = None, check_only: bool = False
    ) -> tuple[list[str], list[str]]:
        """Format resources in the project.

        Args:
            files (list[str]): List of specific file paths to format. If None, format all resources.
            check_only: If True, do not write; return paths that would change and any errors.

        Returns:
            tuple[list[str], list[str]]: (affected_paths, errors). When check_only, affected_paths
            are paths that would change; otherwise paths that were formatted. errors are messages.
        """
        new_resources_mappings, kept_resources_mappings, _ = self.find_new_kept_deleted(
            self.discover_local_resources()
        )
        all_mappings = new_resources_mappings + kept_resources_mappings
        filtered_resource_mappings: list[ResourceMapping] = [
            m
            for m in all_mappings
            if not files
            or m.file_path in files
            or (
                issubclass(m.resource_type, MultiResourceYamlResource)
                and _parse_multi_resource_path(m.file_path)[0] in files
            )
        ]
        return self._format_resources(filtered_resource_mappings, check_only=check_only)

    def _format_resources(
        self, resource_mappings: list[ResourceMapping], check_only: bool = False
    ) -> tuple[list[str], list[str]]:
        """Format resources in the project.

        Args:
            resource_mappings: List of resource mappings to format.
            check_only: If True, do not write; only report what would change.

        Returns:
            tuple[list[str], list[str]]: (affected_paths, errors). When check_only, affected_paths
            are paths that would change; otherwise paths that were written. errors are messages.
        """
        affected: list[str] = []
        errors: list[str] = []

        # Multi-resource YAML files share a single .yaml file across many virtual
        # sub-paths. Format at the whole-file level instead of per-resource.
        multi_file_paths: set[str] = set()
        regular_mappings: list[ResourceMapping] = []
        for resource_mapping in resource_mappings:
            if issubclass(resource_mapping.resource_type, MultiResourceYamlResource):
                true_path, _ = _parse_multi_resource_path(resource_mapping.file_path)
                multi_file_paths.add(true_path)
            else:
                regular_mappings.append(resource_mapping)

        for file_path in multi_file_paths:
            try:
                content = Resource.read_from_file(file_path)
                formatted_content = MultiResourceYamlResource.format_resource(
                    content, file_name=file_path
                )
                if check_only:
                    if formatted_content.strip() != content.strip():
                        affected.append(file_path)
                elif formatted_content.strip() != content.strip():
                    Resource.save_to_file(formatted_content, file_path)
                    affected.append(file_path)
            except Exception as e:  # noqa: BLE001
                errors.append(f"{file_path}: {e}")

        for resource_mapping in regular_mappings:
            try:
                content = resource_mapping.resource_type.read_from_file(resource_mapping.file_path)
                formatted_content = resource_mapping.resource_type.format_resource(
                    content,
                    file_name=resource_mapping.resource_name,
                )
                if check_only:
                    if formatted_content.strip() != content.strip():
                        affected.append(resource_mapping.file_path)
                elif formatted_content.strip() != content.strip():
                    resource_mapping.resource_type.save_to_file(
                        formatted_content, resource_mapping.file_path
                    )
                    affected.append(resource_mapping.file_path)
            except Exception as e:  # noqa: BLE001
                errors.append(f"{resource_mapping.file_path}: {e}")
        return (affected, errors)

    def validate_project(self) -> list[str]:
        """Validate all resources in the project.

        Returns:
            list[str]: A list of validation error messages.
        """
        # Read local resources
        new_resource_mappings, kept_resource_mappings, _ = self.find_new_kept_deleted(
            self.discover_local_resources()
        )
        local_resource_mappings = new_resource_mappings + kept_resource_mappings

        resource_mappings = local_resource_mappings + self.slim_resources

        resources: ResourceMap = {}
        for resource_mapping in local_resource_mappings:
            local_resource = self.read_local_resource(
                resource=resource_mapping,
                resource_mappings=resource_mappings,
            )
            resources.setdefault(resource_mapping.resource_type, {})[
                resource_mapping.resource_id
            ] = local_resource

        return self.validate_resources(
            resources_dict=resources,
            resource_mappings=resource_mappings,
        )

    @staticmethod
    def validate_resources(
        resources_dict: ResourceMap,
        resource_mappings: list[ResourceMapping],
    ) -> list[str]:
        """Validate all resources in the project.

        Returns:
            list[str]: A list of validation error messages.
        """
        validation_errors = []
        for resource_type, resources in resources_dict.items():
            for resource_id, resource in resources.items():
                try:
                    resource.validate(
                        resource_mappings=resource_mappings,
                    )
                except ValueError as e:
                    # ValueError already contains context, just add file path if missing
                    error_msg = str(e)
                    validation_errors.append(
                        f"Validation error in {resource.file_path}: {error_msg}"
                    )
                except Exception as e:
                    # For other exceptions, provide full context
                    try:
                        resource_name = resource.name
                    except Exception:
                        resource_name = "unknown"
                    try:
                        file_path = resource.file_path
                    except Exception:
                        file_path = "unknown path"
                    validation_errors.append(
                        f"Validation error in {file_path} "
                        f"(resource: {resource_name}, ID: {resource_id}, type: {resource_type.__name__}): "
                        f"{type(e).__name__}: {e}"
                    )

            try:
                # Ensures cleaner error output for collections of resources (e.g., handoffs.yaml)
                resource_type.validate_collection(resources)
            except ValueError as e:
                validation_errors.append(f"Validation error: {e}")

        return validation_errors

    def merge_branch(
        self, message: Optional[str], conflict_resolutions: list[dict[str, Any]] = None
    ) -> tuple[bool, list[dict[str, str]], list[dict[str, str]]]:
        """Merge the current branch into main in the project.

        Args:
            message (Optional[str]): The merge commit message.
            conflict_resolutions (list[dict[str, Any]]): A list of conflict
                resolutions. Each resolution should have:
                - path: List of strings representing the path to the conflicted field (e.g., ["users", "1", "name"])
                - strategy: Resolution strategy - "ours", "theirs", or "base"
                - value: Optional custom value

        Returns:
            bool: True if the merge was successful, False otherwise
            list[dict[str, str]]: A list of conflicts
            list[dict[str, str]]: A list of errors
        """
        branches = self.api_handler.get_branches()
        branch_meta = {meta["branchId"]: meta for meta in branches.values()}
        current_branch_meta = branch_meta.get(self.branch_id)

        if not current_branch_meta:
            raise ValueError(f"Branch {self.branch_id} does not exist.")

        if self.branch_id == "main":
            raise ValueError("Merging from 'main' branch is not supported.")

        if diffs := self.get_diffs():
            raise ValueError(
                f"Cannot merge branch with uncommitted changes, diffs: {list(diffs.keys())}"
            )

        for resolution in conflict_resolutions or []:
            if "path" not in resolution or "strategy" not in resolution:
                raise ValueError(f"Resolution must include 'path' and 'strategy': {resolution}")
            if resolution["strategy"] not in {"ours", "theirs", "base"}:
                raise ValueError(
                    f"Invalid conflict resolution strategy: {resolution['strategy']} for path {resolution['path']}. "
                    f"Must be one of 'ours', 'theirs', or 'base'."
                )

        success, conflicts, errors = self.api_handler.merge_branch(
            message=message, conflict_resolutions=conflict_resolutions
        )
        if success:
            parent_branch_id = current_branch_meta.get("parentBranchId")
            parent_branch_meta = branch_meta.get(parent_branch_id) or {}
            parent_branch_name = parent_branch_meta.get("name")
            if not parent_branch_name:
                logger.warning(
                    f"Could not resolve parent branch for '{self.branch_id}' "
                    f"(parentBranchId={parent_branch_id!r}); defaulting to 'main'."
                )
                parent_branch_name = "main"
            success, _ = self.switch_branch(parent_branch_name, force=True)
            return success, [], []

        return False, conflicts, errors

    def sync_branch(
        self, conflict_resolutions: list[dict[str, Any]] = None
    ) -> tuple[bool, list[dict[str, str]], list[dict[str, str]]]:
        """Sync the current branch with its parent in the project.

        Args:
            conflict_resolutions (list[dict[str, Any]]): A list of conflict
                resolutions. Each resolution should have:
                - path: List of strings representing the path to the conflicted field (e.g., ["users", "1", "name"])
                - strategy: Resolution strategy - "ours", "theirs", or "base"
                - value: Optional custom value

        Returns:
            bool: True if the sync was successful, False otherwise
            list[dict[str, str]]: A list of conflicts
            list[dict[str, str]]: A list of errors
        """
        branches = self.api_handler.get_branches()
        branch_ids = {meta["branchId"] for meta in branches.values()}
        if self.branch_id not in branch_ids:
            raise ValueError(f"Branch {self.branch_id} does not exist.")

        if self.branch_id == "main":
            raise ValueError("Syncing 'main' branch is not supported.")

        if diffs := self.get_diffs():
            raise ValueError(
                f"Cannot sync branch with uncommitted changes, diffs: {list(diffs.keys())}"
            )

        for resolution in conflict_resolutions or []:
            if "path" not in resolution or "strategy" not in resolution:
                raise ValueError(f"Resolution must include 'path' and 'strategy': {resolution}")
            if resolution["strategy"] not in {"ours", "theirs", "base"}:
                raise ValueError(
                    f"Invalid conflict resolution strategy: {resolution['strategy']} for path {resolution['path']}. "
                    f"Must be one of 'ours', 'theirs', or 'base'."
                )

        success, conflicts, errors = self.api_handler.sync_branch(
            conflict_resolutions=conflict_resolutions
        )
        if success:
            self.pull_project(force=True)
            return True, [], []

        return False, conflicts, errors

    def delete_branch(self, branch_name: str) -> bool:
        """Delete a branch in the project.

        Args:
            branch_name (str): The name of the branch to delete.

        Returns:
            bool: True if the branch was deleted successfully, False otherwise
        """
        branches = self.api_handler.get_branches()
        if branch_name not in branches:
            raise ValueError(f"Branch {branch_name} does not exist.")

        if branch_name == "main":
            raise ValueError("Deleting 'main' branch is not supported.")

        branch_id = branches[branch_name]["branchId"]
        success = self.api_handler.delete_branch(branch_id)
        if success and self.branch_id == branch_id:
            self.switch_branch("main", force=True)
        return True

    def sync_ids_with_sandbox(self) -> bool:
        """Sync ids of resources in sandbox into current branch

        Returns:
            bool: True if the sync was successful, False otherwise
        """
        if self.branch_id == "main":
            raise ValueError("Cannot sync ids while on main branch.")

        if self.get_diffs():
            raise ValueError("Cannot sync ids due to uncommitted changes.")

        # Sandbox slim mappings describe what main withheld; local files resolve their
        # references against this branch's own slim mappings, so they are not needed here.
        sandbox_resources, _ = self.get_remote_resources_by_name("main")
        # Build lookup by file path -> Resource
        sandbox_resource_lookup: dict[str, Resource] = {}
        for resources_dict in sandbox_resources.values():
            for resource in resources_dict.values():
                sandbox_resource_lookup[resource.file_path] = resource

        # 1a. Resolve synced FlowConfig ids first, so flow-scoped resources below can
        # translate their (stale, local) flow_id to the id the flow was synced to.
        flow_id_translation: dict[str, str] = {}
        for resources_dict in self.resources.values():
            for resource in resources_dict.values():
                if not isinstance(resource, FlowConfig):
                    continue
                sandbox_version = sandbox_resource_lookup.get(resource.file_path)
                flow_id_translation[resource.resource_id] = (
                    sandbox_version.resource_id if sandbox_version else resource.resource_id
                )

        # 1b. Build sync resource_mappings: use sandbox id when there is a sandbox match by file_path
        sync_mappings: list[ResourceMapping] = []
        for resource_type, resources_dict in self.resources.items():
            for resource_id, resource in resources_dict.items():
                sandbox_version = sandbox_resource_lookup.get(resource.file_path)
                local_flow_id = getattr(resource, "flow_id", None)

                if isinstance(resource, FlowConfig):
                    mapping_resource_id = (
                        sandbox_version.resource_id if sandbox_version else resource.resource_id
                    )
                    mapping_flow_id = mapping_resource_id
                else:
                    mapping_flow_id = flow_id_translation.get(local_flow_id, local_flow_id)
                    if sandbox_version:
                        mapping_resource_id = sandbox_version.resource_id
                    else:
                        # No sandbox counterpart, so this resource was added on the branch and
                        # its composite `{flow_id}_{step_id}` id still carries the pre-sync flow
                        # id. Re-point it at the synced flow id, otherwise the prefix and flow_id
                        # disagree and references (start_step, child_step) cannot be resolved
                        # back to bare step ids.
                        #
                        # Only flow steps embed the flow id in their own id. Flow-scoped
                        # functions also carry a flow_id but keep a standalone id, so
                        # prepending the synced flow id to those would corrupt them.
                        mapping_resource_id = resource.resource_id
                        old_prefix = f"{local_flow_id}_"
                        if (
                            local_flow_id
                            and mapping_flow_id != local_flow_id
                            and issubclass(resource_type, BaseFlowStep)
                            and mapping_resource_id.startswith(old_prefix)
                        ):
                            mapping_resource_id = (
                                f"{mapping_flow_id}_{mapping_resource_id.removeprefix(old_prefix)}"
                            )

                resource_path = resource.get_path(self.root_path)
                sync_mappings.append(
                    ResourceMapping(
                        resource_id=mapping_resource_id,
                        resource_type=resource_type,
                        resource_name=resource.name,
                        file_path=resource_path,
                        flow_name=(
                            resource.name
                            if isinstance(resource, FlowConfig)
                            else getattr(resource, "flow_name", None)
                        ),
                        resource_prefix=resource.get_resource_prefix(file_path=resource.file_path),
                        flow_id=mapping_flow_id,
                    )
                )

        # 2. Re-read all resources with sync mappings (references resolve from mappings)
        branch_by_path: dict[str, tuple[type[Resource], str, Resource]] = {}
        for resource_type, resources_dict in self.resources.items():
            for resource_id, resource in resources_dict.items():
                path = resource.file_path
                branch_by_path[path] = (resource_type, resource_id, resource)

        slim_mappings = self.slim_resources
        new_state: ResourceMap = {}
        for mapping in sync_mappings:
            relative_file_path = os.path.relpath(mapping.file_path, self.root_path)
            original = branch_by_path.get(relative_file_path)
            branch_resource = original[2] if original else None
            sandbox_resource = sandbox_resource_lookup.get(relative_file_path, branch_resource)
            local_resource = self.read_local_resource(
                resource=mapping,
                resource_mappings=[*slim_mappings, *sync_mappings],
                original_resource=sandbox_resource,
            )

            new_state.setdefault(mapping.resource_type, {})[mapping.resource_id] = local_resource

        # 3. Compare new_state vs self.resources by file_path -> new/deleted/updated
        deleted_resources: ResourceMap = {}
        new_resources: ResourceMap = {}
        updated_resources: ResourceMap = {}

        for resource_type, resources_dict in new_state.items():
            for new_id, resource in resources_dict.items():
                path = resource.get_path(self.root_path)
                relative_file_path = os.path.relpath(path, self.root_path)
                branch = branch_by_path.get(relative_file_path)
                if not branch:
                    continue
                _, old_id, branch_resource = branch
                if old_id != new_id:
                    new_resources.setdefault(resource_type, {})[new_id] = resource
                    deleted_resources.setdefault(resource_type, {})[old_id] = branch_resource
                elif resource != branch_resource:
                    updated_resources.setdefault(resource_type, {})[new_id] = resource

        if not (new_resources or deleted_resources or updated_resources):
            logger.info("No resources required to be synced.")
            return True

        subresource_changes = self._get_updated_subresources(
            new_resources,
            updated_resources,
            self.resources,
        )

        new_resources.update(subresource_changes.new)
        updated_resources.update(subresource_changes.updated)
        deleted_resources.update(subresource_changes.deleted)

        if not (updated_resources or new_resources or deleted_resources):
            return True

        self._stage_commands(new_state, new_resources, updated_resources, deleted_resources)
        success = self.api_handler.send_queued_commands()

        self.branch_id = self.api_handler.branch_id

        if not success:
            return False

        self.resources = new_state
        self.file_structure_info = self.compute_file_structure_info(self.resources)
        self.save_config()

        return True

    def promote_deployment(self, deployment_id: str, target_env: str, message: str) -> bool:
        """Promote a deployment to specified environment.

        Args:
            deployment_id (str): The ID of the deployment to promote.
            target_env (str): The target environment to promote to (pre-release or live)
            message (str, optional): Optional message to include with the promotion

        Returns:
            bool: True if the promotion was successful, False otherwise
        """
        if target_env not in {"pre-release", "live"}:
            raise ValueError("target_env must be either 'pre-release' or 'live'.")
        self.api_handler.promote_deployment(
            region=self.region,
            project_id=self.project_id,
            deployment_id=deployment_id,
            target_env=target_env,
            message=message,
        )
        return True

    def rollback_deployment(self, deployment_id: str, message: str) -> bool:
        """Rollback sandbox/main to a previous deployment.

        Args:
            deployment_id (str): The ID of the deployment to rollback.
            message (str, optional): Optional message to include with the rollback

        Returns:
            bool: True if the rollback was successful, False otherwise
        """
        self.api_handler.rollback_deployment(
            region=self.region,
            project_id=self.project_id,
            deployment_id=deployment_id,
            message=message,
        )
        return True

    # ── Simulation tests ───────────────────────────────────────────────────

    def resolve_tests(self, files: list[str] = None, tags: list[str] = None) -> list["TestCase"]:
        """Resolve which tests match the given criteria.

        Runs all tests by default. Use files or tags to filter.

        Args:
            files: List of specific test file paths to select.
            tags: List of tags to filter by.

        Returns:
            list[TestCase]: The matched test cases.
        """
        tests: dict[str, TestCase] = self.resources.get(TestCase, {})
        matched: list[TestCase] = []
        if tags:
            for test in tests.values():
                if any(tag in test.tags.tags for tag in tags):
                    matched.append(test)
        elif files:
            for test in tests.values():
                if test.file_path in files:
                    matched.append(test)
        else:
            matched = list(tests.values())

        if not matched:
            raise ValueError("No tests found to run based on the provided criteria.")

        return matched

    def trigger_tests(self, test_ids: list[str]) -> dict:
        """Trigger tests for the project.

        Args:
            test_ids: List of test case resource IDs to run.

        Returns:
            dict: API response with test run details.
        """
        if not test_ids:
            raise ValueError("No test IDs provided.")

        return self.api_handler.trigger_test_run(
            self.region,
            self.project_id,
            test_ids,
            self.branch_id,
        )

    def get_test_run(self, test_run_id: str) -> dict:
        """Get a test run by ID, including individual test results.

        Args:
            test_run_id: The test run ID.

        Returns:
            dict: The test run detail response.
        """
        return self.api_handler.get_test_run(self.region, self.project_id, test_run_id)

    def list_test_runs(self, limit: int = 10, offset: int = 0) -> dict:
        """List test runs for the project.

        Args:
            limit: The maximum number of test runs to return.
            offset: The number of test runs to skip before starting to collect the result set.

        Returns:
            dict: The list of test runs.
        """
        return self.api_handler.list_test_runs(
            self.region, self.project_id, limit, offset, branch_id=self.branch_id
        )

    # ── A/B tests ───────────────────────────────────────────────────

    def create_ab_test(
        self, name: str, variant_deployment_id: str, traffic_percentage: int
    ) -> dict:
        """Create a new A/B test for the project.

        Args:
            name: Display name for the test.
            variant_deployment_id: ID of the pre-release variant deployment.
            traffic_percentage: Percentage of traffic routed to variant (0-100).

        Returns:
            dict: The created A/B test record.
        """
        return self.api_handler.create_ab_test(
            region=self.region,
            account_id=self.account_id,
            project_id=self.project_id,
            name=name,
            variant_deployment_id=variant_deployment_id,
            traffic_percentage=traffic_percentage,
        )

    def list_ab_tests(self, limit: int | None = None) -> list[dict]:
        """List A/B tests for the project.

        Args:
            limit: Maximum number of tests to return.

        Returns:
            list[dict]: A list of A/B test records.
        """
        result = self.api_handler.list_ab_tests(
            region=self.region,
            account_id=self.account_id,
            project_id=self.project_id,
            limit=limit,
        )
        return result.get("ab_tests", [])

    def get_active_ab_test(self) -> dict:
        """Get the active A/B test for the project.

        Returns:
            dict: The active A/B test record, or empty dict if none.
        """
        return self.api_handler.get_active_ab_test(
            region=self.region,
            account_id=self.account_id,
            project_id=self.project_id,
        )

    def end_ab_test(self, ab_test_id: str, chosen_deployment_id: str) -> dict:
        """End an A/B test and choose a winner.

        Args:
            ab_test_id: The A/B test ID.
            chosen_deployment_id: Deployment ID to keep (control or variant).

        Returns:
            dict: The ended A/B test record.
        """
        return self.api_handler.end_ab_test(
            region=self.region,
            account_id=self.account_id,
            project_id=self.project_id,
            ab_test_id=ab_test_id,
            chosen_deployment_id=chosen_deployment_id,
        )

    def update_ab_test(self, ab_test_id: str, traffic_percentage: int) -> dict:
        """Update traffic percentage for an A/B test.

        Args:
            ab_test_id: The A/B test ID.
            traffic_percentage: New traffic percentage (0-100).

        Returns:
            dict: The updated A/B test record.
        """
        return self.api_handler.update_ab_test(
            region=self.region,
            account_id=self.account_id,
            project_id=self.project_id,
            ab_test_id=ab_test_id,
            traffic_percentage=traffic_percentage,
        )

    # ── RTC (Real-Time Configuration) ──
    RTC_ENV_TO_DIR = {
        "sandbox": "draft_and_sandbox",
        "pre-release": "pre_release",
        "live": "live",
    }

    def get_rtc_last_updated(self, env: str) -> Optional[str]:
        """Get the stored lastUpdated for an RTC environment."""
        if not self.rtc_metadata:
            return None
        env_meta = self.rtc_metadata.get(env)
        if not env_meta:
            return None
        return env_meta.get("last_updated")

    def set_rtc_last_updated(self, env: str, last_updated: Optional[str]) -> None:
        """Set the lastUpdated for an RTC environment and save."""
        self._update_rtc_metadata(env, last_updated=last_updated)

    def get_rtc_base(self, env: str) -> tuple[Optional[dict], Optional[dict]]:
        """Get the base copies of schema and data for an environment.

        Returns:
            (base_schema, base_data) or (None, None) if not stored.
        """
        if not self.rtc_metadata:
            return None, None
        env_meta = self.rtc_metadata.get(env)
        if not env_meta:
            return None, None
        return env_meta.get("base_schema"), env_meta.get("base_data")

    def set_rtc_base(
        self,
        env: str,
        schema: Optional[dict] = None,
        variables: Optional[dict] = None,
    ) -> None:
        """Set the base copies for an RTC environment.

        Only updates the fields that are provided (not None).
        """
        self._update_rtc_metadata(env, schema=schema, variables=variables)

    def _update_rtc_metadata(
        self,
        env: str,
        last_updated: Optional[str] = None,
        schema: Optional[dict] = None,
        variables: Optional[dict] = None,
    ) -> None:
        """Update RTC metadata for an environment in a single write."""
        if self.rtc_metadata is None:
            self.rtc_metadata = {}
        if env not in self.rtc_metadata:
            self.rtc_metadata[env] = {}
        if last_updated is not None:
            self.rtc_metadata[env]["last_updated"] = last_updated
        if schema is not None:
            self.rtc_metadata[env]["base_schema"] = schema
        if variables is not None:
            self.rtc_metadata[env]["base_data"] = variables
        self.save_config()

    def _rtc_env_dir(self, env: str) -> str:
        """Get the local directory path for an RTC environment."""
        dir_name = self.RTC_ENV_TO_DIR[env]
        return os.path.join(self.root_path, "real_time_configuration", dir_name)

    def rtc_fetch_config(self, env: str) -> dict:
        """Fetch RTC config for an environment from the API.

        Args:
            env: The environment (sandbox, pre-release, live).

        Returns:
            dict: The RTC config with schema, variables, clientEnv, lastUpdated.
        """
        return AgentStudioInterface.get_rtc_config(
            region=self.region,
            project_id=self.project_id,
            client_env=env,
        )

    def rtc_load_local(
        self,
        env: str,
        schema_only: bool = False,
        data_only: bool = False,
    ) -> dict:
        """Load local RTC files for an environment.

        Args:
            env: The environment to load.
            schema_only: If True, only load schema.
            data_only: If True, only load data.

        Returns:
            dict with 'schema' and 'variables' keys (None if not loaded).

        Raises:
            FileNotFoundError: If required files are missing.
            ValueError: If JSON is invalid.
        """
        env_dir = self._rtc_env_dir(env)
        schema_path = os.path.join(env_dir, "schema.json")
        data_path = os.path.join(env_dir, "data.json")

        schema = None
        variables = None

        if not data_only:
            if not os.path.exists(schema_path):
                raise FileNotFoundError(f"schema.json not found at {schema_path}")
            try:
                with open(schema_path, "r", encoding="utf-8") as f:
                    schema = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in {schema_path}: {e}") from e

        if not schema_only:
            if not os.path.exists(data_path):
                raise FileNotFoundError(f"data.json not found at {data_path}")
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    variables = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in {data_path}: {e}") from e

        return {"schema": schema, "variables": variables}

    def check_rtc_drift(self, env: str) -> dict:
        """Check for drift between local and remote RTC config.

        Args:
            env: The environment to check.

        Returns:
            dict with:
                - status: "no_metadata" | "in_sync" | "drifted"
                - remote_config: dict (only when drifted)
                - local_last_updated: str (when metadata exists)
                - remote_last_updated: str (when metadata exists)
        """
        local_last_updated = self.get_rtc_last_updated(env)
        if local_last_updated is None:
            return {"status": "no_metadata"}

        remote_config = self.rtc_fetch_config(env)
        remote_last_updated = remote_config.get("lastUpdated")

        if remote_last_updated == local_last_updated:
            return {
                "status": "in_sync",
                "local_last_updated": local_last_updated,
                "remote_last_updated": remote_last_updated,
            }

        return {
            "status": "drifted",
            "remote_config": remote_config,
            "local_last_updated": local_last_updated,
            "remote_last_updated": remote_last_updated,
        }

    def rtc_pull_env(
        self,
        env: str,
        schema_only: bool = False,
        data_only: bool = False,
    ) -> dict:
        """Pull RTC config for a single environment from the API and write to disk.

        Args:
            env: The environment to pull (sandbox, pre-release, live).
            schema_only: If True, only pull schema.
            data_only: If True, only pull data.

        Returns:
            dict with environment, schema_file, data_file paths.
        """
        config = self.rtc_fetch_config(env)

        env_dir = self._rtc_env_dir(env)
        os.makedirs(env_dir, exist_ok=True)

        schema = config.get("schema") or {}
        variables = config.get("variables") or {}

        schema_path = os.path.join(env_dir, "schema.json")
        data_path = os.path.join(env_dir, "data.json")

        if not data_only:
            utils.write_json_file(schema_path, schema)
        if not schema_only:
            utils.write_json_file(data_path, variables)

        self._update_rtc_metadata(
            env,
            last_updated=config.get("lastUpdated"),
            schema=schema,
            variables=variables,
        )

        result = {"environment": env}
        if not data_only:
            result["schema_file"] = schema_path
        if not schema_only:
            result["data_file"] = data_path
        return result

    def rtc_push_to_api(
        self,
        env: str,
        schema: Optional[dict] = None,
        variables: Optional[dict] = None,
        schema_only: bool = False,
        data_only: bool = False,
    ) -> dict:
        """Push RTC config to the API and update local state.

        Args:
            env: The environment to push to.
            schema: Schema dict to push (None to skip).
            variables: Variables dict to push (None to skip).
            schema_only: If True, only push schema.
            data_only: If True, only push data.

        Returns:
            dict with success status.
        """
        import requests

        last_response = None
        if schema is not None and not data_only:
            try:
                last_response = AgentStudioInterface.put_rtc_schema(
                    region=self.region,
                    project_id=self.project_id,
                    client_env=env,
                    schema=schema,
                )
            except requests.HTTPError as e:
                return {"success": False, "error": str(e), "step": "schema"}

        if variables is not None and not schema_only:
            try:
                last_response = AgentStudioInterface.patch_rtc_variables(
                    region=self.region,
                    project_id=self.project_id,
                    client_env=env,
                    variables=variables,
                )
            except requests.HTTPError as e:
                if last_response and last_response.get("lastUpdated"):
                    self.set_rtc_last_updated(env, last_response["lastUpdated"])
                return {
                    "success": False,
                    "error": f"Schema pushed but variables failed: {e}",
                    "step": "variables",
                }

        base_schema, base_data = self.get_rtc_base(env)
        self._update_rtc_metadata(
            env,
            last_updated=last_response.get("lastUpdated") if last_response else None,
            schema=schema if schema is not None else base_schema,
            variables=variables if variables is not None else base_data,
        )

        env_dir = self._rtc_env_dir(env)
        os.makedirs(env_dir, exist_ok=True)
        if schema is not None:
            utils.write_json_file(os.path.join(env_dir, "schema.json"), schema)
        if variables is not None:
            utils.write_json_file(os.path.join(env_dir, "data.json"), variables)

        return {
            "success": True,
            "environment": env,
            "schema_file": os.path.join(env_dir, "schema.json"),
            "data_file": os.path.join(env_dir, "data.json"),
        }

    def rtc_diff_env(self, env: str) -> dict:
        """Compare local RTC files against remote for one environment.

        Args:
            env: The environment to diff.

        Returns:
            dict with environment, schema changes, data changes.
        """
        env_dir = self._rtc_env_dir(env)
        schema_path = os.path.join(env_dir, "schema.json")
        data_path = os.path.join(env_dir, "data.json")

        if not os.path.exists(schema_path) and not os.path.exists(data_path):
            return {"environment": env, "status": "no_local_files"}

        remote_config = self.rtc_fetch_config(env)
        env_diff: dict = {"environment": env, "schema": [], "data": []}

        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                local_schema = json.load(f)
            remote_schema = remote_config.get("schema") or {}
            env_diff["schema"] = utils.diff_dicts(local_schema, remote_schema)

        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                local_data = json.load(f)
            remote_data = remote_config.get("variables") or {}
            env_diff["data"] = utils.diff_dicts(local_data, remote_data)

        return env_diff

    def rtc_validate_env(self, env: str) -> dict:
        """Validate local RTC data against its schema for one environment.

        Args:
            env: The environment to validate.

        Returns:
            dict with environment, valid status, and any errors.
        """
        env_dir = self._rtc_env_dir(env)
        schema_path = os.path.join(env_dir, "schema.json")
        data_path = os.path.join(env_dir, "data.json")

        if not os.path.exists(schema_path) or not os.path.exists(data_path):
            return {"environment": env, "status": "skipped"}

        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return {"environment": env, "valid": False, "errors": [f"Invalid JSON: {e}"]}

        validation_errors = self.validate_rtc_data(schema, data)
        if validation_errors:
            return {"environment": env, "valid": False, "errors": validation_errors}
        return {"environment": env, "valid": True}

    @staticmethod
    def validate_rtc_data(schema: dict, data: dict) -> list[str]:
        """Validate RTC data against its schema using JSON Schema Draft 7.

        Returns:
            List of validation error messages, empty if valid.
        """
        import jsonschema

        if not schema:
            return []

        try:
            jsonschema.Draft7Validator.check_schema(schema)
        except (jsonschema.SchemaError, jsonschema.exceptions.UnknownType) as e:
            return [f"Invalid schema: {e}"]

        try:
            validator = jsonschema.Draft7Validator(schema)
            errors = sorted(
                validator.iter_errors(data),
                key=lambda e: [str(p) for p in e.absolute_path],
            )
            return [
                f"{'.'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}"
                for e in errors
            ]
        except (jsonschema.SchemaError, jsonschema.exceptions.UnknownType) as e:
            return [f"Invalid schema: {e}"]

    def get_branch_history(self, branch_id: str) -> list[dict[str, Any]]:
        """Get the history of a branch.

        Args:
            branch_id (str): The ID of the branch to get history for.

        Returns:
            list[dict[str, Any]]: A list of commit history entries for the branch.
        """
        return self.api_handler.get_branch_history(branch_id)

    def rename_branch(self, new_branch_name: str) -> bool:
        """Rename the current branch.

        Args:
            new_branch_name (str): The new name for the current branch.

        Returns:
            bool: True if the rename was successful, False otherwise.
        """
        if not new_branch_name:
            raise ValueError("New branch name must be provided.")

        if self.branch_id == "main":
            raise ValueError("Renaming 'main' branch is not supported.")

        branches = self.api_handler.get_branches()

        if new_branch_name in branches:
            raise ValueError(f"Branch {new_branch_name} already exists.")

        success = self.api_handler.rename_branch(new_branch_name=new_branch_name)
        return success

    def list_archived_branches(self) -> list[dict[str, Any]]:
        """List soft-deleted (archived) branches for the project.

        Returns:
            list[dict[str, Any]]: A list of archived branch entries.
        """
        return self.api_handler.list_archived_branches()

    def restore_branch(self, branch_id: str) -> bool:
        """Restore a soft-deleted branch from the archive.

        Identified by id rather than name because archived names are not unique —
        the same branch name can be archived repeatedly. Use
        ``list_archived_branches`` to find the id.

        Args:
            branch_id (str): The branch id of the archived branch to restore.

        Returns:
            bool: True if the branch was restored successfully, False otherwise.
        """
        if not branch_id:
            raise ValueError("Branch id must be provided.")

        archived = self.api_handler.list_archived_branches()
        if not any(branch.get("branchId") == branch_id for branch in archived):
            raise ValueError(
                f"Branch '{branch_id}' not found in archive. "
                "Use 'poly branch list --archived' to see available branches."
            )

        return self.api_handler.restore_branch(branch_id)

    def tag_branch(self, branch_name: str = None) -> bool:
        """Tag the current branch with a new tag.

        Args:
            branch_name (str): The name of the branch to tag. If None, tags the current branch.
        Returns:
            bool: True if the tagging was successful, False otherwise.
        """
        branches = self.api_handler.get_branches()
        if branch_name is None:
            branch_id = self.branch_id
            branch_name = next(
                (name for name, meta in branches.items() if meta["branchId"] == branch_id), None
            )
            if branch_name is None:
                raise ValueError(f"Current branch ID {branch_id} does not exist.")
        else:
            if branch_name not in branches:
                raise ValueError(f"Branch {branch_name} does not exist.")
            branch_id = branches[branch_name]["branchId"]

        if branch_id == "main":
            raise ValueError("Tagging 'main' branch is not supported.")

        success = self.api_handler.tag_branch(branch_id)
        return success

    def untag_branch(self, branch_name: str = None) -> bool:
        """Remove a tag from a branch.

        Args:
            branch_name (str): The name of the branch to untag. If None, untags the current branch.
        Returns:
            bool: True if the untagging was successful, False otherwise.
        """
        branches = self.api_handler.get_branches()
        if branch_name is None:
            branch_id = self.branch_id
            branch_name = next(
                (name for name, meta in branches.items() if meta["branchId"] == branch_id), None
            )
            if branch_name is None:
                raise ValueError(f"Current branch ID {branch_id} does not exist.")
        else:
            if branch_name not in branches:
                raise ValueError(f"Branch {branch_name} does not exist.")
            branch_id = branches[branch_name]["branchId"]

        if branch_id == "main":
            raise ValueError("Untagging 'main' branch is not supported.")

        success = self.api_handler.untag_branch(branch_id)
        return success

    def get_project_info(self) -> dict[str, Any]:
        """Get basic information about the project from the API.

        Returns:
            dict[str, Any]: A dictionary containing project information.
        """
        return self.api_handler.get_project(self.region, self.account_id, self.project_id)

    @property
    def deployment_mode(self) -> DeploymentMode:
        """Get the deployment mode for the project."""
        if self._deployment_mode is None:
            cfg = self.get_project_info().get("config") or {}
            deployment_mode = DeploymentMode(cfg.get("deployment_mode", "releases"))
            if (
                deployment_mode == DeploymentMode.RELEASES_BRANCHES
                and not self.using_simplified_deployments
            ):
                deployment_mode = DeploymentMode.RELEASES
            self._deployment_mode = deployment_mode
        return self._deployment_mode

    @cached_property
    def using_simplified_deployments(self) -> bool:
        """Check if the project is using simplified deployments."""
        flag_enabled = self.api_handler.feature_flag_enabled(
            key="deployment-simplification",
            region=self.region,
            project_id=self.project_id,
            default=False,
        )
        if not flag_enabled:
            return False

        # A project is converged if the main == live
        # Once a project is converged, all deployments will go to live
        # To check, look at most recent deployment in sandbox and live. If it is the same as live, then the project is converged
        live_deployments = self.api_handler.get_deployments(
            self.region, self.account_id, self.project_id, client_env="live"
        )
        sandbox_deployments = self.api_handler.get_deployments(
            self.region, self.account_id, self.project_id, client_env="sandbox"
        )

        live_head = next((d for d in live_deployments if not d.get("deleted", False)), None)
        sandbox_head = next((d for d in sandbox_deployments if not d.get("deleted", False)), None)

        def _parse_created_at(deployment: dict) -> datetime:
            return datetime.strptime(deployment["created_at"], "%a, %d %b %Y %H:%M:%S %Z")

        if live_head is None and sandbox_head is None:
            # No deployments in either environment, consider converged
            return True

        return live_head is not None and (
            sandbox_head is None or _parse_created_at(live_head) >= _parse_created_at(sandbox_head)
        )
