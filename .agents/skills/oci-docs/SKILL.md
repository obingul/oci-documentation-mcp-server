---
name: oci-docs
description: Use when the user invokes /oci-docs or asks to query OCI documentation with the repo's oci-docs CLI.
---

Run the OCI Documentation CLI from the repository root.

## Command Surface

Treat `/oci-docs` as a thin slash-command wrapper around `uv run oci-docs`.

Supported forms:

- `/oci-docs answer <question> [--search-phrase <phrase>] [--max-sources <n>] [--json]`
- `/oci-docs search <search phrase> [--limit <n>] [--json]`
- `/oci-docs read <docs-url> [--max-length <n>] [--start-index <n>]`

If the first argument is omitted, default to `answer` and treat all remaining text as the question.

## Workflow

1. Parse the user input after `/oci-docs`.
2. Build the matching CLI command without changing option names or meanings.
3. Run it from the cloned `oci-documentation-mcp-server` repository root.
4. Return the CLI result concisely. If the command fails, include the failing subcommand and the error text.

## CLI Mapping

- `answer` maps to `uv run oci-docs answer`.
- `search` maps to `uv run oci-docs search`.
- `read` maps to `uv run oci-docs read`.

Preserve CLI flags exactly:

- `answer`: `--search-phrase`, `--max-sources`, `--json`
- `search`: `--limit`, `--json`
- `read`: `--max-length`, `--start-index`
