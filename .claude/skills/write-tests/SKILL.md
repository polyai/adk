---
name: write-tests
description: Write readable tests for new or changed ADK code and show that coverage of the touched modules didn't drop. Use after implementing a feature or fix in the polyai-adk repo, or when asked to add test coverage.
metadata:
  internal: true
---

# Write tests for an ADK change

## 1. Measure first

Run `uv run pytest src/poly/tests/ --cov=poly --cov-report=term-missing` and note the coverage
of each module the change touches.

## 2. Write the tests

- **Placement:** add to the existing file and class for the area:
  - `resources_test.py` for resources
  - `project_test.py` for project logic
  - `cli_test.py` for argument parsing and command output
  - `tests/api/` for handlers
  - `tests/call/` for voice calls
  - The `*_test.py` file named after the feature (`metrics_test.py`, `rtc_test.py`, …)

  Only create a new file or class when nothing fits.
- **Fixtures:** use real objects and the fixture projects in `src/poly/tests/test_projects/`.
  When a resource gains a field or a new resource type is added, add an example to
  `test_projects/test_project/` as well.
- **Mocks:** mock only at the API or filesystem boundary, one `@patch` per test where possible.
  Don't assert that a mock was called when you could assert on the result.
- **Style:** `unittest.TestCase` classes. Names read as `test_<scenario>_<expected_outcome>`,
  with one behaviour per test and a short docstring.
- **Cover:** the happy path, edge cases (empty, `None`, missing fields), errors (`ValueError` for
  bad input), and a YAML round-trip (`to_yaml_dict` → `from_yaml_dict`) for resources.
- Never test generated code under `handlers/protobuf/` or `types/`.

## 3. Measure again

Re-run the coverage command and the full suite. Then run `uv run ruff check . --fix` and
`uv run ruff format .`.

## Report

The tests you added (file and class), and the before → after coverage for each touched module.
If coverage dropped, say which lines are uncovered and why.
