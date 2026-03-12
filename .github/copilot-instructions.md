# Project Context

Agent Development Kit (ADK) is a CLI and Python package for managing Agent Studio projects locally. It syncs project configuration (functions, flows, entities, topics, agent settings) between the local filesystem and the Agent Studio Platform via a Git-like workflow. Resources are stored as YAML/Python files; the handlers package is used for API communication.

# Review Checklist

When reviewing PRs:


- **Ignore proto changes** Changes to the proto files shouldn't be reviewed
- **New resource type**: Verify the change includes (1) resource class in `src/poly/resources/`, (2) entry in `RESOURCE_NAME_TO_CLASS` in `project.py`, and (3) `_read_<resource_type>_from_projection` in `SyncClientHandler` plus a call from `_load_resources()` (4) Additional tests in `tests/resources_tests.py`.
- **Output or CLI behavior change**: Verify `pyproject.toml` has a minor version bump if the tool’s output to disk or user-facing behavior changed.

# General Code Review Standards

## Code Quality Essentials

- Functions should be focused and appropriately sized
- Use clear, descriptive naming conventions
- Ensure proper error handling throughout

## Security Standards

- Never hardcode credentials or API keys in code or config
- Do not store secrets in YAML or project config files
- Validate and sanitize data from API responses and user inputs that are written to disk or into protobufs

## Documentation Expectations

- All public functions must include doc comments
- Complex algorithms should have explanatory comments
- README files must be kept up to date

# Version bumping

This project is versioned in pyproject.toml. There is an autotool that increases the patch version every push. However for changes that affect the tools output to disk, this should come with a minor update.

Patch:
- Bug fix
- Small feature that doesn't change any current interaction

Minor:
- Changing output style
- Feature updates

Major:
- Complete rework of core/major output difference

# Resource Classes

## Adding New Resource Types

When adding a new resource type:

1. **Create the resource class** in `src/poly/resources/`:
   - Inherit from `YamlResource` for YAML-based resources or `Resource` for other formats
   - Implement all abstract methods: `command_type`, `build_update_proto`, `build_delete_proto`, `build_create_proto`, `file_path`, `raw`, `validate`, `to_yaml_dict`, `from_yaml_dict`
   - For YAML resources, also implement `make_pretty` and `from_pretty` if you need resource name/ID substitution

2. **Register the resource** in `project.py`:
   - Add to `RESOURCE_NAME_TO_CLASS` dictionary
   - Import the class at the top of the file
   - The key should match the API resource name (e.g., "functions", "topics", "entities")

3. **Update resource mappings**:
   - Each resource class implements `get_resource_prefix()` (with appropriate kwargs such as `file_path`). Ensure it returns the correct prefix for that resource type (e.g. "fn" for functions).
   - This is used in resource name/ID substitution in YAML files.

4. **Add function to read resource in handlers**:
   - Add a static method `_read_<resource_type>_from_projection(projection: dict)` in `SyncClientHandler` (`src/poly/handlers/platform_api.py`).
   - Add a call to this method in `_load_resources()` in `SyncClientHandler`.
   - The method should:
     - Extract resource data from the projection dictionary using nested `.get()` calls
     - Create Resource instances from the extracted data
     - Return a `dict[str, Resource]` mapping resource IDs to Resource instances
     - For agent settings (multiple resource types), return `dict[type, dict[str, Resource]]`
   - Handle missing or None values gracefully using `.get()` with defaults; skip archived resources if applicable (check for `archived` field).
   - Example patterns: simple resources (e.g. `_read_entities_from_projection`), complex resources (e.g. `_read_functions_from_projection`), agent settings (e.g. `_read_agent_settings_from_projection`).

## Resource Validation

- Use `ValueError` for validation errors - they are caught and formatted with file paths automatically
- Validation should check:
  - Required fields are present
  - Field types and formats are correct
  - References to other resources are valid (use `resource_mappings` parameter)
- Validation errors should include clear, actionable messages

## Resource File Paths

- File paths are relative to the project root
- Use `get_path(base_path)` to get the full path
- File paths should be deterministic based on resource name/ID
- For flows, steps are stored in `flows/{flow_name}/steps/` directory

# Error Handling

- **Validation errors**: Use `ValueError` with descriptive messages. These are automatically caught and formatted with file paths.
- **API errors**: Use custom exceptions like `PlatformAPIError` for API-related failures
- **File I/O errors**: Let exceptions propagate naturally, but wrap in context if needed
- Always include context in error messages (file path, resource name, resource ID)

# Logging

- Use `logging` for all logging (imported as `import logging`)
- Then set `logger` with `logger = logging.getLogger(__name__)`
- Use appropriate log levels:
  - `logger.info()` for normal operations and important state changes
  - `logger.warning()` for recoverable issues or unexpected but handled situations
  - `logger.error()` for errors that are caught and handled
  - `logger.debug()` for detailed debugging information
- Include relevant context in log messages (resource IDs, file paths, etc.)

# Code Style

- **Formatting**: Use `ruff` for formatting
- **Line length**: 100 characters
- **Type hints**: Use type hints for all function parameters and return types
- **Docstrings**: Include docstrings for all classes and public methods
- **Imports**: Use absolute imports from `poly` package
- **Naming**: Follow PEP 8 conventions

# Testing

- Write tests in `src/poly/tests/`
- Use `unittest.TestCase` for test classes
- Test files should mirror the source structure (e.g., `resources_test.py` for resource classes)
- Use test projects in `tests/test_projects/` for integration-style tests
- Ensure all tests pass: `pytest`

# Protobuf Handling

- Protobuf files are in `src/poly/handlers/protobuf/`
- These are generated files - **do not edit them directly, only copy from poly-core**
- Use protobuf message types from the generated files
- When working with protobuf:
  - Use `build_create_proto()`, `build_update_proto()`, `build_delete_proto()` methods
  - Convert to/from protobuf in resource classes, not in API handlers
  - Handle protobuf serialization/deserialization carefully

# Resource Mappings

- `ResourceMapping` objects track relationships between resources
- Used for:
  - Validating references between resources
  - Converting resource IDs to names in YAML (pretty printing)
  - Converting resource names to IDs when reading from disk
- When validating references, use the `resource_mappings` parameter passed to `validate()`

# File Operations

- Use `Resource.read_from_file()` and `Resource.save_to_file()` for file I/O
- These handle encoding and error cases consistently
- For YAML files, use `resource_utils.load_yaml()` and `resource_utils.dump_yaml()`
- Always handle file path construction using `os.path.join()` or `Resource.get_path()`

# API Handlers

- API handlers are in `src/poly/handlers/`
- `AgentStudioInterface` is the main interface - use as wrapper for operations. This will call the lower level API handlers
- `SyncClientHandler` wraps the platform API for lower-level operations
- Always handle API errors gracefully and provide meaningful error messages
Set the `POLY_ADK_KEY` environment variable before running CLI commands

# Constants and Configuration

- Project-level constants are in `constants.py`
- Use constants for:
  - Permissions list
  - File names (e.g., `PROJECT_CONFIG_FILE`, `STATUS_FILE`)
  - Resource decorators (e.g., `DECORATORS`)
- Don't hardcode values that might change

# YAML Handling

- Use `ruamel.yaml` via `resource_utils` for YAML operations
- Preserve YAML formatting when possible (comments, ordering)
- Handle YAML parsing errors with clear error messages
- When reading YAML, handle empty files gracefully (return empty dict)