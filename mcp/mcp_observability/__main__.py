"""Entry point for running the observability MCP server."""

import asyncio
import os
import sys

from mcp_observability.server import main


async def run() -> None:
    # Accept URLs from command line or environment
    victorialogs_url = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("VICTORIALOGS_URL")
    victoriatraces_url = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("VICTORIATRACES_URL")
    await main(victorialogs_url=victorialogs_url, victoriatraces_url=victoriatraces_url)


if __name__ == "__main__":
    asyncio.run(run())
