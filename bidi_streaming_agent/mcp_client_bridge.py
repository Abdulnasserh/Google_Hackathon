"""
MCP Client Bridge — Connects ADK Agent to FastMCP Servers
==========================================================
This module acts as a bridge between Google ADK Agents and MCP servers.
It spawns the MCP server as a subprocess, fetches tool definitions
over the stdio protocol, and wraps them into callable Python functions
that the ADK Agent can use.

Architecture:
    ADK Agent → MCP Client Bridge → (subprocess) → FastMCP Server
                    ↕ stdio
"""

import asyncio
import inspect
import os
import sys
import threading
from typing import Callable, List, Optional

from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession


def _run_async(coro):
    """
    Run an async coroutine safely, whether or not an event loop
    is already running (e.g. inside uvicorn).
    Falls back to running in a separate thread if needed.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're inside an existing event loop (e.g. uvicorn) — 
        # run in a new thread with its own event loop
        result = [None]
        exception = [None]

        def run_in_thread():
            try:
                result[0] = asyncio.run(coro)
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join(timeout=30)

        if exception[0]:
            raise exception[0]
        return result[0]
    else:
        return asyncio.run(coro)


def create_mcp_bridge_tools(server_script: str) -> List[Callable]:
    """
    Connects to the specified FastMCP server over stdio,
    retrieves all its registered tools, and automatically wraps them
    into local Python async functions with accurate schemas
    so the ADK Agent can use them seamlessly.

    Args:
        server_script: Relative path to the MCP server script
                       (e.g. 'bidi_streaming_agent/mcp_servers/mac_mcp_server.py')
    
    Returns:
        List of async callables that the ADK Agent can use as tools.
    """
    # Resolve the script path relative to the project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    abs_script_path = os.path.join(project_root, server_script)

    # Use sys.executable to ensure the subprocess uses the same virtualenv Python
    python_cmd = sys.executable

    # Helper to securely run an MCP command
    async def run_mcp_tool(tool_name: str, args: dict) -> str:
        server_params = StdioServerParameters(
            command=python_cmd,
            args=[abs_script_path]
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=args)
                # Parse the MCP tool result (typically a Content object with text)
                if result.content and len(result.content) > 0:
                    return result.content[0].text
                return "Tool executed successfully but returned no output."

    # Fetch the list of tools synchronously at import time to build definitions
    async def fetch_tools():
        server_params = StdioServerParameters(
            command=python_cmd,
            args=[abs_script_path]
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.list_tools()

    try:
        print(f"[MCP Bridge] Fetching tools from {server_script}...")
        mcp_tools = _run_async(fetch_tools())
    except Exception as e:
        print(f"[MCP Bridge] Failed to fetch tools from {server_script}: {e}")
        return []

    dynamic_tools = []
    
    for tool_info in mcp_tools.tools:
        name = tool_info.name
        doc = tool_info.description or f"MCP Tool: {name}"
        
        # Determine arguments from JSON schema
        schema = tool_info.inputSchema or {}
        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])
        
        # Build an async wrapper function with dynamic arguments
        # Capture the name in the closure correctly using default arg
        async def wrapper(_name=name, **kwargs) -> str:
            return await run_mcp_tool(_name, kwargs)

        # Set metadata for ADK reflection
        wrapper.__name__ = name
        wrapper.__doc__ = doc
        
        # We manually build the signature for ADK's introspection
        params = []
        for prop_name, prop_details in properties.items():
            # Map JSON schema types to Python types
            prop_type = str
            json_type = prop_details.get("type")
            if json_type == "integer":
                prop_type = int
            elif json_type == "boolean":
                prop_type = bool

            # Handle Optional types (anyOf with null)
            any_of = prop_details.get("anyOf", [])
            if any_of:
                for variant in any_of:
                    if variant.get("type") == "string":
                        prop_type = str
                        break
                    elif variant.get("type") == "integer":
                        prop_type = int
                        break

            # Determine default value
            is_required = prop_name in required_fields
            default = inspect.Parameter.empty if is_required else prop_details.get("default", inspect.Parameter.empty)
            
            params.append(
                inspect.Parameter(
                    name=prop_name,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=default,
                    annotation=prop_type
                )
            )

        wrapper.__signature__ = inspect.Signature(parameters=params)
        dynamic_tools.append(wrapper)

    print(f"[MCP Bridge] Successfully loaded {len(dynamic_tools)} tools")
    return dynamic_tools
