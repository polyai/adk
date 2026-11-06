"""What resources refer to, and which IDs and names exist now.

A saved resource holds IDs where its file shows names. While every ID it refers to still
exists, and no name it couldn't resolve has appeared, an unedited file still means exactly its
saved resource, so the ADK needn't read it.

Copyright PolyAI Limited
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

import poly.resources.resource_utils as utils
from poly.resources.flows import BaseFlowStep, FlowConfig
from poly.resources.resource import ResourceMapping

# (kind, value). The kind is a template reference name such as "global_functions", a resource
# class name such as "Variant", or one of the shared kinds below. The value is an ID, or a name
# that didn't resolve.
Reference = tuple[str, str]

# Any flow step (FlowStep or FunctionStep), by "<flow ID>_<step ID>".
FLOW_STEP = "flow_step"
# A flow as code imports it: functions.<cleaned flow ID>, flows.<cleaned flow name>.functions.
FLOW_MODULE = "flow_module"


@dataclass
class KnownIds:
    """The IDs that exist now, and the IDs each name has, per reference kind."""

    ids: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    names: dict[str, dict[str, set[str]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(set))
    )

    def _add(self, kind: str, resource_id: str, name: str) -> None:
        self.ids[kind].add(resource_id)
        self.names[kind][name].add(resource_id)

    @classmethod
    def from_mappings(cls, mappings: Iterable[ResourceMapping]) -> "KnownIds":
        """Index mappings by class name, template reference name and the shared kinds."""
        known = cls()
        for mapping in mappings:
            known._add(mapping.resource_type.__name__, mapping.resource_id, mapping.resource_name)
            if reference := utils.PREFIX_TO_REFERENCE.get(mapping.resource_prefix):
                known._add(reference, mapping.resource_id, mapping.resource_name)
            if issubclass(mapping.resource_type, BaseFlowStep):
                known._add(FLOW_STEP, mapping.resource_id, mapping.resource_name)
            if mapping.resource_type is FlowConfig:
                known._add(
                    FLOW_MODULE,
                    utils.clean_name(mapping.resource_id),
                    utils.clean_name(mapping.resource_name),
                )
        return known

    def exists(self, kind: str, value: str) -> bool:
        """Whether `value` is the ID of something of this kind."""
        return value in self.ids.get(kind, ())

    def name_exists(self, kind: str, value: str) -> bool:
        """Whether something of this kind is now named `value`."""
        return bool(self.names.get(kind, {}).get(value))

    def resolve(self, kind: str, value: str) -> tuple[list[str], bool]:
        """Return the IDs `value` stands for now, and whether it resolved at all.

        An ID stands for itself. A name stands for the IDs of everything with that name.
        """
        if self.exists(kind, value):
            return [value], True
        ids = self.names.get(kind, {}).get(value)
        return sorted(ids or ()), bool(ids)
