"""Agent Studio project management

Copyright PolyAI Limited
"""

import base64
import json
import logging
import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass, fields
from datetime import datetime
from typing import Any, Optional, TypeAlias

from google.protobuf.message import Message

import poly.resources.resource_utils as resource_utils
import poly.utils as utils
from poly.handlers.interface import (
    AgentStudioInterface,
)
from poly.resources import (
    ApiIntegration,
    AsrSettings,
    BaseFlowStep,
    ChatGreeting,
    ChatStylePrompt,
    Entity,
    ExperimentalConfig,
    FlowConfig,
    FlowStep,
    Function,
    FunctionStep,
    Handoff,
    KeyphraseBoosting,
    MultiResourceYamlResource,
    PhraseFilter,
    Pronunciation,
    Resource,
    ResourceMapping,
    SettingsPersonality,
    SettingsRole,
    SettingsRules,
    SMSTemplate,
    StepType,
    SubResource,
    Topic,
    TranscriptCorrection,
    Variable,
    Variant,
    VariantAttribute,
    VoiceDisclaimerMessage,
    VoiceGreeting,
    VoiceStylePrompt,
)
from poly.resources.resource import _parse_multi_resource_path
from poly.utils import compute_variable_references

logger = logging.getLogger(__name__)

PROJECT_CONFIG_FILE = "project.yaml"
STATUS_FILE = os.path.join("_gen", ".agent_studio_config")
_LEGACY_STATUS_FILE = ".agent_studio_config"


# New resources to be added here
RESOURCE_NAME_TO_CLASS: dict[str, type[Resource]] = {
    "api_integration": ApiIntegration,
    "functions": Function,
    "topics": Topic,
    "personality": SettingsPersonality,
    "role": SettingsRole,
    "rules": SettingsRules,
    "flow_steps": FlowStep,
    "function_steps": FunctionStep,
    "flow_config": FlowConfig,
    "entities": Entity,
    "experimental_config": ExperimentalConfig,
    "sms_templates": SMSTemplate,
    "handoffs": Handoff,
    "variants": Variant,
    "variant_attributes": VariantAttribute,
    "variables": Variable,
    "voice_greeting": VoiceGreeting,
    "voice_style_prompt": VoiceStylePrompt,
    "voice_disclaimer": VoiceDisclaimerMessage,
    "chat_greeting": ChatGreeting,
    "chat_style_prompt": ChatStylePrompt,
    "keyphrase_boosting": KeyphraseBoosting,
    "transcript_corrections": TranscriptCorrection,
    "asr_settings": AsrSettings,
    "phrase_filtering": PhraseFilter,
    "pronunciations": Pronunciation,
}

DECORATORS = ["func_parameter", "func_description", "func_latency_control"]


RESOURCE_CLASS_TO_NAME: dict[type[Resource], str] = {
    v: k for k, v in RESOURCE_NAME_TO_CLASS.items()
}

ResourceType: TypeAlias = type[Resource]
ResourceMap: TypeAlias = dict[ResourceType, dict[str, Resource]]
SubResourceType: TypeAlias = type[SubResource]
SubResourceMap: TypeAlias = dict[SubResourceType, dict[str, SubResource]]
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


@dataclass
class AgentStudioProject:
    """Dataclass representing an Agent Studio Project"""

    region: str
    account_id: str
    project_id: str
    root_path: str
    resources: ResourceMap
    last_updated: datetime
    branch_id: str = None
    _api_handler: AgentStudioInterface = None
    file_structure_info: dict[str, dict[str, str]] = None

    # Store resources that were not loaded from the status file
    # So they aren't considered locally deleted when pushing/pulling
    # before they are saved.
    _not_loaded_resources: list[ResourceType] = None

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
        return {
            "project_id": self.project_id,
            "account_id": self.account_id,
            "region": self.region,
        }

    @classmethod
    def _load_resources_from_status_dict(
        cls, status_dict: dict
    ) -> tuple[ResourceMap, list[ResourceType]]:
        resources: ResourceMap = {}
        not_loaded_resources: list[ResourceType] = []
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
        return resources, not_loaded_resources

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

        # Load resources
        resources, not_loaded_resources = cls._load_resources_from_status_dict(status_dict)

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
            branch_id=status_dict.get("branch_id", "main"),
            _not_loaded_resources=not_loaded_resources,
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
            "last_updated": (self.last_updated.isoformat() if self.last_updated else None),
            "file_structure_info": self.file_structure_info,
            "branch_id": self.branch_id,
        }

    @classmethod
    def from_dict(cls, data: dict, root_path: str) -> "AgentStudioProject":
        """Load whole project class from a dictionary"""
        resources, not_loaded_resources = cls._load_resources_from_status_dict(data)

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
            _not_loaded_resources=not_loaded_resources,
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
            format (bool): If True, format resources after pulling
            projection_json (dict[str, Any]): A dictionary containing the projection
                If provided, the projection will be used instead of fetching it from the API.
            on_save: Optional callback invoked with (current, total)
                during the resource save loop.

        Returns:
            AgentStudioProject: An instance of AgentStudioProject with functions loaded
            dict[str, Any]: The projection data
        """

        base_path = os.path.join(base_path, account_id, project_id)

        project = cls(
            region=region,
            account_id=account_id,
            project_id=project_id,
            root_path=base_path,
            resources={},
            last_updated=datetime.now(),
            branch_id="main",
        )
        project.resources, projection = project.api_handler.pull_resources(
            projection_json=projection_json
        )
        project._check_no_duplicate_resource_paths(project.resources)

        resource_mappings: list[ResourceMapping] = project._make_resource_mappings(
            project.resources
        )

        all_resources = project.all_resources
        total = len(all_resources)

        MultiResourceYamlResource._file_cache.clear()

        for i, resource in enumerate(all_resources, 1):
            if on_save:
                on_save(i, total)
            is_multi = isinstance(resource, MultiResourceYamlResource)
            resource.save(
                base_path,
                resource_mappings=resource_mappings,
                resource_name=resource.name,
                format=format,
                save_to_cache=is_multi,
            )

        MultiResourceYamlResource.write_cache_to_file()
        MultiResourceYamlResource._file_cache.clear()

        project.save_config(write_project_yaml=True)

        utils.export_decorators(DECORATORS, base_path)
        utils.save_imports(base_path)

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
    ) -> None:
        """Load the current state of project on Agent Studio into memory

        This is used when no current resources are loaded.

        Args:
            preserve_not_loaded_resources: If True, retain the current
                _not_loaded_resources value across the load (used when reloading
                for comparison without affecting local state).
            projection_json: If set, build resources from this projection dict
                instead of fetching from the API (same shape as a sourcerer projection).
        """
        resources, _ = self.api_handler.pull_resources(projection_json=projection_json)
        self._check_no_duplicate_resource_paths(resources)

        self.resources = resources
        self.file_structure_info = self.compute_file_structure_info(resources)
        if not preserve_not_loaded_resources:
            self._not_loaded_resources = []
        self.save_config()

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

        incoming_resources, projection = self.api_handler.pull_resources(
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
        )

        # -------
        # Deal with empty flow folders
        # -------

        flow_folder = os.path.join(self.root_path, "flows")
        if os.path.exists(flow_folder):
            self._delete_empty_folders(flow_folder)

        # Save the updated project configuration
        self.resources = incoming_resources

        # Update file_structure_info
        self.file_structure_info = self.compute_file_structure_info(incoming_resources)

        # Delete all new resources
        if force:
            new_resources, _, _ = self.find_new_kept_deleted(self.discover_local_resources())
            pronunciations = []
            for resource_mapping in new_resources:
                # Because pronunciation uses position as a "name", deleting these out of order
                # Effectively "changes" the name, causing some of the resources to not be deleted
                if resource_mapping.resource_type == Pronunciation:
                    pronunciations.append(resource_mapping.file_path)
                else:
                    resource_mapping.resource_type.delete_resource(resource_mapping.file_path)

            for file_path in self._sort_paths_for_reverse_deletion(pronunciations, Pronunciation):
                Pronunciation.delete_resource(file_path)

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
        incoming_resources = self.get_remote_resources_by_name(env)
        if not incoming_resources:
            raise ValueError(f"No resources returned from environment '{env}'.")
        self.branch_id = self.api_handler.branch_id

        self._check_no_duplicate_resource_paths(incoming_resources)

        files_with_conflicts = self._update_pulled_resources(
            original_resources=self.resources,
            incoming_resources=incoming_resources,
            force=True,
            format=format,
            on_save=None,
        )

        flow_folder = os.path.join(self.root_path, "flows")
        if os.path.exists(flow_folder):
            self._delete_empty_folders(flow_folder)

        self.resources = incoming_resources
        self.file_structure_info = self.compute_file_structure_info(incoming_resources)

        new_resources, _, _ = self.find_new_kept_deleted(self.discover_local_resources())
        pronunciations = []
        for resource_mapping in new_resources:
            # Because pronunciation uses position as a "name", deleting these out of order
            # effectively "changes" the name, causing some resources not to be deleted.
            if resource_mapping.resource_type == Pronunciation:
                pronunciations.append(resource_mapping.file_path)
            else:
                resource_mapping.resource_type.delete_resource(resource_mapping.file_path)

        for file_path in self._sort_paths_for_reverse_deletion(pronunciations, Pronunciation):
            Pronunciation.delete_resource(file_path)

        utils.export_decorators(DECORATORS, self.root_path)
        utils.save_imports(self.root_path)
        self.save_config()

        return files_with_conflicts

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

        # Compute current file (formatted)
        local_file_contents = {}
        MultiResourceYamlResource._file_cache.clear()
        if not force:
            for file in incoming_file_contents.keys():
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

        return files_with_conflicts, progress_offset

    def _update_pulled_resources(
        self,
        original_resources: ResourceMap,
        incoming_resources: ResourceMap,
        force: bool,
        format: bool = False,
        on_save: Callable[[int, int], None] | None = None,
    ) -> list[str]:
        files_with_conflicts = []

        # Generate resource mappings
        incoming_resource_mappings: list[ResourceMapping] = self._make_resource_mappings(
            incoming_resources
        )

        # If not force, compare with original and local changes
        original_resource_mappings: list[ResourceMapping] = self._make_resource_mappings(
            self.resources
        )

        # Merging is done on a per file basis.
        # For most resources - a resource is a single file
        # For MultiResourceYamlResources - a resource is a part of a file,
        # So first compute the whole file, then do merge process separately for each file.
        total = sum(len(res) for res in incoming_resources.values())

        multi_conflicts, current = self._update_multi_resource_yaml_resources(
            original_resources=self.resources,
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
                    local_content = resource_type.read_from_file(local_file_path)
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

        return files_with_conflicts

    def _stage_commands(
        self,
        new_state: ResourceMap,
        new_resources: ResourceMap,
        updated_resources: ResourceMap,
        deleted_resources: ResourceMap,
        email: Optional[str] = None,
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
        commands = []
        if pre_changes.new or pre_changes.deleted or pre_changes.updated:
            commands.extend(
                self.api_handler.queue_resources(
                    new_resources=pre_changes.new,
                    deleted_resources=pre_changes.deleted,
                    updated_resources=pre_changes.updated,
                    email=email,
                )
            )

        if new_resources or deleted_resources or updated_resources:
            commands.extend(
                self.api_handler.queue_resources(
                    new_resources=new_resources,
                    deleted_resources=deleted_resources,
                    updated_resources=updated_resources,
                    email=email,
                )
            )

        if post_changes.new or post_changes.deleted or post_changes.updated:
            commands.extend(
                self.api_handler.queue_resources(
                    new_resources=post_changes.new,
                    deleted_resources=post_changes.deleted,
                    updated_resources=post_changes.updated,
                    email=email,
                )
            )

        return commands

    def push_project(
        self,
        force=False,
        skip_validation=False,
        dry_run=False,
        format=False,
        email=None,
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
            email (str): Email to use for metadata creation.
                If None, use the email of the current user.

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
                resource_mappings=local_resource_mappings,
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

                has_changed, _ = resource.get_status(original_resource_hash)

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
                resources_dict=new_state, resource_mappings=local_resource_mappings
            )
            if validation_errors:
                error_messages = "\n".join(validation_errors)
                return False, f"Validation errors detected:\n{error_messages}", []

        commands = self._stage_commands(
            new_state, new_resources, updated_resources, deleted_resources, email=email
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
            # Update local state
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

        Only update the default variant if it's being enabled.

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

        # When a function is deleted the backend prunes that function ID from all
        # variable references. If the deleted function was the variable's only reference,
        # the backend auto-deletes the variable, which causes an explicit delete command
        # to fail and destroys any data on the variable.
        # If we want to keep the variable (another function is being updated/created to reference it)
        # Then it needs to be recreated after the function is deleted.
        old_var_refs = compute_variable_references(
            self.resources, self._make_resource_mappings(self.resources)
        )
        new_var_refs = compute_variable_references(state, self._make_resource_mappings(state))

        deleted_fn_ids = set(deleted_resources.get(Function, {}).keys()) | set(
            deleted_resources.get(FunctionStep, {}).keys()
        )

        for var_id, old_refs in old_var_refs.items():
            if var_id not in self.resources.get(Variable, {}):
                continue  # Variable not in current state (e.g. new variable from linked project sync)
            if var_id in deleted_resources.get(Variable, {}):
                continue  # already being explicitly deleted
            all_old_fn_ids = {fn_id for field_refs in old_refs.values() for fn_id in field_refs}
            if all_old_fn_ids.issubset(deleted_fn_ids):
                variable = self.resources[Variable][var_id]
                deleted_resources.setdefault(Variable, {})[var_id] = variable
                new_resources.setdefault(Variable, {})[var_id] = variable

            # If the variable references have changed, update the variable references
            new_refs = new_var_refs.get(var_id, {})
            if old_refs != new_refs:
                variable = self.resources[Variable][var_id]
                variable.references = new_refs
                updated_resources.setdefault(Variable, {})[var_id] = variable

        # Update new variables with their references
        for var_id, variable in new_resources.get(Variable, {}).items():
            variable_refs = new_var_refs.get(var_id, {})
            variable.references = variable_refs
            updated_resources.setdefault(Variable, {})[var_id] = variable

        # Create flow steps at same time as creating a flow
        for flow_config_id, flow_config in new_resources.get(FlowConfig, {}).items():
            if not isinstance(flow_config, FlowConfig):
                raise TypeError(f"Flow config is not a FlowConfig: {flow_config}")
            steps = []
            functions = []
            for resource_id, resource in list(new_resources.get(FlowStep, {}).items()):
                if isinstance(resource, FlowStep) and resource.flow_id == flow_config_id:
                    steps.append(resource)
                    new_resources[FlowStep].pop(resource_id, None)
                    if new_resources[FlowStep] == {}:
                        new_resources.pop(FlowStep, None)

            for resource_id, resource in list(new_resources.get(Function, {}).items()):
                if isinstance(resource, Function) and resource.flow_id == flow_config_id:
                    functions.append(resource)
                    new_resources[Function].pop(resource_id, None)
                    if new_resources[Function] == {}:
                        new_resources.pop(Function, None)

            flow_config.steps = steps
            flow_config.functions = functions

            function_start_step = next(
                (
                    step
                    for step in new_resources.get(FunctionStep, {}).values()
                    if step.step_id == flow_config.start_step
                    and step.flow_id == flow_config.resource_id
                ),
                None,
            )
            if function_start_step:
                # Create a dummy default step
                dummy_step_id = f"{function_start_step.step_id}_start_step_temp"
                dummy = FlowStep(
                    resource_id=f"{flow_config.name}_{dummy_step_id}",
                    step_id=dummy_step_id,
                    name=f"{flow_config.name}-temp",
                    flow_id=flow_config.resource_id,
                    flow_name=flow_config.name,
                    step_type=StepType.DEFAULT_STEP,
                    prompt="temp prompt",
                )
                flow_config.steps.append(dummy)
                flow_config.start_step = dummy.step_id
                reset_flow_config = FlowConfig(
                    resource_id=flow_config.resource_id,
                    name=flow_config.name,
                    description=flow_config.description,
                    start_step=function_start_step.step_id,
                )
                updated_resources.setdefault(FlowConfig, {})[flow_config.resource_id] = (
                    reset_flow_config
                )
                post_push_deleted_resources.setdefault(FlowStep, {})[dummy.resource_id] = dummy

        # Deleting flow config deletes all its steps/functions, so we don't need to
        for flow_config_id in deleted_resources.get(FlowConfig, {}):
            for resource_type in [FlowStep, Function, FunctionStep]:
                for resource_id, resource in list(deleted_resources.get(resource_type, {}).items()):
                    if (
                        isinstance(resource, (FlowStep, Function, FunctionStep))
                        and resource.flow_id == flow_config_id
                    ):
                        deleted_resources[resource_type].pop(resource_id, None)

        # If we are deleting a start step and updating the flow config to use a different step,
        # we need to delete the start step after the creation of the new one
        for flow_config_id, flow_config in updated_resources.get(FlowConfig, {}).items():
            if flow_config_id in new_resources.get(FlowConfig, {}):
                continue
            old_flow_config = self.resources.get(FlowConfig, {}).get(flow_config_id)
            old_step_resource_id = f"{old_flow_config.name}_{old_flow_config.start_step}"

            old_start_step = self.resources.get(FlowStep, {}).get(
                old_step_resource_id
            ) or self.resources.get(FunctionStep, {}).get(old_step_resource_id)
            if not old_start_step:
                raise ValueError(f"Old start step not found: {old_step_resource_id}")

            if flow_config.start_step != old_start_step.step_id:
                if old_start_step.resource_id in deleted_resources.get(type(old_start_step), {}):
                    # If it's being recreated with the same name (sync ids) we need to create a dummy step
                    new_step_resource_id = f"{flow_config.name}_{flow_config.start_step}"
                    if (
                        (
                            new_start_step := (
                                new_resources.get(FlowStep, {}).get(new_step_resource_id)
                                or new_resources.get(FunctionStep, {}).get(new_step_resource_id)
                            )
                        )
                        and new_start_step.name == old_start_step.name
                        and isinstance(new_start_step, type(old_start_step))
                    ):
                        dummy_step_id = f"{old_start_step.step_id}_temp"
                        dummy = FlowStep(
                            resource_id=f"{new_start_step.flow_name}_{dummy_step_id}",
                            step_id=dummy_step_id,
                            name=f"{new_start_step.name}-temp",
                            flow_id=new_start_step.flow_id,
                            flow_name=new_start_step.flow_name,
                            step_type=StepType.DEFAULT_STEP,
                            prompt="temp prompt",
                        )
                        flow_config_switch_to_dummy = FlowConfig(
                            resource_id=flow_config.resource_id,
                            name=flow_config.name,
                            description=flow_config.description,
                            start_step=dummy.step_id,
                        )
                        pre_push_new_resources.setdefault(FlowStep, {})[dummy.resource_id] = dummy
                        pre_push_updated_resources.setdefault(FlowConfig, {})[
                            flow_config.resource_id
                        ] = flow_config_switch_to_dummy
                        post_push_deleted_resources.setdefault(FlowStep, {})[dummy.resource_id] = (
                            dummy
                        )
                        updated_resources.setdefault(FlowConfig, {})[flow_config.resource_id] = (
                            flow_config
                        )
                    else:
                        # Move the old start step to post-push deleted resources
                        post_push_deleted_resources.setdefault(type(old_start_step), {})[
                            old_start_step.resource_id
                        ] = old_start_step
                        deleted_resources.get(type(old_start_step), {}).pop(
                            old_start_step.resource_id, None
                        )

        # If a flow step has changed type, we need to delete the old step and create a new one.
        # For the start step, use a dummy workaround (empty default_step).
        updated_flow_steps: list[tuple[str, FlowStep]] = list(
            updated_resources.get(FlowStep, {}).items()
        )
        removed_flow_step_ids = []
        for flow_step_id, flow_step in updated_flow_steps:
            original_flow_step: FlowStep = self.resources.get(FlowStep, {}).get(flow_step_id)
            if flow_step.step_type != original_flow_step.step_type:
                flow_config = state.get(FlowConfig, {}).get(original_flow_step.flow_id)
                is_start_step = (
                    flow_config is not None and flow_config.start_step == original_flow_step.step_id
                )
                if is_start_step:
                    dummy_step_id = f"{original_flow_step.step_id}_temp"
                    dummy = FlowStep(
                        resource_id=f"{original_flow_step.flow_name}_{dummy_step_id}",
                        step_id=dummy_step_id,
                        name=f"{original_flow_step.name}-temp",
                        flow_id=original_flow_step.flow_id,
                        flow_name=original_flow_step.flow_name,
                        step_type=StepType.DEFAULT_STEP,
                        prompt="temp prompt",
                    )
                    flow_config_switch_to_dummy = FlowConfig(
                        resource_id=flow_config.resource_id,
                        name=flow_config.name,
                        description=flow_config.description,
                        start_step=dummy.step_id,
                    )
                    pre_push_new_resources.setdefault(FlowStep, {})[dummy.resource_id] = dummy
                    pre_push_updated_resources.setdefault(FlowConfig, {})[
                        flow_config.resource_id
                    ] = flow_config_switch_to_dummy
                    updated_resources.setdefault(FlowConfig, {})[flow_config.resource_id] = (
                        flow_config
                    )
                    post_push_deleted_resources.setdefault(FlowStep, {})[dummy.resource_id] = dummy
                deleted_resources.setdefault(FlowStep, {})[flow_step_id] = original_flow_step
                new_resources.setdefault(FlowStep, {})[flow_step_id] = flow_step
                removed_flow_step_ids.append(flow_step_id)

        for flow_step_id in removed_flow_step_ids:
            updated_resources[FlowStep].pop(flow_step_id, None)

        # Add known attributes to any new variant to give it a default value
        for variant in new_resources.get(Variant, {}).values():
            if not isinstance(variant, Variant):
                raise TypeError(f"Variant is not a Variant: {variant}")
            attribute_ids = list(self.resources.get(VariantAttribute, {}).keys())
            variant.attribute_ids = attribute_ids

        # Only update the default variant if it's being enabled
        updated_variants: list[Variant] = list(updated_resources.get(Variant, {}).values())
        for variant in updated_variants:
            if not variant.is_default:
                updated_resources[Variant].pop(variant.resource_id, None)

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
        files_with_conflicts = []
        modified_files = []
        new_files = []
        deleted_files = []

        new_resources_mappings, kept_resources_mappings, deleted_resources_mappings = (
            self.find_new_kept_deleted(self.discover_local_resources())
        )

        new_files = [resource.file_path for resource in new_resources_mappings]

        deleted_files = [resource.file_path for resource in deleted_resources_mappings]

        local_resources_mappings = new_resources_mappings + kept_resources_mappings

        for kept_local_resource_mapping in kept_resources_mappings:
            original_hash = self.file_structure_info.get(
                os.path.relpath(kept_local_resource_mapping.file_path, self.root_path),
                {},
            ).get("hash")
            local_resource = self.read_local_resource(
                resource=kept_local_resource_mapping, resource_mappings=local_resources_mappings
            )

            modified, has_conflict = local_resource.get_status(original_hash)
            if modified:
                modified_files.append(kept_local_resource_mapping.file_path)
            if has_conflict:
                files_with_conflicts.append(kept_local_resource_mapping.file_path)

        return files_with_conflicts, modified_files, new_files, deleted_files

    def revert_changes(self, files: list[str] = None) -> list[str]:
        """Revert changes in the project.

        Args:
            files (list[str]): List of specific files to revert. If None, revert all changes.
        """
        reverted_files = []
        resource_mappings = self._make_resource_mappings(self.resources)
        all_files = not files
        for resource in self.all_resources:
            if not all_files and resource.get_path(self.root_path) not in files:
                continue

            resource.save(self.root_path, resource_mappings=resource_mappings)
            reverted_files.append(resource.get_path(self.root_path))

        return reverted_files

    def get_diffs(self, all_files: bool = False, files: list[str] = None) -> dict[str, str]:
        """Get the diffs of all resources in the project.

        Args:
            all_files (bool): If True, get diffs for all files.
            files (list[str]): List of specific files to get diffs for.

        Returns:
            dict[str, str]: A dictionary mapping resource file names to their diffs.
        """
        diffs = {}
        new_resources_mappings, kept_resources_mappings, deleted_resources_mappings = (
            self.find_new_kept_deleted(self.discover_local_resources())
        )
        local_resources_mappings = new_resources_mappings + kept_resources_mappings

        for local_resource_mapping in kept_resources_mappings:
            if not all_files and files and local_resource_mapping.file_path not in files:
                continue

            original_hash = self.file_structure_info.get(
                os.path.relpath(local_resource_mapping.file_path, self.root_path), {}
            ).get("hash")

            local_resource = self.read_local_resource(
                resource=local_resource_mapping, resource_mappings=local_resources_mappings
            )

            modified, _ = local_resource.get_status(original_hash)
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
            resource = self.read_local_resource(
                resource=resource_mapping, resource_mappings=local_resources_mappings
            )

            diffs[resource.file_path] = resource_utils.get_diff(
                "",
                resource.read_to_raw(
                    resource.get_path(self.root_path),
                    resource_name=resource.name,
                    resource_mappings=local_resources_mappings,
                ),
            )

        for resource_mapping in deleted_resources_mappings:
            if not all_files and files and resource_mapping.file_path not in files:
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

    def get_remote_resources_by_name(self, name: str) -> ResourceMap:
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
                return {}
            logger.info(f"Pulling resources from deployment '{deployment_id}' ({name})...")
            return self.api_handler.pull_deployment_resources(deployment_id)

        # 2) Branch name -> branch resources (event sourcing only)
        branches = self.api_handler.get_branches()
        if name in branches:
            branch_id = branches[name]
            branch_api_handler = AgentStudioInterface(
                self.region, self.account_id, self.project_id, branch_id
            )
            logger.info(f"Pulling resources from branch '{name}'...")
            resources, _ = branch_api_handler.pull_resources()
            return resources

        # 3) Deployment version hash prefix -> deployment resources
        version_hash = (name or "")[:9].lower()
        if version_hash:
            deployments, _ = self.get_deployments(client_env="sandbox")
            deployment = next(
                (d for d in deployments if d.get("version_hash")[:9] == version_hash), {}
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
            resources: ResourceMap = {}
            for resource_mapping in local_resources_mappings:
                resource = self.read_local_resource(
                    resource=resource_mapping, resource_mappings=local_resources_mappings
                )
                resources.setdefault(resource_mapping.resource_type, {})[
                    resource_mapping.resource_id
                ] = resource
            return resources

        logger.error(f"Name '{name}' not found in environments, branches, or deployments.")
        return {}

    def diff_remote_named_versions(
        self, before_name: str, after_name: str
    ) -> Optional[dict[str, str]]:
        """Compute diffs between two remote project states (branches / envs / deployments)."""
        before_resources = self.get_remote_resources_by_name(before_name)
        after_resources = self.get_remote_resources_by_name(after_name)

        if not before_resources or not after_resources:
            logger.error(
                "Could not retrieve resources for one or both specified names: "
                f"before={before_name}, after={after_name}"
            )
            return None

        before_resources_by_path: dict[tuple[ResourceType, str], Resource] = {}
        for resource_type, resources_dict in before_resources.items():
            for resource_id, resource in resources_dict.items():
                before_resources_by_path[(resource_type, resource.file_path)] = resource

        after_resources_by_path: dict[tuple[ResourceType, str], Resource] = {}
        for resource_type, resources_dict in after_resources.items():
            for resource_id, resource in resources_dict.items():
                after_resources_by_path[(resource_type, resource.file_path)] = resource
        # Combine both resource sets to create comprehensive resource_mappings
        # This ensures all resource references can be properly converted to pretty names
        combined_resources: ResourceMap = {}
        for resource_type, resources_dict in before_resources.items():
            combined_resources[resource_type] = combined_resources.get(resource_type, {})
            combined_resources[resource_type].update(resources_dict)
        for resource_type, resources_dict in after_resources.items():
            combined_resources[resource_type] = combined_resources.get(resource_type, {})
            combined_resources[resource_type].update(resources_dict)

        resource_mappings = self._make_resource_mappings(combined_resources)

        diffs: dict[str, str] = {}

        all_resource_paths = set(before_resources_by_path.keys()) | set(
            after_resources_by_path.keys()
        )

        for resource_key in all_resource_paths:
            before_resource = before_resources_by_path.get(resource_key)
            after_resource = after_resources_by_path.get(resource_key)

            if before_resource and after_resource:
                before_pretty = before_resource.to_pretty(resource_mappings=resource_mappings)
                after_pretty = after_resource.to_pretty(resource_mappings=resource_mappings)
                if before_pretty != after_pretty:
                    diffs[before_resource.file_path] = resource_utils.get_diff(
                        before_pretty, after_pretty
                    )
            elif before_resource and not after_resource:
                before_pretty = before_resource.to_pretty(resource_mappings=resource_mappings)
                diffs[before_resource.file_path] = resource_utils.get_diff(before_pretty, "")
            elif not before_resource and after_resource:
                after_pretty = after_resource.to_pretty(resource_mappings=resource_mappings)
                diffs[after_resource.file_path] = resource_utils.get_diff("", after_pretty)

        if not diffs:
            logger.info(
                f"No differences detected between names '{before_name}' and '{after_name}'."
            )
            return None

        return diffs

    def discover_local_resources(self) -> DiscoveredResourcePaths:
        """Return a dict of all discovered resources locally
        Using the resource name as the key

        Returns:
            DiscoveredResourcePaths: A dictionary mapping resource types to
                lists of discovered resource file paths.
        """
        discovered_resources: DiscoveredResourcePaths = {}
        for resource_class in RESOURCE_NAME_TO_CLASS.values():
            discovered = resource_class.discover_resources(self.root_path)
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
        except Exception as e:
            raise ValueError(
                f"Error reading resource {resource.resource_name} at {resource.file_path}"
            ) from e

        return resource

    def find_new_kept_deleted(
        self, discovered_resources: dict[type[Resource], list[str]]
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
                if file_path in known_files:
                    # Remove root path from file path
                    resource_info = self.file_structure_info.get(
                        os.path.relpath(file_path, self.root_path)
                    )
                    if not resource_info:
                        raise ValueError(f"Resource info not found for {file_path}")

                    kept_resource_mappings.append(
                        ResourceMapping(
                            resource_id=resource_info["resource_id"],
                            resource_type=resource_type,
                            resource_name=resource_info["resource_name"],
                            file_path=file_path,
                            flow_name=flow_paths_to_names.get(
                                resource_utils.get_flow_name_from_path(file_path),
                            ),
                            resource_prefix=resource_type.get_resource_prefix(file_path=file_path),
                        )
                    )

                else:
                    # Flow step names are not from file names, so we need to handle them separately
                    resource_name = os.path.splitext(os.path.basename(file_path))[0]
                    flow_name = flow_paths_to_names.get(
                        resource_utils.get_flow_name_from_path(file_path),
                    )
                    resource_id = self.generate_uuid(resource_type)
                    if resource_type == FlowStep:
                        flow_step: FlowStep = self.read_local_resource(
                            ResourceMapping(
                                resource_id="temp_id",
                                resource_type=FlowStep,
                                resource_name=resource_name,
                                file_path=file_path,
                                flow_name=flow_name,
                                resource_prefix=resource_type.get_resource_prefix(
                                    file_path=file_path
                                ),
                            ),
                            resource_mappings=[],
                        )
                        resource_name = flow_step.name
                        resource_id = f"{flow_name}_{resource_id}"

                    elif resource_type == FunctionStep:
                        resource_id = f"{flow_name}_{resource_id}"

                    if resource_type == FlowConfig:
                        resource_name = flow_name

                    # Resource name in file path is cleaned, so we need to get the original name
                    if issubclass(resource_type, MultiResourceYamlResource):
                        resource = self.read_local_resource(
                            ResourceMapping(
                                resource_id="temp_id",
                                resource_type=resource_type,
                                resource_name=resource_name,
                                file_path=file_path,
                                flow_name=flow_name,
                                resource_prefix=resource_type.get_resource_prefix(
                                    file_path=file_path
                                ),
                            ),
                            resource_mappings=[],
                        )
                        resource_name = resource.name

                    new_resource_mappings.append(
                        ResourceMapping(
                            resource_id=resource_id,
                            resource_type=resource_type,
                            resource_name=resource_name,
                            file_path=file_path,
                            flow_name=flow_name,
                            resource_prefix=resource_type.get_resource_prefix(file_path=file_path),
                        )
                    )

        deleted_file_paths = known_files - discovered_files
        for file_path in deleted_file_paths:
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

    def get_branches(self) -> tuple[Optional[str], dict[str, str]]:
        """Get a list of all branches in the (remote) project.

        Returns:
            Optional[str], dict[str, str]: The current branch name and a dictionary mapping
            branch names to branch IDs. First element is None if the current branch does not exist in the remote.
        """
        branches = self.api_handler.get_branches()
        current_branch = next(
            (name for name, branch_id in branches.items() if branch_id == self.branch_id),
            None,
        )
        return current_branch, branches

    def create_branch(self, branch_name: str = None) -> str:
        """Create a new branch in the project.

        Args:
            branch_name (str): The name of the new branch

        Returns:
            str: The ID of the newly created branch
        """
        branch_id = self.api_handler.create_branch(branch_name)
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
        if self.get_diffs(all_files=True) and not force:
            raise ValueError(
                "Cannot switch branches with uncommitted changes. Use --force to switch and discard changes."
            )

        branches = self.api_handler.get_branches()
        if branch_name not in branches:
            raise ValueError(f"Branch {branch_name} does not exist.")
        success = self.api_handler.switch_branch(branches[branch_name])
        projection = {}
        if success:
            self.branch_id = branches[branch_name]
            _, projection = self.pull_project(
                force=force, format=format, projection_json=projection_json, on_save=on_save
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
    ) -> dict:
        """Create a chat session (standard or draft).

        Pass environment="draft" to start a branch draft session, which fetches
        branch deployment info from sourcerer before creating the conversation.

        Args:
            environment (str): The environment to create the chat session in: draft, sandbox, pre-release or live.
            channel (str): The channel to create the chat session in: chat.polyai or webchat.polyai.
            variant (ty.Optional[str]): The variant ID to create the chat session in.

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
            )

        return AgentStudioInterface.create_chat(
            region=self.region,
            account_id=self.account_id,
            project_id=self.project_id,
            environment=environment,
            variant_id=variant,
            channel=channel,
        )

    def send_message(
        self,
        conversation_id: str,
        text: str,
        environment: str,
    ) -> dict:
        """Send a message to an active chat conversation.

        Args:
            conversation_id (str): The ID of the conversation to send the message to.
            text (str): The user message text to send.
            environment (str): The environment of the conversation: draft, sandbox, pre-release or live.

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
            )
        return AgentStudioInterface.send_chat_message(
            region=self.region,
            account_id=self.account_id,
            project_id=self.project_id,
            conversation_id=conversation_id,
            text=text,
            environment=environment,
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

    def get_conversation_url(self, conversation_id: str) -> str:
        """Build the Studio URL for a conversation.

        Args:
            conversation_id (str): The ID of the conversation to get the URL for.

        Returns:
            str: The URL of the conversation.
        """
        region_link_map = {"uk-1": "uk", "euw-1": "eu", "us-1": "us"}
        short = region_link_map.get(self.region, self.region)
        return (
            f"https://studio.{short}.poly.ai"
            f"/{self.account_id}/{self.project_id}"
            f"/conversations/{conversation_id}"
        )

    def _make_resource_mappings(self, resources: ResourceMap) -> list[ResourceMapping]:
        resource_mappings: list[ResourceMapping] = []
        for resource_type, resources_dict in resources.items():
            for resource_id, resource in resources_dict.items():
                resource_path = resource.get_path(self.root_path)
                resource_mappings.append(
                    ResourceMapping(
                        resource_id=resource_id,
                        resource_type=resource_type,
                        resource_name=resource.name,
                        file_path=resource_path,
                        flow_name=(
                            resource.name
                            if isinstance(resource, FlowConfig)
                            else getattr(resource, "flow_name", None)
                        ),
                        resource_prefix=resource.get_resource_prefix(file_path=resource.file_path),
                    )
                )
        return resource_mappings

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
        resource_mappings: list[ResourceMapping] = [
            m for m in all_mappings if (not files or m.file_path in files)
        ]
        return self._format_resources(resource_mappings, check_only=check_only)

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
        for resource_mapping in resource_mappings:
            try:
                content = resource_mapping.resource_type.read_from_file(resource_mapping.file_path)
                formatted_content = resource_mapping.resource_type.format_resource(
                    content,
                    file_name=resource_mapping.resource_name,
                )
                if check_only:
                    if formatted_content.strip() != content.strip():
                        affected.append(resource_mapping.file_path)
                else:
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

        resources: ResourceMap = {}
        for resource_mapping in local_resource_mappings:
            local_resource = self.read_local_resource(
                resource=resource_mapping,
                resource_mappings=local_resource_mappings,
            )
            resources.setdefault(resource_mapping.resource_type, {})[
                resource_mapping.resource_id
            ] = local_resource

        return self.validate_resources(
            resources_dict=resources,
            resource_mappings=local_resource_mappings,
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
        self, message: str, conflict_resolutions: list[dict[str, Any]] = None
    ) -> tuple[bool, list[str], list[str]]:
        """Merge a branch into the current branch in the project.

        Args:
            message (str): The merge commit message.
            conflict_resolutions (list[dict[str, Any]]): A list of conflict
                resolutions. Each resolution should have:
                - path: List of strings representing the path to the conflicted field (e.g., ["users", "1", "name"])
                - strategy: Resolution strategy - "ours", "theirs", or "base"
                - value: Optional custom value (only used with custom strategy)

        Returns:
            bool: True if the merge was successful, False otherwise
            list[str]: A list of conflict paths if the merge failed, empty list if successful
            list[str]: A list of error messages if the merge failed, empty list if successful
        """
        branches = self.api_handler.get_branches()
        if self.branch_id not in branches.values():
            raise ValueError(f"Branch {self.branch_id} does not exist.")

        if self.branch_id == "main":
            raise ValueError("Merging from 'main' branch is not supported.")

        if diffs := self.get_diffs(all_files=True):
            raise ValueError(
                f"Cannot merge branch with uncommitted changes, diffs: {list(diffs.keys())}"
            )

        success, conflicts, errors = self.api_handler.merge_branch(
            message=message, conflict_resolutions=conflict_resolutions
        )
        if success:
            self.switch_branch("main", force=True)
            return True, [], []

        error_messages = []
        conflict_messages = []
        if conflicts:
            conflict_messages = [conflict["path"] for conflict in conflicts]
            logger.debug(f"Merge conflicts detected: conflicts={conflicts!r}")
        if errors:
            error_messages = [f"{error['path']}: {error['message']}" for error in errors]
            logger.debug(f"Merge errors detected: errors={errors!r}")
        return False, conflict_messages, error_messages

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

        success = self.api_handler.delete_branch(branches[branch_name])
        if success and self.branch_id == branches[branch_name]:
            self.switch_branch("main", force=True)
        return True

    def sync_ids_with_sandbox(self, email: str = None) -> bool:
        """Sync ids of resources in sandbox into current branch

        Args:
            email (str): Email to use for metadata creation.
                If None, use the email of the current user.

        Returns:
            bool: True if the sync was successful, False otherwise
        """
        if self.branch_id == "main":
            raise ValueError("Cannot sync ids while on main branch.")

        if self.get_diffs(all_files=True):
            raise ValueError("Cannot sync ids due to uncommitted changes.")

        sandbox_resources = self.get_remote_resources_by_name("main")
        # Build lookup by file path -> Resource
        sandbox_resource_lookup: dict[str, Resource] = {}
        for resources_dict in sandbox_resources.values():
            for resource in resources_dict.values():
                sandbox_resource_lookup[resource.file_path] = resource

        # 1. Build sync resource_mappings: use sandbox id when there is a sandbox match by file_path
        sync_mappings: list[ResourceMapping] = []
        for resource_type, resources_dict in self.resources.items():
            for resource_id, resource in resources_dict.items():
                sandbox_version = sandbox_resource_lookup.get(resource.file_path)
                mapping_resource_id = (
                    sandbox_version.resource_id if sandbox_version else resource.resource_id
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
                    )
                )

        # 2. Re-read all resources with sync mappings (references resolve from mappings)
        branch_by_path: dict[str, tuple[type[Resource], str, Resource]] = {}
        for resource_type, resources_dict in self.resources.items():
            for resource_id, resource in resources_dict.items():
                path = resource.file_path
                branch_by_path[path] = (resource_type, resource_id, resource)

        new_state: ResourceMap = {}
        for mapping in sync_mappings:
            relative_file_path = os.path.relpath(mapping.file_path, self.root_path)
            original = branch_by_path.get(relative_file_path)
            branch_resource = original[2] if original else None
            sandbox_resource = sandbox_resource_lookup.get(relative_file_path, branch_resource)
            local_resource = self.read_local_resource(
                resource=mapping,
                resource_mappings=sync_mappings,
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

        self._stage_commands(
            new_state, new_resources, updated_resources, deleted_resources, email=email
        )
        success = self.api_handler.send_queued_commands()

        self.branch_id = self.api_handler.branch_id

        if not success:
            return False

        self.resources = new_state
        self.file_structure_info = self.compute_file_structure_info(self.resources)
        self.save_config()

        return True
