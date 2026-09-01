"""Tests for handling auth-filtered ("slim") projections

The API filters projections per slice. A user without read access to a slice
gets a skeleton carrying only identity fields - ids, names, references - with
the substantive fields stripped. A resource the user cannot read is not
represented locally at all: no file, no baseline entry. It looks like a remote
delete, which is honest, since from that user's vantage point it does not exist.

Copyright PolyAI Limited
"""

import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import poly.resources  # noqa: F401  - triggers resource registration
import poly.resources.resource_utils as resource_utils
from poly.project import AgentStudioProject
from poly.resources.entities import Entity
from poly.resources.function import Function
from poly.resources.resource import (
    PROJECTION_REGISTRY,
    RESOURCE_CLASS_TO_NAME,
    MultiResourceYamlResource,
    ResourceMapping,
    load_resources_from_projection,
)
from poly.resources.sms import SMSTemplate
from poly.resources.topic import Topic
from poly.resources.variable import Variable
from poly.utils.prepush import fix_orphaned_variables

# A projection where every slice came back auth-filtered, built from the fields
# each slice declares in its alwaysPresentJsonPaths allow-list. Slices whose
# allow-list is empty are omitted entirely, as the API omits them.
SKELETON_PROJECTION = {
    "documents": {
        "documents": {"ids": ["CONTEXT.MD"], "entities": {"CONTEXT.MD": {"path": "CONTEXT.MD"}}}
    },
    "knowledgeBase": {
        "topics": {
            "ids": ["TOPIC-1"],
            "entities": {"TOPIC-1": {"id": "TOPIC-1", "name": "billing", "references": {}}},
        },
        "uninstantiatedTopics": {"ids": [], "entities": {}},
    },
    "entities": {
        "entities": {
            "ids": ["ENTITY-1"],
            "entities": {"ENTITY-1": {"id": "ENTITY-1", "name": "customer_name"}},
        }
    },
    "functions": {
        "functions": {
            "ids": ["FUNCTION-1"],
            "entities": {
                "FUNCTION-1": {
                    "id": "FUNCTION-1",
                    "name": "lookup_order",
                    "references": {},
                    "parameters": {"ids": ["P1"], "entities": {"P1": {"id": "P1", "name": "p"}}},
                    "latencyControl": {"delayResponses": {"ids": []}},
                }
            },
        }
    },
    "specialFunctions": {
        "startFunction": {"id": "SF-1", "parameters": {"ids": [], "entities": {}}},
        "endFunction": {"id": "EF-1", "parameters": {"ids": [], "entities": {}}},
    },
    "flows": {
        "flows": {
            "ids": ["FLOW-1"],
            "entities": {
                "FLOW-1": {
                    "id": "FLOW-1",
                    "name": "MyFlow",
                    "steps": {
                        "entities": {
                            "STEP-1": {"id": "STEP-1", "name": "greet", "references": {}},
                            "STEP-2": {"id": "STEP-2", "name": "lookup", "references": {}},
                        }
                    },
                    "transitionFunctions": {
                        "ids": ["TF-1"],
                        "entities": {"TF-1": {"id": "TF-1", "name": "go", "references": {}}},
                    },
                }
            },
        }
    },
    "handoff": {
        "handoffs": {
            "ids": ["HO-1"],
            "entities": {"HO-1": {"id": "HO-1", "name": "agent", "references": {}}},
        }
    },
    "sms": {
        "templates": {
            "ids": ["SMS-1"],
            "entities": {"SMS-1": {"id": "SMS-1", "name": "confirm", "references": {}}},
        }
    },
    "variables": {
        "variables": {
            "ids": ["VAR-1"],
            "entities": {"VAR-1": {"id": "VAR-1", "name": "order_id", "references": {}}},
        }
    },
    "variantManagement": {
        "attributes": {
            "ids": ["ATTR-1"],
            "entities": {"ATTR-1": {"id": "ATTR-1", "name": "brand", "references": {}}},
        },
        # Variant names are exposed to filtered readers so that test cases, gated
        # on a different permission, can resolve the variant they run against.
        "variants": {"ids": ["V-1"], "entities": {"V-1": {"id": "V-1", "name": "Default"}}},
        "variantAttributeValues": {"ids": ["V-1"], "entities": {"V-1": {"id": "V-1"}}},
    },
    # Likewise translation keys, which topics and behaviour rules embed as {{tn:}}.
    "translations": {
        "translations": {
            "ids": ["TN-1"],
            "entities": {"TN-1": {"id": "TN-1", "translationKey": "greeting"}},
        }
    },
    "testing": {"testCases": {"ids": ["TC-1"], "entities": {"TC-1": {"id": "TC-1"}}}},
    "pronunciations": {"pronunciations": {"ids": ["PR-1"], "entities": {"PR-1": {"id": "PR-1"}}}},
    "keyphraseBoosting": {
        "keyphraseBoosting": {"ids": ["KB-1"], "entities": {"KB-1": {"id": "KB-1"}}}
    },
    "stopKeywords": {"filters": {"ids": ["SK-1"], "entities": {"SK-1": {"id": "SK-1"}}}},
    "experimentalConfig": {
        "experimentalConfigs": {"ids": ["default"], "entities": {"default": {"id": "default"}}}
    },
    "channels": {"webChat": {"status": 1}},
    "languages": {"additionalLanguages": {"ids": ["fr"], "entities": {"fr": {"id": "fr"}}}},
    "csat": {"enabled": True},
    "webchatCsat": {
        "enabled": True,
        "questions": {"ids": ["Q1"], "entities": {"Q1": {"id": "Q1"}}},
    },
    "childOverwrites": {"knowledgeBase": {"topics": {"ids": [], "entities": {}}}},
}

# Variables and their names are the whole of the Variable resource, and the
# variables slice keeps both, so a filtered slice is indistinguishable from - and
# just as usable as - a full one.
TYPES_READABLE_FROM_SKELETON = {"variables"}

# Types whose ids appear inside a resource gated on a *different* permission.
# These are kept as identity-only stubs so those references still resolve to a
# name; everything else withheld is dropped entirely.
TYPES_KEPT_AS_SLIM = {
    "entities",
    "functions",
    "handoffs",
    "sms_templates",
    "translations",
    "variant_attributes",
    "variants",
}


class SkeletonProjectionParsing(unittest.TestCase):
    """Every registered resource must tolerate an auth-filtered projection."""

    @staticmethod
    def _parse(resource_cls):
        return resource_cls.from_projection(SKELETON_PROJECTION)

    def test_no_resource_type_raises(self):
        """A slim projection must never abort the pull."""
        for resource_cls in PROJECTION_REGISTRY:
            name = RESOURCE_CLASS_TO_NAME[resource_cls]
            with self.subTest(resource=name):
                self._parse(resource_cls)

    def test_only_referenced_types_survive_as_slim(self):
        """Withheld resources are dropped unless something else points at them."""
        real, slim = set(), set()
        for resource_cls in PROJECTION_REGISTRY:
            name = RESOURCE_CLASS_TO_NAME[resource_cls]
            for resource in self._parse(resource_cls).values():
                (slim if resource.slim else real).add(name)

        self.assertEqual(real, TYPES_READABLE_FROM_SKELETON)
        self.assertEqual(slim, TYPES_KEPT_AS_SLIM)

    def test_readable_resources_survive_downstream_operations(self):
        """Whatever is kept in full must be usable, not a half-built object.

        compute_hash and file_path run on every pull and push, so a resource
        that parses but blows up here fails far from the cause - which is how
        filtered entities and additional_languages used to surface.
        """
        for resource_cls in PROJECTION_REGISTRY:
            name = RESOURCE_CLASS_TO_NAME[resource_cls]
            for resource in self._parse(resource_cls).values():
                if resource.slim:
                    continue
                with self.subTest(resource=name):
                    resource.compute_hash()
                    resource.validate()

    def test_slim_resources_can_be_turned_into_mappings(self):
        """A stub's only job is to feed the id<->name lookup.

        file_path and get_resource_prefix are what _make_resource_mapping needs,
        and both are derived from fields the skeleton actually provides. Nothing
        else is required of a stub - notably not compute_hash or validate, which
        would be operating on absent data.
        """
        for resource_cls in PROJECTION_REGISTRY:
            name = RESOURCE_CLASS_TO_NAME[resource_cls]
            for resource in self._parse(resource_cls).values():
                if not resource.slim:
                    continue
                with self.subTest(resource=name):
                    self.assertTrue(resource.resource_id)
                    self.assertTrue(resource.name)
                    resource.get_resource_prefix(file_path=resource.file_path)


class FalsyGuardValuesAreReadable(unittest.TestCase):
    """The guards test for a field's presence, never its truthiness.

    An empty string or False is readable data. Getting this wrong would hide
    resources the user can perfectly well read - the failure mode this whole
    change exists to prevent, just in the opposite direction.
    """

    def test_empty_topic_content_is_kept(self):
        projection = {
            "knowledgeBase": {
                "topics": {"entities": {"TOPIC-1": {"name": "empty", "content": "", "actions": ""}}}
            }
        }
        self.assertEqual(list(Topic.from_projection(projection)), ["TOPIC-1"])

    def test_inactive_sms_template_is_a_read_not_a_hide(self):
        """active=False is a deactivated template, not a filtered one.

        Both end up absent, but only the filtered case should log - so the
        guard must see the field and fall through to the "active" check.
        """
        projection = {
            "sms": {"templates": {"entities": {"SMS-1": {"name": "old", "active": False}}}}
        }
        with self.assertNoLogs("poly.resources.sms", level="DEBUG"):
            self.assertEqual(SMSTemplate.from_projection(projection), {})


class FunctionSliceIndependence(unittest.TestCase):
    """Functions are drawn from three slices gated on two different permissions.

    "functions" gates the special and global function slices; "jupiter_flows"
    gates transition functions. Losing one must not hide the others.
    """

    @staticmethod
    def _full_function(func_id, name):
        return {"id": func_id, "name": name, "description": "", "code": "pass"}

    def test_unreadable_transition_functions_keep_global_functions(self):
        projection = {
            "functions": {
                "functions": {"entities": {"FN-1": self._full_function("FN-1", "readable")}}
            },
            "flows": {
                "flows": {
                    "entities": {
                        "FLOW-1": {
                            "id": "FLOW-1",
                            "name": "MyFlow",
                            "transitionFunctions": {
                                "entities": {"TF-1": {"id": "TF-1", "name": "hidden"}}
                            },
                        }
                    }
                }
            },
        }
        functions = Function.from_projection(projection)
        self.assertEqual(list(functions), ["FN-1"])

    def test_unreadable_global_functions_keep_transition_functions(self):
        projection = {
            "functions": {"functions": {"entities": {"FN-1": {"id": "FN-1", "name": "hidden"}}}},
            "flows": {
                "flows": {
                    "entities": {
                        "FLOW-1": {
                            "id": "FLOW-1",
                            "name": "MyFlow",
                            "transitionFunctions": {
                                "entities": {"TF-1": self._full_function("TF-1", "readable")}
                            },
                        }
                    }
                }
            },
        }
        functions = Function.from_projection(projection)
        # The global function is referenced by topics and phrase filters, so it
        # is kept as a stub rather than dropped - but only the readable one is
        # a real, file-backed resource.
        self.assertEqual(
            {f_id: f.slim for f_id, f in functions.items()}, {"TF-1": False, "FN-1": True}
        )


class WithheldSlicesAreReported(unittest.TestCase):
    """A withheld slice arrives as nothing at all, so the absence is the signal."""

    def test_absent_slice_logs_and_yields_nothing(self):
        with self.assertLogs("poly.resources.topic", level="DEBUG"):
            self.assertEqual(Topic.from_projection({}), {})

    def test_present_but_empty_slice_is_silent(self):
        """An authorised slice with no entities is emitted, just empty - not withheld."""
        projection = {"knowledgeBase": {"topics": {"entities": {}}}}
        with self.assertNoLogs("poly.resources.topic", level="DEBUG"):
            self.assertEqual(Topic.from_projection(projection), {})


class PrepushDerivationsAreInertWhenHidden(unittest.TestCase):
    """Why the prepush derivations need no read-access handling of their own.

    They compare the baseline against local files, and a slim pull empties both
    together - it rewrites the manifest and deletes the files in one go. So a
    hidden resource is absent from both sides and no derivation can see a delta.
    fix_orphaned_variables is the one that would corrupt server state if it did:
    variableUpdate is gated on jupiter_flows, not functions, so the API would
    accept a reference graph rebuilt from functions the user cannot see.
    """

    def test_no_variable_commands_when_functions_are_hidden(self):
        variable = Variable(resource_id="VAR-1", name="order_id")
        visible = {Variable: {"VAR-1": variable}, Function: {}}
        new, updated, deleted = {}, {}, {}

        fix_orphaned_variables(visible, new, updated, deleted, visible, lambda _: [])

        self.assertEqual((new, updated, deleted), ({}, {}, {}))


class SlimResourcesSurviveTheStatusFile(unittest.TestCase):
    """Slim resources have to outlive the process that pulled them.

    Every command other than pull rehydrates from _gen/.agent_studio_config, so
    a slim resource that is not written there is gone by the next command - and
    with it the id<->name mapping, which makes every reference to a withheld
    resource read back as a raw id and the file look locally modified.
    """

    def _project(self) -> AgentStudioProject:
        resources, slim_resources = load_resources_from_projection(SKELETON_PROJECTION)
        project = AgentStudioProject(
            region="local",
            account_id="ACCOUNT-1",
            project_id="PROJECT-1",
            root_path="/tmp/does-not-need-to-exist",
            resources=resources,
            slim_resources=slim_resources,
            last_updated=datetime(2026, 1, 1),
        )
        project.file_structure_info = project.compute_file_structure_info(project.resources)
        return project

    @staticmethod
    def _slim_ids(project: AgentStudioProject) -> set[tuple[str, str]]:
        return {
            (RESOURCE_CLASS_TO_NAME[mapping.resource_type], mapping.resource_id)
            for mapping in project.slim_resources
        }

    def test_slim_resources_round_trip_through_to_dict(self):
        project = self._project()
        self.assertTrue(self._slim_ids(project), "fixture should produce slim resources")

        reloaded = AgentStudioProject.from_dict(project.to_dict(), project.root_path)

        self.assertEqual(self._slim_ids(reloaded), self._slim_ids(project))

    def test_slim_resources_keep_their_names_when_reloaded(self):
        """The name is the whole point - an id alone resolves nothing."""
        project = self._project()
        names = {m.resource_id: m.resource_name for m in project.slim_resources}
        self.assertTrue(names, "fixture should produce slim resources")

        reloaded = AgentStudioProject.from_dict(project.to_dict(), project.root_path)
        reloaded_names = {m.resource_id: m.resource_name for m in reloaded.slim_resources}

        self.assertEqual(reloaded_names, names)

    def test_from_dict_ignores_keys_from_a_newer_adk(self):
        """The status file outlives any one ADK version.

        A field added by a newer version (or a hand edit) must not turn every
        later command into a TypeError.
        """
        mapping = next(iter(self._project().slim_resources))
        data = {**mapping.to_dict(), "added_in_a_newer_version": True}

        self.assertEqual(ResourceMapping.from_dict(data), mapping)

    def test_from_dict_drops_a_mapping_missing_required_fields(self):
        """A truncated entry loses that one mapping, not the whole command."""
        self.assertIsNone(ResourceMapping.from_dict({"resource_type": "entities"}))

    def test_slim_resources_are_absent_from_file_structure_info(self):
        """No file on disk means no baseline entry.

        Otherwise find_new_kept_deleted sees a known file that discovery can
        never turn up, and reports it deleted on every run.
        """
        project = self._project()
        slim_paths = {m.file_path for m in project.slim_resources}
        self.assertTrue(slim_paths)

        self.assertEqual(slim_paths & set(project.file_structure_info), set())

    def test_slim_resources_are_absent_from_the_resource_map(self):
        """Slim resources are mappings, not resources.

        Leaving them in resources means push tries to serialize a resource
        whose substantive fields were never sent, and save writes a file for
        something the user cannot read.
        """
        project = self._project()
        self.assertTrue(project.slim_resources, "fixture should produce slim resources")

        self.assertEqual(
            [r for resources in project.resources.values() for r in resources.values() if r.slim],
            [],
        )

    def test_slim_resources_are_carried_past_a_rebuild_from_disk(self):
        """A push replaces resources with state re-read from local files.

        Slim resources have no file, so they cannot be in that state - they
        have to survive on slim_resources or they are lost from the status
        file on every push.
        """
        project = self._project()
        expected = self._slim_ids(project)
        self.assertTrue(expected, "fixture should produce slim resources")

        # What push does: swap in state rebuilt from the local files.
        project.resources = {
            resource_type: dict(resources) for resource_type, resources in project.resources.items()
        }

        reloaded = AgentStudioProject.from_dict(project.to_dict(), project.root_path)
        self.assertEqual(self._slim_ids(reloaded), expected)


class PullBaselineKeepsOriginalSlimMappings(unittest.TestCase):
    """The merge baseline must use the slim mappings recorded with it.

    pull_project swaps self.slim_resources for the incoming list before the
    merge runs. If the baseline then resolves references against the incoming
    mappings, a withheld resource renamed remotely renders the baseline with the
    new name while the disk file still carries the old one - a phantom local
    change, surfacing exactly when merge output matters most.
    """

    @staticmethod
    def _mapping(name: str) -> ResourceMapping:
        return ResourceMapping(
            resource_id="ENTITY-1",
            resource_type=Entity,
            resource_name=name,
            file_path=os.path.join("config", "entities.yaml", "entities", name),
            flow_name=None,
            resource_prefix="entity",
            flow_id=None,
        )

    def test_pull_passes_original_and_incoming_slim_lists_separately(self):
        original = [self._mapping("old_name")]
        incoming = [self._mapping("new_name")]

        project = AgentStudioProject(
            region="local",
            account_id="ACCOUNT-1",
            project_id="PROJECT-1",
            root_path=tempfile.mkdtemp(),
            resources={},
            slim_resources=original,
            last_updated=datetime(2026, 1, 1),
        )

        self.addCleanup(patch.stopall)
        mock_api = patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock).start()
        mock_api.pull_resources.return_value = ({}, incoming, {})
        patch.object(AgentStudioProject, "save_config").start()
        mock_update = patch.object(
            AgentStudioProject, "_update_pulled_resources", return_value=[]
        ).start()

        project.pull_project(force=False)

        kwargs = mock_update.call_args.kwargs
        self.assertEqual(kwargs["original_slim_resources"], original)
        self.assertEqual(kwargs["incoming_slim_resources"], incoming)
        self.assertEqual(project.slim_resources, incoming)


class WithheldTypeIsRemovedFromDisk(unittest.TestCase):
    """A type readable on one pull and withheld on the next must leave no file behind.

    Withheld types are absent from incoming_resources entirely, so the local file is
    only removed by the "entire type absent from incoming" pass. That pass batches its
    deletions into the file cache, and a cached entry carries the pre-write mtime - so
    if the cache is not flushed, the deletions never reach disk *and* every later read
    in the same process sees a file state that is not on disk. The visible symptom is
    a force pull that needs running twice before `poly diff` comes back clean.
    """

    READABLE_ENTITIES = {
        "entities": {
            "entities": {
                "ids": ["ENTITY-1"],
                "entities": {
                    "ENTITY-1": {
                        "id": "ENTITY-1",
                        "name": "account_number",
                        "description": "The caller's account number.",
                        "type": "alphanumeric",
                        "config": {"value": {}},
                    }
                },
            }
        }
    }

    def setUp(self):
        self.root_path = tempfile.mkdtemp()
        self.addCleanup(patch.stopall)
        MultiResourceYamlResource._file_cache.clear()
        self.addCleanup(MultiResourceYamlResource._file_cache.clear)

    def _project_with_readable_entities(self) -> AgentStudioProject:
        resources, slim_resources = load_resources_from_projection(self.READABLE_ENTITIES)
        project = AgentStudioProject(
            region="us-1",
            account_id="ACCOUNT-1",
            project_id="PROJECT-1",
            root_path=self.root_path,
            resources=resources,
            slim_resources=slim_resources,
            last_updated=datetime(2026, 1, 1),
        )
        for entity in resources[Entity].values():
            entity.save(self.root_path, resource_name=entity.name, resource_mappings=[])
        project.file_structure_info = project.compute_file_structure_info(project.resources)
        MultiResourceYamlResource._file_cache.clear()
        return project

    @property
    def _entities_file(self) -> str:
        return os.path.join(self.root_path, "config", "entities.yaml")

    def test_one_force_pull_clears_a_type_that_became_withheld(self):
        project = self._project_with_readable_entities()
        self.assertIn("account_number", open(self._entities_file).read())

        withheld, slim_resources = load_resources_from_projection(SKELETON_PROJECTION)
        mock_api = patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock).start()
        mock_api.pull_resources.return_value = (withheld, slim_resources, {})
        patch.object(AgentStudioProject, "save_config").start()

        project.pull_project(force=True)

        self.assertNotIn(
            "account_number",
            open(self._entities_file).read(),
            "one force pull should remove the withheld entity from disk",
        )

    def test_the_file_cache_never_disagrees_with_disk(self):
        """A cache entry that was never flushed hides the real file from everything after it.

        The entry is stamped with the file's pre-write mtime, so the mtime check that is
        supposed to catch staleness reads it as fresh and hands back content that is not
        on disk - which is how discovery came to miss files that were still there.
        """
        project = self._project_with_readable_entities()

        withheld, slim_resources = load_resources_from_projection(SKELETON_PROJECTION)
        mock_api = patch.object(AgentStudioProject, "api_handler", new_callable=MagicMock).start()
        mock_api.pull_resources.return_value = (withheld, slim_resources, {})
        patch.object(AgentStudioProject, "save_config").start()

        project.pull_project(force=True)

        for file_path, (_, cached_dict) in MultiResourceYamlResource._file_cache.items():
            self.assertEqual(
                resource_utils.load_yaml(open(file_path).read()) or {},
                cached_dict,
                f"cached content for {file_path} does not match what is on disk",
            )


if __name__ == "__main__":
    unittest.main()
