# Reviewing ADK pull requests

Checklist for any reviewer, human or AI. It repeats the rules from `AGENTS.md` that matter in
review, because some review tools read only this file.

Report **blocking** issues first, then **nits**. Don't comment on what the ignore list covers.

## Blocking

1. **Layering.** Command classes in `src/poly/cli_commands/` only parse, call `AgentStudioProject`
   and print. Flag API calls, file I/O, validation or merge logic in the CLI layer, and any new
   direct call to `AgentStudioInterface` from a command. The fix is a project method, even a thin
   wrapper.
2. **PR title type.** The title becomes the release. `feat:` for anything a user can see,
   including output or on-disk changes. `fix:`/`perf:` for patches. `chore:`/`docs:`/`ci:`/`build:`/
   `refactor:`/`style:`/`test:` don't release, so a user-visible change under one of them never
   ships a release.
3. **Version or changelog edits.** Versions in `pyproject.toml` and `skills/*/SKILL.md`, and
   `CHANGELOG.md`, are written by semantic-release. A hand edit is wrong. Don't ask for a bump
   either.
4. **Docs and skills.** A user-facing change must update `docs/docs/` (the command page and any
   guide), `src/poly/docs/` when a resource's YAML shape changes, and `skills/` when a command,
   flag or workflow a skill mentions changes.
5. **Generated files.** No hand edits under `src/poly/handlers/protobuf/` or `src/poly/types/`.
   Look for stray files too (scratch scripts, `BUILD.bazel`, deleted `__init__.py`).
6. **Internal references.** The repo and its PRs are public. Flag real client or project names,
   project or account IDs, internal repos, services or tooling, in code, docs, tests or the PR text.
7. **Ticket IDs in the PR title or description.** Ask for them to move to a PR comment.
8. **Unsafe side effects.** Deletes must touch only files the ADK owns. Anything that reaches
   `live` must say so. `--json` must not prompt.
9. **Validation and round-trip.** Anything the platform would reject should fail locally first.
   Resource changes must survive pull → push with no diff, and the `test_project` fixture should
   cover new fields or resource types.
10. **Resource registration.** A new resource type needs `@register_resource`, a `from_projection`
    classmethod, an import in `resources/__init__.py`, and tests in `resources_test.py`.
11. **Dependencies.** New dependencies need `licenses.json` regenerated. Heavy ones belong in an
    optional extra.
12. **PR template.** The description uses `.github/PULL_REQUEST_TEMPLATE.md` and its sections only.

## Worth raising

- Reimplementing an existing helper (`make_request`, `load_yaml`/`dump_yaml`, `discover_resources`,
  `load_project`, `json_print`) instead of reusing or extending it.
- Back-compat shims or code nothing calls. Delete it.
- Flags or terms that differ from sibling commands (`--json`, `--path`, `--force`, region names).
- Tests in a new file or class when an existing one fits, or mocks deeper than the API boundary.
- No manual QA notes for a new or changed command.

## Nits

- Verbose or narrating comments, especially ones an AI tool left behind.
- Naming, help text that a user could misread.

## Ignore

`CHANGELOG.md`, `chore(release):` commits, version stamps, `uv.lock`, `licenses.json` contents,
and everything under `src/poly/handlers/protobuf/` and `src/poly/types/`.
