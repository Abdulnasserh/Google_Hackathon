import sys
import os
from mcp.server.fastmcp import FastMCP

# Add the parent directory to Python path so we can import our tools
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from bidi_streaming_agent.tools.windows_tools import (
    ping_host, check_dns, traceroute, get_network_config, get_wifi_profiles, get_wifi_info,
    check_open_ports, release_renew_ip,
    get_system_info, get_disk_usage, get_disk_health,
    get_top_processes, get_memory_usage, get_battery_info,
    check_for_updates, get_event_log_errors, run_system_file_checker, flush_dns_cache,
    list_startup_programs, get_installed_programs
)

# Initialize FastMCP Server for Windows
mcp = FastMCP("WindowsTechnicianMCP")

# Network Tools
mcp.tool()(ping_host)
mcp.tool()(check_dns)
mcp.tool()(traceroute)
mcp.tool()(get_network_config)
mcp.tool()(get_wifi_profiles)
mcp.tool()(get_wifi_info)
mcp.tool()(check_open_ports)
mcp.tool()(release_renew_ip)

# System Information Tools
mcp.tool()(get_system_info)
mcp.tool()(get_disk_usage)
mcp.tool()(get_disk_health)

# Performance Tools
mcp.tool()(get_top_processes)
mcp.tool()(get_memory_usage)
mcp.tool()(get_battery_info)

# Maintenance Tools
mcp.tool()(check_for_updates)
mcp.tool()(get_event_log_errors)
mcp.tool()(run_system_file_checker)
mcp.tool()(flush_dns_cache)
mcp.tool()(list_startup_programs)
mcp.tool()(get_installed_programs)

if __name__ == "__main__":
    # Start the MCP server
    print("Starting WindowsTechnicianMCP server...", file=sys.stderr)
    mcp.run()
