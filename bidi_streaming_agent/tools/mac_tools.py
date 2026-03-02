"""
macOS CLI Diagnostic Tools
============================
Safe, whitelisted CLI tools for diagnosing macOS issues.
Each function runs a specific system command and returns the output.

Security:
    - Only pre-approved commands are executed (no arbitrary shell input)
    - All commands run with a timeout to prevent hangs
    - Subprocess calls use shell=False where possible for safety

Usage:
    These functions are passed as `tools` to the macOS troubleshooter Agent.
    The LLM reads the docstrings to decide when to call each tool.
"""

import subprocess
import shlex
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate_output(text: str, max_length: int = 3000) -> str:
    """Smartly truncate long command outputs to prevent crashing the LLM context.
    Keeps the beginning and the end (where errors usually are) if it's too long."""
    if len(text) <= max_length:
        return text
    
    half = max_length // 2
    return text[:half] + f"\n\n...[TRUNCATED {len(text) - max_length} characters]...\n\n" + text[-half:]

def _run(cmd: list[str], timeout: int = 30) -> str:
    """Run a command safely and return its stdout, or an error message."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr.strip():
            output += f"\n[stderr]: {result.stderr.strip()}"
        
        final_out = _truncate_output(output if output else "(no output)")
        return final_out
    except subprocess.TimeoutExpired:
        return f"⏱️ Command timed out after {timeout}s: {' '.join(cmd)}"
    except FileNotFoundError:
        return f"❌ Command not found: {cmd[0]}"
    except Exception as e:
        return f"❌ Error running command: {e}"


# ---------------------------------------------------------------------------
# Network Diagnostic Tools
# ---------------------------------------------------------------------------

def ping_host(host: str, count: int = 4) -> dict:
    """
    Ping a host to check network connectivity.
    Use this to diagnose whether the user's machine can reach a server.
    Common hosts: 'google.com', '8.8.8.8', '1.1.1.1', or any user-specified host.

    Args:
        host: The hostname or IP address to ping (e.g. 'google.com', '8.8.8.8').
        count: Number of ping packets to send (default 4, max 10).

    Returns:
        dict with 'status' and 'output' keys.
    """
    count = min(max(count, 1), 10)
    # Sanitize host — no shell metacharacters allowed
    safe_host = shlex.quote(host).strip("'")
    output = _run(["ping", "-c", str(count), safe_host], timeout=30)
    return {"status": "success", "output": output}


def check_dns(domain: str) -> dict:
    """
    Look up DNS records for a domain to diagnose DNS resolution issues.
    Use this when a user says websites aren't loading but their internet seems connected.

    Args:
        domain: The domain name to look up (e.g. 'google.com').

    Returns:
        dict with 'status' and 'output' keys.
    """
    safe_domain = shlex.quote(domain).strip("'")
    output = _run(["nslookup", safe_domain], timeout=15)
    return {"status": "success", "output": output}


def traceroute(host: str) -> dict:
    """
    Trace the network route to a host. Shows each hop between the user and
    the destination. Use this to identify WHERE network slowness or drops occur.

    Args:
        host: The hostname or IP address to trace (e.g. 'google.com').

    Returns:
        dict with 'status' and 'output' keys.
    """
    safe_host = shlex.quote(host).strip("'")
    output = _run(["traceroute", "-m", "15", safe_host], timeout=60)
    return {"status": "success", "output": output}


def get_network_info() -> dict:
    """
    Get the current network interface configuration (IP addresses, subnet masks,
    MAC addresses). Use this to check if the user has a valid IP address and is
    properly connected to a network.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run(["ifconfig"], timeout=10)
    return {"status": "success", "output": output}


def get_wifi_info() -> dict:
    """
    Get detailed Wi-Fi connection info: SSID, signal strength (RSSI), channel,
    security type, transmit rate, and noise level. Use this to diagnose Wi-Fi
    connectivity or performance problems.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run([
        "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport",
        "-I"
    ], timeout=10)
    return {"status": "success", "output": output}


def check_open_ports(host: str = "localhost", ports: str = "80,443,22,3389,8080") -> dict:
    """
    Check if specific network ports are open/listening on a host.
    Use this to troubleshoot service connectivity issues (e.g. web server not responding).

    Args:
        host: The host to scan (default 'localhost').
        ports: Comma-separated port numbers to check (e.g. '80,443,22').

    Returns:
        dict with 'status' and 'output' keys.
    """
    safe_host = shlex.quote(host).strip("'")
    results = []
    for port in ports.split(",")[:10]:  # Max 10 ports
        port = port.strip()
        if not port.isdigit():
            continue
        out = _run(["nc", "-z", "-w", "3", safe_host, port], timeout=5)
        status_str = "OPEN" if "succeeded" in out.lower() or out == "(no output)" else "CLOSED/FILTERED"
        results.append(f"  Port {port}: {status_str}")
    output = f"Port scan results for {host}:\n" + "\n".join(results)
    return {"status": "success", "output": output}


# ---------------------------------------------------------------------------
# System Information Tools
# ---------------------------------------------------------------------------

def get_system_info() -> dict:
    """
    Get a comprehensive overview of the Mac's hardware and software:
    model, processor, memory, macOS version, serial number, etc.
    Use this as a first step when diagnosing any system issue.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run(["system_profiler", "SPHardwareDataType", "SPSoftwareDataType"], timeout=15)
    return {"status": "success", "output": output}


def get_disk_usage() -> dict:
    """
    Get disk usage for all mounted volumes — shows total space, used space,
    and available space. Use this when the user complains about storage or
    when apps won't install due to low disk space.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run(["df", "-h"], timeout=10)
    return {"status": "success", "output": output}


def get_disk_info() -> dict:
    """
    Get detailed disk/partition info using diskutil — shows APFS containers,
    volumes, file systems, and disk health. Use this for deeper disk diagnostics
    beyond just space usage.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run(["diskutil", "list"], timeout=10)
    return {"status": "success", "output": output}


# ---------------------------------------------------------------------------
# Performance & Process Tools
# ---------------------------------------------------------------------------

def get_top_processes(count: int = 10) -> dict:
    """
    Get the top CPU-consuming processes currently running on the Mac.
    Use this when the user complains about the computer being slow,
    fans running loudly, or high CPU usage.

    Args:
        count: Number of top processes to show (default 10, max 25).

    Returns:
        dict with 'status' and 'output' keys.
    """
    count = min(max(count, 1), 25)
    output = _run(["ps", "aux", "-r"], timeout=10)
    # Return header + top N lines
    lines = output.split("\n")
    truncated = "\n".join(lines[:count + 1])
    return {"status": "success", "output": truncated}


def get_memory_usage() -> dict:
    """
    Get detailed memory (RAM) usage statistics — pages free, active,
    inactive, wired, compressed, and swap usage. Use this when diagnosing
    slow performance or apps crashing due to low memory.

    Returns:
        dict with 'status' and 'output' keys.
    """
    vm_output = _run(["vm_stat"], timeout=10)
    # Also get swap info
    sysctl_output = _run(["sysctl", "vm.swapusage"], timeout=5)
    return {"status": "success", "output": f"{vm_output}\n\nSwap usage:\n{sysctl_output}"}


def get_battery_info() -> dict:
    """
    Get battery health, charge level, and power adapter status.
    Use this when diagnosing battery drain, charging issues, or
    power-related problems on MacBooks.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run(["pmset", "-g", "batt"], timeout=10)
    return {"status": "success", "output": output}


def get_thermal_info() -> dict:
    """
    Get the current thermal/power management conditions, including whether
    thermal throttling is active. Use this when users report overheating
    or unexpected performance drops.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run(["pmset", "-g", "therm"], timeout=10)
    return {"status": "success", "output": output}


# ---------------------------------------------------------------------------
# System Maintenance Tools
# ---------------------------------------------------------------------------

def check_for_updates() -> dict:
    """
    Check for available macOS software updates. Use this when the user
    asks about updates or when diagnosing issues that may be caused by
    running an outdated OS version.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run(["softwareupdate", "--list"], timeout=60)
    return {"status": "success", "output": output}


def get_system_logs(keyword: Optional[str] = None, minutes: int = 5) -> dict:
    """
    Retrieve recent system log entries. Optionally filter by keyword.
    Use this to investigate crashes, errors, or system events that
    happened recently.

    Args:
        keyword: Optional keyword to filter logs (e.g. 'error', 'kernel', 'crash').
        minutes: How many minutes back to search (default 5, max 30).

    Returns:
        dict with 'status' and 'output' keys.
    """
    minutes = min(max(minutes, 1), 30)
    cmd = ["log", "show", "--last", f"{minutes}m", "--style", "compact"]
    if keyword:
        safe_keyword = shlex.quote(keyword).strip("'")
        cmd.extend(["--predicate", f'eventMessage contains "{safe_keyword}"'])
    output = _run(cmd, timeout=30)
    # Truncate to avoid overwhelming output
    lines = output.split("\n")
    if len(lines) > 50:
        output = "\n".join(lines[:50]) + f"\n\n... ({len(lines) - 50} more lines truncated)"
    return {"status": "success", "output": output}


def flush_dns_cache() -> dict:
    """
    Flush the local DNS cache. Use this when users have DNS resolution
    problems — websites not loading, getting wrong IP addresses, or
    after changing DNS servers.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run(["sudo", "dscacheutil", "-flushcache"], timeout=10)
    killall_output = _run(["sudo", "killall", "-HUP", "mDNSResponder"], timeout=10)
    return {"status": "success", "output": f"DNS cache flush:\n{output}\nmDNSResponder restart:\n{killall_output}"}


def list_startup_items() -> dict:
    """
    List applications and services that launch at startup/login.
    Use this when diagnosing slow boot times or unwanted programs
    starting automatically.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run(["launchctl", "list"], timeout=10)
    lines = output.split("\n")
    if len(lines) > 40:
        output = "\n".join(lines[:40]) + f"\n\n... ({len(lines) - 40} more items)"
    return {"status": "success", "output": output}


# ---------------------------------------------------------------------------
# All tools list (for easy import into the agent)
# ---------------------------------------------------------------------------

ALL_MAC_TOOLS = [
    # Network
    ping_host,
    check_dns,
    traceroute,
    get_network_info,
    get_wifi_info,
    check_open_ports,
    # System
    get_system_info,
    get_disk_usage,
    get_disk_info,
    # Performance
    get_top_processes,
    get_memory_usage,
    get_battery_info,
    get_thermal_info,
    # Maintenance
    check_for_updates,
    get_system_logs,
    flush_dns_cache,
    list_startup_items,
]
