# CLI command layer

Rules for `src/poly/cli_commands/`. The repo-wide rules in the root `AGENTS.md` still apply.

- A command class subclasses `BaseCommand` (`base.py`), defines `add_arguments` and `run`, and is
  listed in `COMMANDS` in `src/poly/cli.py`. Subcommands dispatch from `run` to one classmethod
  per action.
- This layer only parses arguments, calls `AgentStudioProject` methods and prints. Get the project
  with `load_project(args.path, output_json=args.json)` (`shared.py`). If a command needs data the
  project doesn't expose, add a project method, even if it only forwards to the interface.
- Reuse the shared parent parsers in `Parents` (`base.py`) for `--path`, `--json`, `--verbose`
  and `--debug`. Don't redefine them per command.
- `--json`: print one object with `json_print` (`output/json_output.py`), never prompt, and
  exit 1 on failure. Human output goes through `output/console.py` helpers (`success`, `error`,
  `info`, `paged_output` for long lists).
- Failures exit non-zero in both modes. Unexpected exceptions reach `handle_exception` in
  `cli.py`; don't catch and swallow them here.
- Import heavy modules (console rendering, call/WebRTC, YAML dumpers) inside the method that
  needs them, so `poly --help` and completion stay fast.
- A new command or flag also needs a page in `docs/docs/reference/cli/` and, if a user skill
  covers the area, an update in `skills/`.
