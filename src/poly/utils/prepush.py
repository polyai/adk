"""Pre-push cleaning of resource change sets.

Each function here adjusts the new/updated/deleted resource maps (in place)
before they are turned into push commands, working around API constraints such
as undeletable start steps, cascade deletes and backend-managed variable
references. They are orchestrated, in order, by
``AgentStudioProject._clean_resources_before_push``.

Copyright PolyAI Limited
"""

import copy
from typing import Callable, TypeAlias

from poly.resources import (
    ChatGreeting,
    ChatSafetyFilters,
    ChatStylePrompt,
    Condition,
    FlowConfig,
    FlowStep,
    Function,
    FunctionStep,
    Resource,
    ResourceMapping,
    StepType,
    Variable,
    Variant,
    VariantAttribute,
)
from poly.utils.commands import (
    create_command_clear_flow_settings,
    create_command_webchat_channel_update_status,
)
from poly.utils.variable_references import compute_variable_references

ResourceMap: TypeAlias = dict[type[Resource], dict[str, Resource]]


def enable_webchat_channel(
    new_resources: ResourceMap,
    pre_push_updated_resources: ResourceMap,
    queue_command: Callable[..., None],
) -> None:
    """Enable the Webchat channel when new Webchat configs are being created.

    Queues a channel-enable command and moves any new Webchat config resources
    to the pre-push updated set (enabling the channel creates them remotely).
    """
    # If we are creating any Webchat config, instead enable Webchat and set
    # the configs as update
    if (
        ChatGreeting in new_resources
        or ChatSafetyFilters in new_resources
        or ChatStylePrompt in new_resources
    ):
        queue_command(create_command_webchat_channel_update_status(enabled=True))
        # Move any Webchat config in new resources to updated resources
        for resource_type in [ChatGreeting, ChatSafetyFilters, ChatStylePrompt]:
            for resource_id, resource in new_resources.get(resource_type, {}).items():
                pre_push_updated_resources.setdefault(resource_type, {})[resource_id] = resource
            if resource_type in new_resources:
                new_resources.pop(resource_type)


def fix_orphaned_variables(
    state: ResourceMap,
    new_resources: ResourceMap,
    updated_resources: ResourceMap,
    deleted_resources: ResourceMap,
    current_resources: ResourceMap,
    make_resource_mappings: Callable[[ResourceMap], list[ResourceMapping]],
) -> None:
    """Recreate or update variables whose function references are changing.

    Handles variables orphaned by function deletions (delete + recreate) and
    refreshes the references of changed or new variables.
    """
    # When a function is deleted the backend prunes that function ID from all
    # variable references. If the deleted function was the variable's only reference,
    # the backend auto-deletes the variable, which causes an explicit delete command
    # to fail and destroys any data on the variable.
    # If we want to keep the variable (another function is being updated/created to reference it)
    # Then it needs to be recreated after the function is deleted.
    old_var_refs = compute_variable_references(
        current_resources, make_resource_mappings(current_resources)
    )
    new_var_refs = compute_variable_references(state, make_resource_mappings(state))

    deleted_fn_ids = set(deleted_resources.get(Function, {}).keys()) | set(
        deleted_resources.get(FunctionStep, {}).keys()
    )

    for var_id, old_refs in old_var_refs.items():
        if var_id not in current_resources.get(Variable, {}):
            continue  # Variable not in current state (e.g. new variable from linked project sync)
        if var_id in deleted_resources.get(Variable, {}):
            continue  # already being explicitly deleted
        all_old_fn_ids = {fn_id for field_refs in old_refs.values() for fn_id in field_refs}
        if all_old_fn_ids.issubset(deleted_fn_ids):
            variable = current_resources[Variable][var_id]
            deleted_resources.setdefault(Variable, {})[var_id] = variable
            new_resources.setdefault(Variable, {})[var_id] = variable

        # If the variable references have changed, update the variable references
        new_refs = new_var_refs.get(var_id, {})
        if old_refs != new_refs:
            variable = current_resources[Variable][var_id]
            variable.references = new_refs
            updated_resources.setdefault(Variable, {})[var_id] = variable

    # Update new variables with their references
    for var_id, variable in new_resources.get(Variable, {}).items():
        variable_refs = new_var_refs.get(var_id, {})
        variable.references = variable_refs
        updated_resources.setdefault(Variable, {})[var_id] = variable


def group_new_flow_resources(
    new_resources: ResourceMap,
    updated_resources: ResourceMap,
    post_push_deleted_resources: ResourceMap,
) -> None:
    """Group new flow steps/functions under their new flow config.

    If a new flow's start step is a function step, push a dummy default step
    as the start step first, then reset the flow config post-push.
    """
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
                resource_id=f"{flow_config.resource_id}_{dummy_step_id}",
                step_id=dummy_step_id,
                name=f"{flow_config.name}-temp",
                flow_id=flow_config.resource_id,
                flow_name=flow_config.name,
                step_type=StepType.DEFAULT_STEP,
                prompt="temp prompt",
            )
            push_flow_config = copy.deepcopy(flow_config)
            push_flow_config.steps.append(dummy)
            push_flow_config.start_step = dummy.step_id
            new_resources[FlowConfig][flow_config_id] = push_flow_config
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


def prune_cascade_deleted_flow_children(deleted_resources: ResourceMap) -> None:
    """Drop step/function deletes covered by their flow config's cascade delete."""
    # Deleting flow config deletes all its steps/functions, so we don't need to
    for flow_config_id in deleted_resources.get(FlowConfig, {}):
        for resource_type in [FlowStep, Function, FunctionStep]:
            for resource_id, resource in list(deleted_resources.get(resource_type, {}).items()):
                if (
                    isinstance(resource, (FlowStep, Function, FunctionStep))
                    and resource.flow_id == flow_config_id
                ):
                    deleted_resources[resource_type].pop(resource_id, None)


def replace_flow_steps_with_dummy_workaround(
    state: ResourceMap,
    new_resources: ResourceMap,
    updated_resources: ResourceMap,
    deleted_resources: ResourceMap,
    pre_push_new_resources: ResourceMap,
    pre_push_updated_resources: ResourceMap,
    post_push_deleted_resources: ResourceMap,
    current_resources: ResourceMap,
) -> None:
    """Handle start-step replacements and flow step type changes.

    A start step cannot be deleted, so replacements use a dummy default step
    (pre-push: create dummy and switch to it; main push: delete/create the real
    step and reset the flow config; post-push: delete the dummy). Steps that
    change type are deleted and recreated rather than updated.
    """
    # If we are deleting a start step and updating the flow config to use a different step,
    # we need to delete the start step after the creation of the new one
    for flow_config_id, flow_config in updated_resources.get(FlowConfig, {}).items():
        if flow_config_id in new_resources.get(FlowConfig, {}):
            continue
        old_flow_config = current_resources.get(FlowConfig, {}).get(flow_config_id)
        old_step_resource_id = f"{old_flow_config.resource_id}_{old_flow_config.start_step}"

        old_start_step = current_resources.get(FlowStep, {}).get(
            old_step_resource_id
        ) or current_resources.get(FunctionStep, {}).get(old_step_resource_id)
        if not old_start_step:
            raise ValueError(f"Old start step not found: {old_step_resource_id}")

        if flow_config.start_step != old_start_step.step_id:
            if old_start_step.resource_id in deleted_resources.get(type(old_start_step), {}):
                # If it's being recreated with the same name (sync ids) we need to create a dummy step
                new_step_resource_id = f"{flow_config.resource_id}_{flow_config.start_step}"
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
                        resource_id=f"{new_start_step.flow_id}_{dummy_step_id}",
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
                    post_push_deleted_resources.setdefault(FlowStep, {})[dummy.resource_id] = dummy
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
        original_flow_step: FlowStep = current_resources.get(FlowStep, {}).get(flow_step_id)
        if flow_step.step_type != original_flow_step.step_type:
            flow_config = state.get(FlowConfig, {}).get(original_flow_step.flow_id)
            is_start_step = (
                flow_config is not None and flow_config.start_step == original_flow_step.step_id
            )
            if is_start_step:
                dummy_step_id = f"{original_flow_step.step_id}_temp"
                dummy = FlowStep(
                    resource_id=f"{original_flow_step.flow_id}_{dummy_step_id}",
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
                pre_push_updated_resources.setdefault(FlowConfig, {})[flow_config.resource_id] = (
                    flow_config_switch_to_dummy
                )
                updated_resources.setdefault(FlowConfig, {})[flow_config.resource_id] = flow_config
                post_push_deleted_resources.setdefault(FlowStep, {})[dummy.resource_id] = dummy
            deleted_resources.setdefault(FlowStep, {})[flow_step_id] = original_flow_step
            new_resources.setdefault(FlowStep, {})[flow_step_id] = flow_step
            removed_flow_step_ids.append(flow_step_id)

    for flow_step_id in removed_flow_step_ids:
        updated_resources[FlowStep].pop(flow_step_id, None)


def default_new_variant_attributes(
    new_resources: ResourceMap,
    deleted_resources: ResourceMap,
    current_resources: ResourceMap,
) -> None:
    """Give new variants all known (non-deleted) attributes as default values."""
    # Add known attributes to any new variant to give it a default value
    deleted_attribute_ids = set(deleted_resources.get(VariantAttribute, {}).keys())
    for variant in new_resources.get(Variant, {}).values():
        if not isinstance(variant, Variant):
            raise TypeError(f"Variant is not a Variant: {variant}")
        attribute_ids = [
            aid
            for aid in current_resources.get(VariantAttribute, {}).keys()
            if aid not in deleted_attribute_ids
        ]
        variant.attribute_ids = attribute_ids


def fix_conditions_for_deleted_steps(
    new_resources: ResourceMap,
    updated_resources: ResourceMap,
    deleted_resources: ResourceMap,
    current_resources: ResourceMap,
) -> None:
    """Adjust condition commands for steps that are being deleted.

    Conditions of a deleted parent step are cascade-deleted by the backend, so
    their explicit deletes are dropped. Condition updates whose original target
    step is being deleted become creates (the delete removes the condition).
    """
    # Don't delete condition if parent step is being deleted
    for flow_step in list(deleted_resources.get(FlowStep, {}).values()):
        for condition in flow_step.conditions:
            deleted_resources.get(Condition, {}).pop(condition.resource_id, None)

    # If we are deleting a step and pointing a condition to a different step, the delete will auto delete the condition so the update will fail. We should instead make it a create
    deleted_steps = list(deleted_resources.get(FlowStep, {}).values()) + list(
        deleted_resources.get(FunctionStep, {}).values()
    )
    updated_conditions = list(updated_resources.get(Condition, {}).items())
    if deleted_steps:
        flows_with_deleted_steps = {deleted_step.flow_id for deleted_step in deleted_steps}
        for condition_id, condition in updated_conditions:
            if condition.flow_id not in flows_with_deleted_steps:
                continue
            original_flow_step: FlowStep = next(
                (
                    flow_step
                    for flow_step in current_resources.get(FlowStep, {}).values()
                    if flow_step.flow_id == condition.flow_id
                    and flow_step.step_id == condition.step_id
                ),
                None,
            )
            if not original_flow_step:
                continue
            original_condition: Condition = next(
                (
                    cond
                    for cond in original_flow_step.conditions
                    if cond.resource_id == condition_id
                ),
                None,
            )
            if not original_condition:
                continue

            deleted_original_step = next(
                (
                    step
                    for step in deleted_steps
                    if step.flow_id == condition.flow_id
                    and step.step_id == original_condition.child_step
                ),
                None,
            )
            if deleted_original_step:
                new_resources.setdefault(Condition, {})[condition_id] = condition
                updated_resources.get(Condition, {}).pop(condition_id, None)


CLEARABLE_SETTINGS = {
    "asr": "asr",
    "barge_in": "bargeIn",
    "llm": "llm",
    "vad": "vad",
}


def clear_unused_settings_from_flow_step(
    updated_resources: ResourceMap,
    current_resources: ResourceMap,
    queue_command: Callable[..., None],
):
    """If a flow step settings is being updated and a setting is cleared it isn't sent in the proto update command.
    The backend will read this as not updated rather than cleared.

    This function queues a new update command with the cleared settings to ensure they are cleared in the backend.
    """
    for flow_step_id, updated_step in updated_resources.get(FlowStep, {}).items():
        updated_step: FlowStep
        original_step: FlowStep = current_resources.get(FlowStep, {}).get(flow_step_id)
        if not original_step:
            continue  # Step not in current state (e.g. new step from linked project sync)
        if not original_step.settings and not updated_step.settings:
            continue  # No settings to compare

        cleared_settings = []
        if original_step.settings and updated_step.settings:
            original_keys = set(original_step.settings.to_yaml_dict().keys())
            updated_keys = set(updated_step.settings.to_yaml_dict().keys())
            cleared_settings = sorted(
                CLEARABLE_SETTINGS[key]
                for key in (original_keys - updated_keys)
                if key in CLEARABLE_SETTINGS
            )

        if cleared_settings:
            queue_command(
                create_command_clear_flow_settings(
                    flow_id=updated_step.flow_id,
                    step_id=updated_step.step_id,
                    cleared_fields=cleared_settings,
                )
            )
