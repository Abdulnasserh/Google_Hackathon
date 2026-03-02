import sys
import os
from mcp.server.fastmcp import FastMCP

# Add the parent directory to Python path so we can import our tools
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from bidi_streaming_agent.tools.mac_tools import (
    ping_host, check_dns, traceroute, get_network_info, get_wifi_info, check_open_ports,
    get_system_info, get_disk_usage, get_disk_info,
    get_top_processes, get_memory_usage, get_battery_info, get_thermal_info,
    check_for_updates, get_system_logs, flush_dns_cache, list_startup_items
)

# Initialize FastMCP Server for macOS
mcp = FastMCP("MacTechnicianMCP")

# Network Tools
mcp.tool()(ping_host)
mcp.tool()(check_dns)
mcp.tool()(traceroute)
mcp.tool()(get_network_info)
mcp.tool()(get_wifi_info)
mcp.tool()(check_open_ports)

# System Information Tools
mcp.tool()(get_system_info)
mcp.tool()(get_disk_usage)
mcp.tool()(get_disk_info)

# Performance Tools
mcp.tool()(get_top_processes)
mcp.tool()(get_memory_usage)
mcp.tool()(get_battery_info)
mcp.tool()(get_thermal_info)

# Maintenance Tools
mcp.tool()(check_for_updates)
mcp.tool()(get_system_logs)
mcp.tool()(flush_dns_cache)
mcp.tool()(list_startup_items)

if __name__ == "__main__":
    # Start the MCP server using standard input/output (the default for MCP)
    print("Starting MacTechnicianMCP server...", file=sys.stderr)
    mcp.run()
