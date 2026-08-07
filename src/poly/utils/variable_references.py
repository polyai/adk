"""Computation of variable references from function/function-step code.

Copyright PolyAI Limited
"""

from poly.resources import Function, FunctionStep, Resource, ResourceMapping

# Maps function_type value -> VariableReferences proto field name
FUNCTION_TYPE_TO_VAR_REF_FIELD: dict[str, str] = {
    "global": "functions",
    "start": "start_functions",
    "end": "end_functions",
    "transition": "flow_functions",
    "function_step": "flow_steps",
}


def _iter_functions_with_var_refs(
    resources: dict[type[Resource], dict[str, Resource]],
    resource_mappings: list[ResourceMapping],
):
    """Yield (function, field_name) for every Function/FunctionStep with variable_references."""
    for fn_type in (Function, FunctionStep):
        for fn in resources.get(fn_type, {}).values():
            variable_references = (
                fn.variable_references
                if fn.variable_references is not None
                else fn._extract_variable_references(fn.code, resource_mappings)
            )
            if not variable_references:
                continue
            ft = fn.function_type
            field_name = FUNCTION_TYPE_TO_VAR_REF_FIELD.get(
                ft.value if hasattr(ft, "value") else str(ft), ""
            )
            yield fn.resource_id, field_name, variable_references


def compute_variable_references(
    resources: dict[type[Resource], dict[str, Resource]],
    resource_mappings: list[ResourceMapping],
) -> dict[str, dict[str, dict[str, bool]]]:
    """Return {var_id: {field_name: {fn_id: True}}} built from all functions in resources.

    The result is suitable for populating VariableReferences on Variable objects.
    New functions are included - the backend accepts references to IDs not yet created.
    """
    var_refs: dict[str, dict[str, dict[str, bool]]] = {}
    for fn_id, field_name, variable_references in _iter_functions_with_var_refs(
        resources, resource_mappings
    ):
        for var_id in variable_references:
            var_refs.setdefault(var_id, {}).setdefault(field_name, {})[fn_id] = True
    return var_refs
