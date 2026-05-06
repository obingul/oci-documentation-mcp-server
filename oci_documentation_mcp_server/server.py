"""Entrypoint for the OCI Documentation MCP server."""

import os
import sys
from loguru import logger


logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))


def main():
    """Run the OCI Documentation MCP server."""
    from oci_documentation_mcp_server.server_oci import main as server_main

    server_main()
