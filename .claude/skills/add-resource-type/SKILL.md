---
name: add-resource-type
description: Add a new Agent Studio resource type to the ADK, covering the class, registration, projection parsing, tests, fixture and docs. Use when asked to support a new resource in the polyai-adk repo.
metadata:
  internal: true
---

# Add a resource type

Read `src/poly/resources/AGENTS.md` first; this skill expands its checklist.

## 1. Study an existing resource

- `src/poly/resources/entities.py`: a simple `YamlResource`.
- `src/poly/resources/resource.py`: the base classes, `register_resource` and
  `load_resources_from_projection`.
- `src/poly/resources/__init__.py`: where classes are imported.
- `AgentStudioProject.find_new_kept_deleted` and `_make_resource_mapping` in `src/poly/project.py`:
  how resource types are handled generically.
- For a resource that belongs to a parent (a step in a flow, an overwrite in a variant):
  `FlowStep` in `flows.py`. It stores the parent id and name as fields and resolves them from the
  enclosing folder name in `read_local_resource`.

## 2. Write the class

Create `src/poly/resources/<name>.py`:
- Subclass `YamlResource` (or `Resource` / `MultiResourceYamlResource`) and implement the
  abstract methods:
  - `command_type`
  - `build_create_proto`, `build_update_proto`, `build_delete_proto`
  - `file_path`, `raw`, `validate`
  - `to_yaml_dict`, `from_yaml_dict`
  - `from_projection`, `read_local_resource`, `discover_resources`
- Add `make_pretty` / `from_pretty` if names or IDs need substituting, and
  `get_resource_prefix()` if other resources can reference this one.
- Decorate it with `@register_resource("<name>")`. That fills `RESOURCE_NAME_TO_CLASS`,
  `RESOURCE_CLASS_TO_NAME` and `PROJECTION_REGISTRY`. There is no other registration step.
- `from_projection` is a classmethod that parses its own keys out of the raw projection dict.
- `validate` should reject everything the platform would reject.

## 3. Wire it in

- Import the class in `src/poly/resources/__init__.py`, which makes the decorator run.
- If the file name is a cleaned version of the real name (accents, casing or punctuation
  stripped, like `Topic` and `ChildTopic`), add the class to the name-recovery condition in
  `find_new_kept_deleted` in `src/poly/project.py`, and import it there.

## 4. Test it

In `src/poly/tests/resources_test.py` (see the `write-tests` skill), cover:
- the YAML round-trip
- `validate` (valid and invalid)
- `file_path`
- `from_projection`

For a parent-scoped resource, also test that `read_local_resource` resolves the parent from the
folder name and copes with an empty `resource_mappings` list.

Add an example of the resource to `src/poly/tests/test_projects/test_project/`.

## 5. Document it

- `src/poly/docs/<name>.md`: the YAML shape, served by `poly docs`.
- `docs/docs/reference/resources/`: follow the `AGENTS.md` in that directory, and add the page to
  `docs/mkdocs.yml`.
- If a user skill in `skills/` describes the area, update it.

## 6. Check

`uv run ruff check . --fix`, `uv run ruff format .`, then the `ci-check` skill. Never touch
`src/poly/handlers/protobuf/` or `src/poly/types/`; if the protobufs lack the resource, stop and
say so.
