# OCI Documentation MCP Server

Model Context Protocol (MCP) server for Oracle Cloud Infrastructure documentation.

This server helps MCP clients search OCI documentation, read OCI documentation pages as markdown, extract selected sections from a documentation page, and answer questions from cited OCI documentation sources.

## Tools

- `search_documentation`: Search OCI documentation through Oracle's documentation search backend.
- `read_documentation`: Fetch an OCI documentation page and convert it to markdown.
- `read_sections`: Fetch specific heading sections from an OCI documentation page.
- `answer_question`: Search OCI documentation, read the most relevant pages, and return an extractive answer with citations.

## Prompt Templates

- `ask_oci_docs`: Answer an OCI documentation question with citations.
- `how_to_oci`: Answer a task-oriented OCI how-to question from task pages, CLI sections, and API references.
- `compare_oci_services`: Compare OCI services or options using cited OCI documentation.

## Installation

Install from Git when you want both the MCP server and the repo-scoped Codex skills:

```bash
git clone <git-url> oci-documentation-mcp-server
cd oci-documentation-mcp-server
uv sync
```

Then configure your MCP client to run the server from the checkout:

```json
{
  "mcpServers": {
    "oci-documentation-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/oci-documentation-mcp-server",
        "run",
        "oci-documentation-mcp-server"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

The Codex skill for `/oci-docs` is included in the Git checkout at `.agents/skills/oci-docs/SKILL.md`. Open Codex from the cloned repository, or start a new Codex session in that directory, so repo-scoped skills are discovered. Restart Codex if `/oci-docs` does not appear immediately.

For a global Codex skill install, copy the skill directory from the checkout:

```bash
mkdir -p ~/.codex/skills
cp -R .agents/skills/oci-docs ~/.codex/skills/oci-docs
```

Run the server directly from the local checkout:

```json
{
  "mcpServers": {
    "oci-documentation-mcp-server": {
      "command": "uv",
      "args": ["run", "oci-documentation-mcp-server"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

For Docker:

```bash
docker build -t mcp/oci-documentation .
```

```json
{
  "mcpServers": {
    "oci-documentation-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "mcp/oci-documentation:latest"
      ]
    }
  }
}
```

## Configuration

| Variable | Description | Default |
| --- | --- | --- |
| `FASTMCP_LOG_LEVEL` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. | `WARNING` |
| `OCI_DOCUMENTATION_SEARCH_URL` | Override for the Oracle documentation search backend. | `https://docs.oracle.com/apps/ohcsearchclient/api/v2/search/pages` |
| `MCP_USER_AGENT` | Optional custom User-Agent for documentation fetches. | Chrome-based default |

## Calling Options

Use an MCP client for normal tool and prompt-template calls:

```text
answer_question(question="How do I launch a compute instance?", max_sources=3)
```

```text
ask_oci_docs(question="How do I launch a compute instance?")
```

Use the local CLI wrapper for terminal workflows:

```bash
uv run oci-docs answer "How do I launch a compute instance?"
uv run oci-docs search "compute instance launch" --limit 5
uv run oci-docs read "https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm"
```

For automation, add `--json` to `answer` or `search`:

```bash
uv run oci-docs answer "How do I launch a compute instance?" --json
```

In Codex, use the repo-scoped `/oci-docs` command for the same command surface:

```text
/oci-docs answer How do I launch a compute instance?
/oci-docs search compute instance launch --limit 5
/oci-docs read https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm
```

## Example Prompts

- "Search OCI documentation for compute instance launch."
- "Answer this from OCI documentation with citations: How do I launch a compute instance?"
- "Read https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm."
- "Read the Networking and Security sections from this OCI documentation URL."

## Development

Install dependencies and run the focused OCI test suite:

```bash
uv sync
uv run pytest tests/test_oci_search.py tests/test_server_oci.py tests/test_architecture_center.py tests/test_oracle_blogs.py tests/test_evidence.py tests/test_oci_evidence_models.py -q
uv run ruff check oci_documentation_mcp_server tests
uv run pyright oci_documentation_mcp_server tests
```
