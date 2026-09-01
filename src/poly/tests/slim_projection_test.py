"""Tests for handling auth-filtered ("slim") projections

The API filters projections per slice. A user without read access to a slice
gets a skeleton carrying only identity fields - ids, names, references - with
the substantive fields stripped. A resource the user cannot read is not
represented locally at all: no file, no baseline entry. It looks like a remote
delete, which is honest, since from that user's vantage point it does not exist.

Copyright PolyAI Limited
"""

import unittest

import poly.resources  # noqa: F401  - triggers resource registration
from poly.resources.function import Function
from poly.resources.resource import PROJECTION_REGISTRY, RESOURCE_CLASS_TO_NAME
from poly.resources.sms import SMSTemplate
from poly.resources.topic import Topic

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
# just as usable as - a full one. Nothing else should survive.
TYPES_READABLE_FROM_SKELETON = {"variables"}


class SkeletonProjectionParsing(unittest.TestCase):
    """Every registered resource must tolerate an auth-filtered projection."""

    def test_no_resource_type_raises(self):
        """A slim projection must never abort the pull."""
        for resource_cls in PROJECTION_REGISTRY:
            name = RESOURCE_CLASS_TO_NAME[resource_cls]
            with self.subTest(resource=name):
                resource_cls.from_projection(SKELETON_PROJECTION)

    def test_only_fully_readable_types_are_represented(self):
        """Anything the user cannot read is hidden rather than partly built."""
        represented = {
            RESOURCE_CLASS_TO_NAME[cls]
            for cls in PROJECTION_REGISTRY
            if cls.from_projection(SKELETON_PROJECTION)
        }
        self.assertEqual(represented, TYPES_READABLE_FROM_SKELETON)

    def test_represented_resources_survive_downstream_operations(self):
        """Whatever is kept must be usable, not a half-built object.

        compute_hash and file_path run on every pull and push, so a resource
        that parses but blows up here fails far from the cause - which is how
        filtered entities and additional_languages used to surface.
        """
        for resource_cls in PROJECTION_REGISTRY:
            name = RESOURCE_CLASS_TO_NAME[resource_cls]
            for resource in resource_cls.from_projection(SKELETON_PROJECTION).values():
                with self.subTest(resource=name):
                    resource.compute_hash()
                    resource.validate()


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
        self.assertEqual(list(functions), ["TF-1"])


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


if __name__ == "__main__":
    unittest.main()
