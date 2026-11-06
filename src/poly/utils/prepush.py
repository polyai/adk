"""Pre-push cleaning of resource change sets.

Each function here adjusts the new/updated/deleted resource maps (in place)
before they are turned into push commands, working around API constraints such
as undeletable start steps, cascade deletes and backend-managed variable
references. They are orchestrated, in order, by
``AgentStudioProject._clean_resources_before_push``.

Copyright PolyAI Limited
"""

import copy
import graphlib
import uuid
from typing import Callable, Optional, TypeAlias

from poly.resources import (
    AsrSettings,
    AttributeKind,
    ChatGreeting,
    ChatSafetyFilters,
    ChatStylePrompt,
    Condition,
    FlowConfig,
    FlowStep,
    Function,
    FunctionStep,
    OutboundCampaign,
    OutboundCampaignFunction,
    OutboundCampaignNode,
    OutboundCampaignSettings,
    Resource,
    ResourceMapping,
    StepType,
    TestCase,
    TestCaseAssertion,
    TestCaseTags,
    Variable,
    Variant,
    VariantAttribute,
)
from poly.resources.outbound_campaign import (
    campaign_nodes,
    function_file_stem,
    map_route_targets,
    node_pairing_key,
    paired_campaigns,
)
from poly.resources.test_suite import (
    TestCaseApiOperationMock,
    TestCaseIntegrationAttributes,
    TestCaseSipHeaders,
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


def pair_renamed_test_cases(
    state: ResourceMap,
    new_resources: ResourceMap,
    updated_resources: ResourceMap,
    deleted_resources: ResourceMap,
) -> None:
    """Push a renamed test case as an update of the saved case, keeping its id.

    A test case's file name comes from its name, so a rename reads as a delete of
    the old file and a create of the new one: the case would get a new id and lose
    its run history. A new case whose scenario matches exactly one deleted case (and
    no other new case) takes that case's id and becomes an update. Its sub-resources
    are re-diffed against the saved case. Anything ambiguous stays a delete and a
    create.
    """
    new_cases = new_resources.get(TestCase, {})
    deleted_cases = deleted_resources.get(TestCase, {})
    if not new_cases or not deleted_cases:
        return

    def by_scenario(cases: dict[str, Resource]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for case_id, case in cases.items():
            scenario = (case.scenario or "").strip() if isinstance(case, TestCase) else ""
            if scenario:
                grouped.setdefault(scenario, []).append(case_id)
        return grouped

    new_ids_by_scenario = by_scenario(new_cases)
    for scenario, old_ids in by_scenario(deleted_cases).items():
        new_ids = new_ids_by_scenario.get(scenario, [])
        if len(old_ids) != 1 or len(new_ids) != 1:
            continue
        old_id, new_id = old_ids[0], new_ids[0]
        case = new_cases.pop(new_id)
        saved_case = deleted_cases.pop(old_id)

        # Drop the sub-resource changes staged for the case as new, under its new id.
        for changes in (new_resources, updated_resources, deleted_resources):
            for sub_type in _TEST_CASE_SUBRESOURCE_TYPES:
                for sub_id in list(changes.get(sub_type, {})):
                    if sub_id == new_id or sub_id.startswith(f"{new_id}:"):
                        changes[sub_type].pop(sub_id)

        case.resource_id = old_id
        for sub_resource in (
            case.assertions,
            case.tags,
            case.sip_headers,
            case.integration_attributes,
        ):
            if sub_resource is not None:
                sub_resource.resource_id = old_id
        updated_resources.setdefault(TestCase, {})[old_id] = case
        sub_changes = case.get_new_updated_deleted_subresources(old_resource=saved_case)
        for changes, sub_resources in zip(
            (new_resources, updated_resources, deleted_resources), sub_changes
        ):
            for sub_resource in sub_resources:
                changes.setdefault(type(sub_resource), {})[sub_resource.resource_id] = sub_resource

        state_cases = state.setdefault(TestCase, {})
        state_cases.pop(new_id, None)
        state_cases[old_id] = case

    for changes in (new_resources, updated_resources, deleted_resources):
        for resource_type in (TestCase, *_TEST_CASE_SUBRESOURCE_TYPES):
            if resource_type in changes and not changes[resource_type]:
                changes.pop(resource_type)


_TEST_CASE_SUBRESOURCE_TYPES = (
    TestCaseAssertion,
    TestCaseTags,
    TestCaseSipHeaders,
    TestCaseIntegrationAttributes,
    TestCaseApiOperationMock,
)


def group_outbound_campaign_changes(
    state: ResourceMap,
    new_resources: ResourceMap,
    updated_resources: ResourceMap,
    deleted_resources: ResourceMap,
    pre_push_updated_resources: ResourceMap,
    pre_push_deleted_resources: ResourceMap,
) -> None:
    """Finish the campaign changes in place.

    The steps run in this order because each relies on the ids the one before settles. A
    renamed folder keeps its campaign's and nodes' ids first, so a node that changes type is
    replaced under its kept campaign. Code changes then go out with the node that has its
    final id. Deleting a campaign deletes its nodes with it, and the label changes left go
    before any create, since Agent Studio refuses a label another node still has.
    """
    pair_renamed_campaigns(state, new_resources, updated_resources, deleted_resources)
    replace_retyped_campaign_nodes(state, new_resources, updated_resources, deleted_resources)
    push_campaign_code_with_nodes(state, new_resources, updated_resources, deleted_resources)
    prune_cascade_deleted_campaign_nodes(deleted_resources)
    relabel_campaign_nodes_first(
        updated_resources, deleted_resources, pre_push_updated_resources, pre_push_deleted_resources
    )
    drop_settings_only_campaign_updates(updated_resources)


def _nodes_by_pairing_key(
    nodes: dict[str, OutboundCampaignNode],
) -> dict[tuple[Optional[str], Optional[str]], OutboundCampaignNode]:
    return {node_pairing_key(node): node for node in nodes.values()}


def pair_renamed_campaigns(
    state: ResourceMap,
    new_resources: ResourceMap,
    updated_resources: ResourceMap,
    deleted_resources: ResourceMap,
) -> None:
    """Push a renamed campaign folder as an update of the saved campaign, keeping its ids.

    The folder name comes from the campaign name, so a rename reads as a delete and a create,
    which would replace a live campaign with a new one. A new campaign whose nodes have exactly
    the same names and types as one deleted campaign, and as no other, takes that campaign's id
    and each node takes the id of the node with its name. The trigger is matched by type alone,
    so it may be renamed too. Anything else stays a delete and a create, which validation refuses.
    """
    for old_id, new_id in paired_campaigns(new_resources, deleted_resources).items():
        _carry_campaign_ids(
            state, new_resources, updated_resources, deleted_resources, new_id, old_id
        )

    _prune_empty(
        (new_resources, updated_resources, deleted_resources),
        (OutboundCampaign, OutboundCampaignSettings, OutboundCampaignNode),
    )


def _carry_campaign_ids(
    state: ResourceMap,
    new_resources: ResourceMap,
    updated_resources: ResourceMap,
    deleted_resources: ResourceMap,
    new_id: str,
    old_id: str,
) -> None:
    campaign = new_resources[OutboundCampaign].pop(new_id)
    saved_campaign = deleted_resources[OutboundCampaign].pop(old_id)
    new_resources.get(OutboundCampaignSettings, {}).pop(new_id, None)
    campaign.resource_id = old_id
    campaign.status = saved_campaign.status
    updated_resources.setdefault(OutboundCampaign, {})[old_id] = campaign
    _stage(
        (new_resources, updated_resources, deleted_resources),
        campaign.get_new_updated_deleted_subresources(old_resource=saved_campaign),
    )
    state_campaigns = state.setdefault(OutboundCampaign, {})
    state_campaigns.pop(new_id, None)
    state_campaigns[old_id] = campaign

    saved_nodes = _nodes_by_pairing_key(campaign_nodes(deleted_resources, old_id))
    new_nodes = _nodes_by_pairing_key(campaign_nodes(new_resources, new_id))
    carried_ids = {node.node_id: saved_nodes[key].node_id for key, node in new_nodes.items()}
    for key, node in new_nodes.items():
        node.data = map_route_targets(node.data, lambda target: carried_ids.get(target, target))
        _carry_node_id(
            state, new_resources, updated_resources, deleted_resources, node, saved_nodes[key]
        )


def _carry_node_id(
    state: ResourceMap,
    new_resources: ResourceMap,
    updated_resources: ResourceMap,
    deleted_resources: ResourceMap,
    node: OutboundCampaignNode,
    saved: OutboundCampaignNode,
) -> None:
    new_resources[OutboundCampaignNode].pop(node.resource_id)
    deleted_resources[OutboundCampaignNode].pop(saved.resource_id)
    state_nodes = state.setdefault(OutboundCampaignNode, {})
    state_nodes.pop(node.resource_id, None)
    node.resource_id = saved.resource_id
    node.position = saved.position
    node.saved_code = saved.code
    node.campaign_published = saved.campaign_published
    state_nodes[node.resource_id] = node
    if node.compute_hash() != saved.compute_hash():
        updated_resources.setdefault(OutboundCampaignNode, {})[node.resource_id] = node


def _remap_campaign_routes(
    state: ResourceMap,
    new_resources: ResourceMap,
    updated_resources: ResourceMap,
    campaign_id: str,
    node_ids: dict[str, str],
) -> None:
    for node in campaign_nodes(state, campaign_id).values():
        data = map_route_targets(node.data, lambda target: node_ids.get(target, target))
        if data == node.data:
            continue
        node.data = data
        if node.resource_id not in new_resources.get(OutboundCampaignNode, {}):
            updated_resources.setdefault(OutboundCampaignNode, {})[node.resource_id] = node


def replace_retyped_campaign_nodes(
    state: ResourceMap,
    new_resources: ResourceMap,
    updated_resources: ResourceMap,
    deleted_resources: ResourceMap,
) -> None:
    """Push a node whose type changed as a delete and a create under a new id.

    Agent Studio refuses to change a node's type, so the node is replaced as a rename would
    replace it, and the routes leading to it follow it to its new id. Validation lets the
    trigger change type only when the campaign has another trigger.
    """
    updated_nodes = updated_resources.get(OutboundCampaignNode, {})
    for resource_id, node in list(updated_nodes.items()):
        node_type = node.data.get("type")
        if node.saved_type in (None, node_type):
            continue
        updated_nodes.pop(resource_id)
        saved = copy.copy(node)
        saved.data = {**node.data, "type": node.saved_type}
        deleted_resources.setdefault(OutboundCampaignNode, {})[resource_id] = saved
        old_node_id = node.node_id
        state_nodes = state.setdefault(OutboundCampaignNode, {})
        state_nodes.pop(resource_id, None)
        node.resource_id = f"{node.campaign_id}:{node_type}-{uuid.uuid4()}"
        node.saved_type = None
        state_nodes[node.resource_id] = node
        new_resources.setdefault(OutboundCampaignNode, {})[node.resource_id] = node
        _remap_campaign_routes(
            state,
            new_resources,
            updated_resources,
            node.campaign_id,
            {old_node_id: node.node_id},
        )
    _prune_empty((updated_resources,), (OutboundCampaignNode,))


def push_campaign_code_with_nodes(
    state: ResourceMap,
    new_resources: ResourceMap,
    updated_resources: ResourceMap,
    deleted_resources: ResourceMap,
) -> None:
    """Send a change to a campaign function file as an update of its node.

    Function files have no command of their own, the same way ASR settings go out by
    section. A node being created or deleted carries its code already. Each function file
    also takes its node's final id, so a later pull matches the two.
    """
    node_ids = {
        (node.campaign_folder, function_file_stem(node.name)): node.resource_id
        for node in state.get(OutboundCampaignNode, {}).values()
    }
    if OutboundCampaignFunction in state:
        functions = {}
        for function in state[OutboundCampaignFunction].values():
            function.resource_id = node_ids.get(
                (function.campaign_folder, function_file_stem(function.name)),
                function.resource_id,
            )
            functions[function.resource_id] = function
        state[OutboundCampaignFunction] = functions
    touched = {
        (function.campaign_folder, function_file_stem(function.name))
        for changes in (new_resources, updated_resources, deleted_resources)
        for function in changes.pop(OutboundCampaignFunction, {}).values()
    }
    if not touched:
        return
    created = new_resources.get(OutboundCampaignNode, {})
    for node in state.get(OutboundCampaignNode, {}).values():
        if (
            (node.campaign_folder, function_file_stem(node.name)) in touched
            and node.resource_id not in created
            and node.code != (node.saved_code or "")
        ):
            updated_resources.setdefault(OutboundCampaignNode, {})[node.resource_id] = node


def relabel_campaign_nodes_first(
    updated_resources: ResourceMap,
    deleted_resources: ResourceMap,
    pre_push_updated_resources: ResourceMap,
    pre_push_deleted_resources: ResourceMap,
) -> None:
    """Send node deletes and label changes before anything is created.

    Agent Studio refuses a label another node still has. A kept node changes label when its
    trigger is renamed, when pull gave it a name, or when only the case or punctuation of its
    name changed. A node taking a label other relabelled nodes give up goes after them.
    """
    if OutboundCampaignNode in deleted_resources:
        pre_push_deleted_resources.setdefault(OutboundCampaignNode, {}).update(
            deleted_resources.pop(OutboundCampaignNode)
        )
    updated_nodes = updated_resources.get(OutboundCampaignNode, {})
    relabelled = [
        updated_nodes.pop(resource_id)
        for resource_id, node in list(updated_nodes.items())
        if node.saved_label is not None and node.saved_label != node.name
    ]
    by_id = {node.resource_id: node for node in relabelled}
    givers: dict[tuple[str, str], list[str]] = {}
    for node in relabelled:
        givers.setdefault((node.campaign_id, node.saved_label.strip()), []).append(node.resource_id)
    order = graphlib.TopologicalSorter(
        {
            node.resource_id: [
                giver
                for giver in givers.get((node.campaign_id, node.name.strip()), [])
                if giver != node.resource_id
            ]
            for node in relabelled
        }
    )
    try:
        ordered = list(order.static_order())
    except graphlib.CycleError:
        ordered = list(by_id)
    for resource_id in ordered:
        pre_push_updated_resources.setdefault(OutboundCampaignNode, {})[resource_id] = by_id[
            resource_id
        ]
    _prune_empty((updated_resources,), (OutboundCampaignNode,))


def drop_settings_only_campaign_updates(updated_resources: ResourceMap) -> None:
    """Send a campaign update only when its name or description changed.

    Settings go out as their own command, so a settings-only change needs no campaign update.
    """
    campaigns = updated_resources.get(OutboundCampaign, {})
    for resource_id, campaign in list(campaigns.items()):
        if campaign.saved_identity == campaign.identity:
            campaigns.pop(resource_id)
    _prune_empty((updated_resources,), (OutboundCampaign,))


def prune_cascade_deleted_campaign_nodes(deleted_resources: ResourceMap) -> None:
    """Drop node deletes covered by deleting their campaign, which deletes its nodes too."""
    deleted_campaign_ids = set(deleted_resources.get(OutboundCampaign, {}))
    nodes = deleted_resources.get(OutboundCampaignNode, {})
    for resource_id, node in list(nodes.items()):
        if isinstance(node, OutboundCampaignNode) and node.campaign_id in deleted_campaign_ids:
            nodes.pop(resource_id)
    _prune_empty((deleted_resources,), (OutboundCampaignNode,))


def _stage(
    changes: tuple[ResourceMap, ResourceMap, ResourceMap],
    sub_changes: tuple[list[Resource], list[Resource], list[Resource]],
) -> None:
    for resource_map, sub_resources in zip(changes, sub_changes):
        for sub_resource in sub_resources:
            resource_map.setdefault(type(sub_resource), {})[sub_resource.resource_id] = sub_resource


def _prune_empty(changes: tuple[ResourceMap, ...], resource_types: tuple[type, ...]) -> None:
    for resource_map in changes:
        for resource_type in resource_types:
            if resource_type in resource_map and not resource_map[resource_type]:
                resource_map.pop(resource_type)


def push_asr_settings_by_section(
    new_resources: ResourceMap, updated_resources: ResourceMap
) -> None:
    """Drop ASR settings themselves from the push.

    Each section is pushed as its own voice channel sub-resource, so the file has no
    command of its own.
    """
    new_resources.pop(AsrSettings, None)
    updated_resources.pop(AsrSettings, None)


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
    # Add known attributes to any new variant to give it a default value. A typed
    # attribute cannot hold "", so its seed is a native null; the real value follows
    # in the attribute update pushed straight after.
    deleted_attribute_ids = set(deleted_resources.get(VariantAttribute, {}).keys())
    for variant in new_resources.get(Variant, {}).values():
        if not isinstance(variant, Variant):
            raise TypeError(f"Variant is not a Variant: {variant}")
        variant.attribute_values = {
            attribute_id: "" if attribute.kind == AttributeKind.STRING else None
            for attribute_id, attribute in current_resources.get(VariantAttribute, {}).items()
            if attribute_id not in deleted_attribute_ids
        }


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
