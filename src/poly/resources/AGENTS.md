# Resource layer

Rules for `src/poly/resources/`. The repo-wide rules in the root `AGENTS.md` still apply.

Only things that appear in the Agent Studio project projection belong here. Anything else
(API keys, conversations, metrics definitions) goes through `project.py` and the handlers.

## Adding a resource type

The `add-resource-type` skill walks through this end to end.

1. Create `src/poly/resources/<name>.py` with a class subclassing `YamlResource` (or
   `Resource` / `MultiResourceYamlResource`). Start from a similar existing resource, e.g.
   `entities.py`. For a resource scoped to a parent, follow `FlowStep` in `flows.py`.
2. Decorate it with `@register_resource("<name>")` (`resource.py`). That one decorator fills
   `RESOURCE_NAME_TO_CLASS`, `RESOURCE_CLASS_TO_NAME` and `PROJECTION_REGISTRY`; there is no
   other registry to edit.
3. Implement `from_projection` as a classmethod on the resource. It parses its own keys out of
   the raw projection, and `load_resources_from_projection` collects it automatically.
4. Import the class in `resources/__init__.py`. That import is what runs the decorator.
5. If the file name is a cleaned version of the resource name (as for `Topic` and `ChildTopic`),
   add the class to the name-recovery condition in `AgentStudioProject.find_new_kept_deleted`.
6. Add tests to `src/poly/tests/resources_test.py` (YAML round-trip, validation, `file_path`,
   `from_projection`), and add an example to `src/poly/tests/test_projects/test_project/`.
7. Document the YAML shape in `src/poly/docs/` (for `poly docs`) and
   `docs/docs/reference/resources/`.

## Rules for resource code

- `validate` should catch everything the platform would reject, so a bad push fails locally.
- `to_yaml_dict` / `from_yaml_dict` must round-trip: a pull followed by a push sends nothing.
- Read and write YAML through `resource_utils` (`load_yaml`, `dump_yaml`) so comments and key
  order survive.
- A resource the user can't access is kept as a slim resource for reference mapping, and never
  written to disk or deleted.
