"""kb-local MCP Server entry point."""

import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from kb_mcp.server import main

if __name__ == "__main__":
    main()
