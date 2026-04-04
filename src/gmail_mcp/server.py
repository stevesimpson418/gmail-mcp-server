"""Gmail MCP Server — entry point."""

from dotenv import load_dotenv
from fastmcp import FastMCP

from gmail_mcp.tools import register_gmail_tools

load_dotenv()

mcp = FastMCP("gmail-mcp-server")
register_gmail_tools(mcp)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
