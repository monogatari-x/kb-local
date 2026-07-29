"""kb-local MCP Server entry point."""

import os
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

sys.stderr.write("[kb-local] starting MCP server\n")
sys.stderr.flush()

from kb_mcp.server import main

if __name__ == "__main__":
    main()
