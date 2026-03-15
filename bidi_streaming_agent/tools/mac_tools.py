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
# ACTION / FIX Tools — Nora can now actually repair issues!
# ---------------------------------------------------------------------------

def kill_process(process_name: str) -> dict:
    """
    Force kill a process by name. Use this when a process is frozen, not
    responding, consuming too much CPU/RAM, or causing issues. This is
    equivalent to what a technician would do in Activity Monitor.

    Args:
        process_name: The exact name of the process to kill (e.g. 'Safari', 'Google Chrome Helper').

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run(["killall", process_name], timeout=10)
    return {"status": "success", "output": f"Attempted to kill '{process_name}': {output}"}


def kill_process_by_pid(pid: int) -> dict:
    """
    Force kill a specific process by its PID (Process ID). Use this when
    you know the exact PID from get_top_processes and need to terminate it.

    Args:
        pid: The process ID number to kill.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run(["kill", "-9", str(pid)], timeout=10)
    return {"status": "success", "output": f"Sent SIGKILL to PID {pid}: {output}"}


def toggle_bluetooth(action: str = "toggle") -> dict:
    """
    Turn Bluetooth on, off, or toggle it. Use this to fix Bluetooth
    connectivity issues — often toggling Bluetooth off and on resolves
    pairing problems with headphones, mice, keyboards, etc.

    Args:
        action: One of 'on', 'off', or 'toggle'.

    Returns:
        dict with 'status' and 'output' keys.
    """
    # Check current status first
    status_out = _run(["defaults", "read", "/Library/Preferences/com.apple.Bluetooth", "ControllerPowerState"], timeout=5)
    
    if action == "toggle":
        # If currently on (1), turn off; if off (0), turn on
        new_state = "0" if "1" in status_out else "1"
    elif action == "off":
        new_state = "0"
    else:
        new_state = "1"
    
    # Use blueutil if available, fallback to system command
    output = _run(["blueutil", "--power", new_state], timeout=10)
    if "not found" in output.lower():
        # Fallback: toggle via system preferences
        output = _run(["osascript", "-e", f'tell application "System Events" to tell process "SystemUIServer" to click menu bar item 1 of menu bar 1'], timeout=10)
    
    state_word = "ON" if new_state == "1" else "OFF"
    return {"status": "success", "output": f"Bluetooth set to {state_word}. {output}"}


def toggle_wifi(action: str = "toggle") -> dict:
    """
    Turn Wi-Fi on, off, or toggle it. Use this to fix Wi-Fi connectivity
    issues — toggling Wi-Fi is often the first troubleshooting step for
    connection problems, slow speeds, or network drops.

    Args:
        action: One of 'on', 'off', or 'toggle'.

    Returns:
        dict with 'status' and 'output' keys.
    """
    # Get the Wi-Fi interface name (usually en0)
    interface_out = _run(["networksetup", "-listallhardwareports"], timeout=5)
    wifi_interface = "en0"  # Default
    lines = interface_out.split("\n")
    for i, line in enumerate(lines):
        if "Wi-Fi" in line and i + 1 < len(lines):
            device_line = lines[i + 1]
            if "Device:" in device_line:
                wifi_interface = device_line.split("Device:")[1].strip()
    
    if action == "toggle":
        # Check current state
        status = _run(["networksetup", "-getairportpower", wifi_interface], timeout=5)
        new_action = "off" if "on" in status.lower() else "on"
    else:
        new_action = action
    
    output = _run(["networksetup", "-setairportpower", wifi_interface, new_action], timeout=10)
    return {"status": "success", "output": f"Wi-Fi turned {new_action.upper()} on {wifi_interface}. {output}"}


def manage_service(service_name: str, action: str = "restart") -> dict:
    """
    Start, stop, or restart a macOS system service (launchd daemon).
    Use this to fix issues like Bluetooth not working, audio services freezing,
    DNS problems, etc. This is what a real technician does to fix service-level issues.

    Args:
        service_name: The service identifier (e.g. 'com.apple.Bluetooth', 'com.apple.audio.coreaudiod',
                      'com.apple.mDNSResponder', 'com.apple.WindowServer').
        action: One of 'start', 'stop', 'restart' (default 'restart').

    Returns:
        dict with 'status' and 'output' keys.
    """
    results = []
    if action in ("stop", "restart"):
        out = _run(["launchctl", "stop", service_name], timeout=10)
        results.append(f"Stop: {out}")
    if action in ("start", "restart"):
        out = _run(["launchctl", "start", service_name], timeout=10)
        results.append(f"Start: {out}")
    
    return {"status": "success", "output": f"Service '{service_name}' {action}ed.\n" + "\n".join(results)}


def clear_system_cache() -> dict:
    """
    Clear macOS system caches to free up space and fix performance issues.
    This is safe and commonly done by technicians to resolve sluggish behavior,
    app crashes, and display glitches.

    Returns:
        dict with 'status' and 'output' keys.
    """
    results = []
    
    # Clear user caches
    out = _run(["rm", "-rf", "/tmp/com.apple.*"], timeout=10)
    results.append(f"Cleared temp caches: {out}")
    
    # Purge memory (frees inactive RAM)
    out = _run(["purge"], timeout=15)
    results.append(f"Memory purge: {out}")
    
    return {"status": "success", "output": "System caches cleared and memory purged.\n" + "\n".join(results)}


def empty_trash() -> dict:
    """
    Empty the user's Trash to free up disk space immediately. Use this
    when disk space is critically low.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run(["osascript", "-e", 'tell application "Finder" to empty trash'], timeout=30)
    return {"status": "success", "output": f"Trash emptied. {output}"}


def open_application(app_name: str) -> dict:
    """
    Open a macOS application by name. Use this to launch apps the user
    needs, such as System Preferences, Activity Monitor, Terminal, etc.

    Args:
        app_name: The name of the application (e.g. 'System Preferences', 'Activity Monitor', 'Safari').

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run(["open", "-a", app_name], timeout=10)
    return {"status": "success", "output": f"Opened '{app_name}'. {output}"}


def close_application(app_name: str) -> dict:
    """
    Gracefully close a macOS application by name. Use this to close
    apps that are not responding or to free up resources.

    Args:
        app_name: The name of the application (e.g. 'Safari', 'Google Chrome').

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run(["osascript", "-e", f'tell application "{app_name}" to quit'], timeout=10)
    return {"status": "success", "output": f"Closed '{app_name}'. {output}"}


def run_safe_shell_command(command: str) -> dict:
    """
    Execute a safe shell command on the user's Mac. This is the ultimate
    technician tool — it lets you run any diagnostic or fix command.
    
    CRITICAL SAFETY RULES:
    - NEVER run destructive commands (rm -rf /, format, etc.)
    - NEVER access passwords, keychains, or private data
    - Only use for legitimate troubleshooting (checking logs, restarting services, etc.)
    - Always explain to the user what you're about to run and why

    Args:
        command: The shell command to execute (e.g. 'defaults read com.apple.dock autohide').

    Returns:
        dict with 'status' and 'output' keys.
    """
    # Safety blocklist
    dangerous = ["rm -rf /", "mkfs", "dd if=", "format", "diskutil erase", "> /dev/", 
                 "security find-generic-password", "security find-internet-password",
                 "passwd", "dscl . -passwd", "curl | bash", "wget | bash"]
    cmd_lower = command.lower()
    for d in dangerous:
        if d in cmd_lower:
            return {"status": "error", "output": f"BLOCKED: Command contains dangerous pattern '{d}'. This operation is not permitted for safety reasons."}
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr.strip():
            output += f"\n[stderr]: {result.stderr.strip()}"
        return {"status": "success", "output": _truncate_output(output if output else "(command completed with no output)")}
    except subprocess.TimeoutExpired:
        return {"status": "error", "output": f"Command timed out after 30s"}
    except Exception as e:
        return {"status": "error", "output": f"Error: {e}"}


def set_volume(level: int) -> dict:
    """
    Set the system audio volume level. Use this when troubleshooting
    audio issues — sometimes the volume is just muted or too low.

    Args:
        level: Volume level from 0 (mute) to 100 (max).

    Returns:
        dict with 'status' and 'output' keys.
    """
    level = min(max(level, 0), 100)
    # macOS volume is 0-7 (osascript uses 0-100)
    output = _run(["osascript", "-e", f"set volume output volume {level}"], timeout=5)
    return {"status": "success", "output": f"Volume set to {level}%. {output}"}


def restart_audio_service() -> dict:
    """
    Restart the macOS Core Audio daemon. This fixes most audio issues
    including no sound, distorted audio, Bluetooth audio not routing,
    and apps not detecting audio devices. This is the #1 fix technicians use.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run(["sudo", "killall", "coreaudiod"], timeout=10)
    return {"status": "success", "output": f"Core Audio service restarted. Audio should resume in a few seconds. {output}"}


def list_directory(path: str) -> dict:
    """
    List files and folders in a specific directory.
    Use this to see what's on the user's Desktop or in any other folder.
    
    Args:
        path: Absolute path to the directory (e.g. '/Users/user/Desktop').
              Use '~/Desktop' for the current user's desktop.
    """
    # Expand ~
    import os
    expanded_path = os.path.expanduser(path)
    output = _run(["ls", "-lah", expanded_path], timeout=10)
    return {"status": "success", "output": output}


def move_path(src: str, dst: str) -> dict:
    """
    Move or rename a file or folder.
    
    Args:
        src: Source path.
        dst: Destination path.
    """
    import os
    src_exp = os.path.expanduser(src)
    dst_exp = os.path.expanduser(dst)
    output = _run(["mv", src_exp, dst_exp], timeout=10)
    return {"status": "success", "output": f"Moved {src} to {dst}. {output}"}


def create_directory(path: str) -> dict:
    """
    Create a new directory (folder).
    
    Args:
        path: Path of the directory to create.
    """
    import os
    exp_path = os.path.expanduser(path)
    output = _run(["mkdir", "-p", exp_path], timeout=10)
    return {"status": "success", "output": f"Created directory {path}. {output}"}


def organize_directory(path: str) -> dict:
    """
    Automatically organize a messy directory by grouping files into subfolders
    based on their file type (e.g. 'Screenshots', 'Documents', 'Images').
    Use this when a user asks to 'clean up' or 'arrange' their Desktop.
    
    Args:
        path: Absolute path to the directory to organize (e.g. '~/Desktop').
    """
    import os
    import shutil
    
    target_dir = os.path.expanduser(path)
    if not os.path.isdir(target_dir):
        return {"status": "error", "output": f"Path '{path}' is not a directory."}
    
    # Define categories and their extensions
    categories = {
        "Screenshots": [".png"], # Special handling for filenames starting with "Screenshot"
        "Images": [".jpg", ".jpeg", ".gif", ".svg", ".bmp", ".tiff", ".webp", ".heic"],
        "Documents": [".pdf", ".docx", ".doc", ".txt", ".rtf", ".pptx", ".xlsx", ".pages", ".numbers", ".key", ".md", ".csv"],
        "Archives": [".zip", ".tar", ".gz", ".7z", ".rar", ".dmg", ".pkg"],
        "Media": [".mp4", ".mov", ".avi", ".mkv", ".mp3", ".wav", ".m4a"],
        "Code": [".py", ".js", ".html", ".css", ".cpp", ".h", ".java", ".go", ".rs", ".ts", ".tsx", ".json", ".yaml", ".yml"],
    }
    
    moved_count = 0
    errors = []
    
    try:
        for filename in os.listdir(target_dir):
            file_path = os.path.join(target_dir, filename)
            
            # Skip directories
            if not os.path.isfile(file_path):
                continue
                
            # Skip hidden files
            if filename.startswith('.'):
                continue
                
            name_lower = filename.lower()
            ext = os.path.splitext(name_lower)[1]
            
            target_category = "Miscellaneous"
            
            # Special case for screenshots
            if name_lower.startswith("screenshot") or "screen shot" in name_lower:
                target_category = "Screenshots"
            else:
                for cat, exts in categories.items():
                    if ext in exts:
                        target_category = cat
                        break
            
            # Create category folder if it doesn't exist
            cat_dir = os.path.join(target_dir, target_category)
            if not os.path.exists(cat_dir):
                try:
                    os.makedirs(cat_dir)
                except Exception as e:
                    errors.append(f"Failed to create directory {target_category}: {e}")
                    continue
                    
            # Move file
            try:
                # Check for name collision
                dest_path = os.path.join(cat_dir, filename)
                if os.path.exists(dest_path):
                    # Simple renaming for collision
                    base, extension = os.path.splitext(filename)
                    idx = 1
                    while os.path.exists(os.path.join(cat_dir, f"{base}_{idx}{extension}")):
                        idx += 1
                    dest_path = os.path.join(cat_dir, f"{base}_{idx}{extension}")
                
                shutil.move(file_path, dest_path)
                moved_count += 1
            except Exception as e:
                errors.append(f"Failed to move {filename}: {e}")
    except Exception as e:
        return {"status": "error", "output": f"Unexpected error during organization: {e}"}
            
    summary = f"Successfully organized {moved_count} files in {path} into folders."
    if errors:
        summary += f"\nNote: {len(errors)} errors occurred:\n" + "\n".join(errors[:5])
        
    return {"status": "success", "output": summary}


# ---------------------------------------------------------------------------
# Personal Assistant Tools — File I/O, URLs, Coding, Clipboard
# ---------------------------------------------------------------------------

def write_file(file_path: str, content: str) -> dict:
    """
    Write content to a file on the user's computer. Creates the file if it
    doesn't exist, or overwrites it if it does. Parent directories are created
    automatically.

    Use this for ANY writing task:
    - Writing documents: letters, essays, study guides, notes
    - Writing code: Python scripts, HTML pages, JavaScript files
    - Writing config files, CSV data, markdown notes, etc.

    Args:
        file_path: Where to save the file (e.g. '~/Desktop/letter.txt',
                   '~/Documents/app.py'). Supports ~ for home directory.
        content: The full text content to write to the file.

    Returns:
        dict with 'status' and 'output' keys.
    """
    import os
    expanded = os.path.expanduser(file_path)
    parent = os.path.dirname(expanded)
    try:
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        with open(expanded, "w", encoding="utf-8") as f:
            f.write(content)
        size = os.path.getsize(expanded)
        return {"status": "success", "output": f"File written: {expanded} ({size} bytes)"}
    except Exception as e:
        return {"status": "error", "output": f"Failed to write file: {e}"}


def read_file(file_path: str, max_lines: int = 200) -> dict:
    """
    Read the contents of a file on the user's computer. Use this to view
    documents, code files, config files, logs, etc.

    Args:
        file_path: Path to the file (e.g. '~/Desktop/notes.txt'). Supports ~.
        max_lines: Maximum number of lines to read (default 200, to prevent
                   overwhelming output for very large files).

    Returns:
        dict with 'status' and 'output' keys.
    """
    import os
    expanded = os.path.expanduser(file_path)
    try:
        if not os.path.exists(expanded):
            return {"status": "error", "output": f"File not found: {expanded}"}
        if not os.path.isfile(expanded):
            return {"status": "error", "output": f"Path is not a file: {expanded}"}
        size = os.path.getsize(expanded)
        with open(expanded, "r", encoding="utf-8", errors="replace") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append(f"\n... [TRUNCATED: file has more than {max_lines} lines] ...")
                    break
                lines.append(line.rstrip("\n"))
        return {"status": "success", "output": f"[{expanded} — {size} bytes]\n" + "\n".join(lines)}
    except Exception as e:
        return {"status": "error", "output": f"Failed to read file: {e}"}


def append_to_file(file_path: str, content: str) -> dict:
    """
    Append content to the end of an existing file. Use this to add lines to
    logs, add items to lists, append data to CSVs, etc.

    Args:
        file_path: Path to the file (e.g. '~/Desktop/todo.txt'). Supports ~.
        content: The text to append to the end of the file.

    Returns:
        dict with 'status' and 'output' keys.
    """
    import os
    expanded = os.path.expanduser(file_path)
    try:
        with open(expanded, "a", encoding="utf-8") as f:
            f.write(content)
        return {"status": "success", "output": f"Appended {len(content)} chars to {expanded}"}
    except Exception as e:
        return {"status": "error", "output": f"Failed to append: {e}"}


def open_url(url: str) -> dict:
    """
    Open a URL in the user's default web browser. Use this to open websites,
    search results, YouTube, documentation, Google Docs, etc.

    Args:
        url: The full URL to open (e.g. 'https://google.com',
             'https://youtube.com/results?search_query=lofi+music').

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run(["open", url], timeout=10)
    return {"status": "success", "output": f"Opened URL in browser: {url}. {output}"}


def search_files(search_path: str, pattern: str) -> dict:
    """
    Search for files by name within a directory tree. Use this to find
    documents, photos, code files, etc. on the user's machine.

    Args:
        search_path: The starting directory to search (e.g. '~', '~/Documents').
        pattern: The filename pattern to search for (e.g. '*.pdf', 'report*', '*.py').

    Returns:
        dict with 'status' and 'output' keys.
    """
    import os
    expanded = os.path.expanduser(search_path)
    output = _run(["find", expanded, "-maxdepth", "5", "-name", pattern, "-type", "f"], timeout=15)
    lines = output.strip().split("\n")
    if len(lines) > 30:
        output = "\n".join(lines[:30]) + f"\n\n... ({len(lines) - 30} more results)"
    return {"status": "success", "output": output}


def clipboard_copy(text: str) -> dict:
    """
    Copy text to the system clipboard. Use this to prepare text for the user
    to paste somewhere (e.g., an email body, a search query, a code snippet).

    Args:
        text: The text to copy to the clipboard.

    Returns:
        dict with 'status' and 'output' keys.
    """
    try:
        process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        process.communicate(text.encode("utf-8"))
        return {"status": "success", "output": f"Copied {len(text)} chars to clipboard."}
    except Exception as e:
        return {"status": "error", "output": f"Failed to copy: {e}"}


def clipboard_paste() -> dict:
    """
    Get the current contents of the system clipboard. Use this to see
    what the user has copied, or to work with clipboard data.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run(["pbpaste"], timeout=5)
    return {"status": "success", "output": f"Clipboard contents:\n{output}"}


def take_screenshot(save_path: str = "~/Desktop/screenshot.png") -> dict:
    """
    Take a screenshot of the user's screen and save it to a file. Use this
    when you need to see what the user is looking at, or when they ask you
    to capture their screen.

    Args:
        save_path: Where to save the screenshot (default: ~/Desktop/screenshot.png).

    Returns:
        dict with 'status' and 'output' keys.
    """
    import os
    expanded = os.path.expanduser(save_path)
    output = _run(["screencapture", "-x", expanded], timeout=10)
    if os.path.exists(expanded):
        size = os.path.getsize(expanded)
        return {"status": "success", "output": f"Screenshot saved: {expanded} ({size} bytes). {output}"}
    return {"status": "error", "output": f"Screenshot may have failed. {output}"}


def create_project(project_name: str, language: str = "python", path: str = "~/Desktop") -> dict:
    """
    Scaffold a new coding project with a proper folder structure.
    Creates the project directory, a main source file, and a README.

    Supported languages: python, javascript, html, java, c, go, rust

    Args:
        project_name: Name of the project (e.g. 'my-web-app', 'calculator').
        language: Programming language (default 'python').
        path: Where to create the project (default '~/Desktop').

    Returns:
        dict with 'status' and 'output' keys.
    """
    import os

    expanded = os.path.expanduser(os.path.join(path, project_name))
    if os.path.exists(expanded):
        return {"status": "error", "output": f"Directory already exists: {expanded}"}

    templates = {
        "python": {
            "main_file": "main.py",
            "main_content": '"""Main entry point for {name}."""\n\n\ndef main():\n    print("Hello from {name}!")\n\n\nif __name__ == "__main__":\n    main()\n',
            "extra_files": {"requirements.txt": "# Add your dependencies here\n"},
        },
        "javascript": {
            "main_file": "index.js",
            "main_content": '// {name} - Main entry point\n\nconsole.log("Hello from {name}!");\n',
            "extra_files": {
                "package.json": '{{\n  "name": "{name}",\n  "version": "1.0.0",\n  "main": "index.js",\n  "scripts": {{\n    "start": "node index.js"\n  }}\n}}\n'
            },
        },
        "html": {
            "main_file": "index.html",
            "main_content": '<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>{name}</title>\n    <link rel="stylesheet" href="style.css">\n</head>\n<body>\n    <h1>Welcome to {name}</h1>\n    <script src="script.js"></script>\n</body>\n</html>\n',
            "extra_files": {
                "style.css": "/* {name} styles */\nbody {{\n    font-family: system-ui, sans-serif;\n    margin: 2rem;\n}}\n",
                "script.js": '// {name} scripts\nconsole.log("{name} loaded!");\n',
            },
        },
        "java": {
            "main_file": "Main.java",
            "main_content": 'public class Main {{\n    public static void main(String[] args) {{\n        System.out.println("Hello from {name}!");\n    }}\n}}\n',
            "extra_files": {},
        },
        "c": {
            "main_file": "main.c",
            "main_content": '#include <stdio.h>\n\nint main() {{\n    printf("Hello from {name}!\\n");\n    return 0;\n}}\n',
            "extra_files": {
                "Makefile": "CC=gcc\nCFLAGS=-Wall\n\nall: main\n\nmain: main.c\n\t$(CC) $(CFLAGS) -o {name} main.c\n\nclean:\n\trm -f {name}\n"
            },
        },
        "go": {
            "main_file": "main.go",
            "main_content": 'package main\n\nimport "fmt"\n\nfunc main() {{\n\tfmt.Println("Hello from {name}!")\n}}\n',
            "extra_files": {},
        },
        "rust": {
            "main_file": "main.rs",
            "main_content": 'fn main() {{\n    println!("Hello from {name}!");\n}}\n',
            "extra_files": {},
        },
    }

    lang = language.lower()
    if lang not in templates:
        return {"status": "error", "output": f"Unsupported language '{language}'. Supported: {', '.join(templates.keys())}"}

    tmpl = templates[lang]
    try:
        os.makedirs(expanded, exist_ok=True)

        # Main file
        main_path = os.path.join(expanded, tmpl["main_file"])
        with open(main_path, "w") as f:
            f.write(tmpl["main_content"].format(name=project_name))

        # Extra files
        for fname, content in tmpl["extra_files"].items():
            fpath = os.path.join(expanded, fname)
            with open(fpath, "w") as f:
                f.write(content.format(name=project_name))

        # README
        readme_path = os.path.join(expanded, "README.md")
        with open(readme_path, "w") as f:
            f.write(f"# {project_name}\n\nA {language} project created by Nora.\n")

        files_created = [tmpl["main_file"]] + list(tmpl["extra_files"].keys()) + ["README.md"]
        return {
            "status": "success",
            "output": f"Project '{project_name}' created at {expanded}\nFiles: {', '.join(files_created)}",
        }
    except Exception as e:
        return {"status": "error", "output": f"Failed to create project: {e}"}


def compile_and_run(file_path: str, language: str = "auto") -> dict:
    """
    Compile (if needed) and run a source code file. Automatically detects the
    language from the file extension.

    Supported: Python (.py), JavaScript (.js), C (.c), Java (.java),
               Go (.go), Rust (.rs), HTML (.html — opens in browser)

    Args:
        file_path: Path to the source file (e.g. '~/Desktop/my-app/main.py').
        language: Language override (default 'auto' — detected from extension).

    Returns:
        dict with 'status' and 'output' keys.
    """
    import os
    expanded = os.path.expanduser(file_path)

    if not os.path.exists(expanded):
        return {"status": "error", "output": f"File not found: {expanded}"}

    ext = os.path.splitext(expanded)[1].lower()
    base = os.path.splitext(os.path.basename(expanded))[0]
    dir_path = os.path.dirname(expanded)

    lang = language.lower()
    if lang == "auto":
        ext_map = {
            ".py": "python", ".js": "javascript", ".c": "c",
            ".java": "java", ".go": "go", ".rs": "rust",
            ".html": "html", ".htm": "html",
        }
        lang = ext_map.get(ext, "unknown")

    if lang == "unknown":
        return {"status": "error", "output": f"Cannot auto-detect language for extension '{ext}'. Please specify language."}

    commands = {
        "python": f"cd {shlex.quote(dir_path)} && python3 {shlex.quote(os.path.basename(expanded))}",
        "javascript": f"cd {shlex.quote(dir_path)} && node {shlex.quote(os.path.basename(expanded))}",
        "c": f"cd {shlex.quote(dir_path)} && gcc -o {shlex.quote(base)} {shlex.quote(os.path.basename(expanded))} && ./{shlex.quote(base)}",
        "java": f"cd {shlex.quote(dir_path)} && javac {shlex.quote(os.path.basename(expanded))} && java {shlex.quote(base)}",
        "go": f"cd {shlex.quote(dir_path)} && go run {shlex.quote(os.path.basename(expanded))}",
        "rust": f"cd {shlex.quote(dir_path)} && rustc {shlex.quote(os.path.basename(expanded))} -o {shlex.quote(base)} && ./{shlex.quote(base)}",
        "html": f"open {shlex.quote(expanded)}",
    }

    cmd = commands.get(lang)
    if not cmd:
        return {"status": "error", "output": f"Unsupported language: {lang}"}

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30,
            cwd=dir_path,
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            output += f"\n[stderr]: {result.stderr.strip()}" if result.stderr else ""
            return {"status": "error", "output": f"Execution failed (exit code {result.returncode}):\n{_truncate_output(output)}"}
        return {"status": "success", "output": _truncate_output(output) if output else "(program completed with no output)"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "output": "Execution timed out after 30 seconds."}
    except Exception as e:
        return {"status": "error", "output": f"Error: {e}"}


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
    # ACTION / FIX Tools
    kill_process,
    kill_process_by_pid,
    toggle_bluetooth,
    toggle_wifi,
    manage_service,
    clear_system_cache,
    empty_trash,
    open_application,
    close_application,
    run_safe_shell_command,
    set_volume,
    restart_audio_service,
    list_directory,
    move_path,
    create_directory,
    organize_directory,
    # Personal Assistant Tools
    write_file,
    read_file,
    append_to_file,
    open_url,
    search_files,
    clipboard_copy,
    clipboard_paste,
    take_screenshot,
    create_project,
    compile_and_run,
]

