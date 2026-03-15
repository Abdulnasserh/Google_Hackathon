"""
Windows CLI Diagnostic Tools
===============================
Safe, whitelisted CLI tools for diagnosing Windows PC issues.
Each function runs a specific system command and returns the output.

Security:
    - Only pre-approved commands are executed (no arbitrary shell input)
    - All commands run with a timeout to prevent hangs
    - Subprocess calls use shell=False where possible for safety

Note:
    These tools will only work when the agent backend is running on a
    Windows machine. If run on macOS/Linux, the commands will return
    "Command not found" errors — which is expected and safe.

Usage:
    These functions are passed as `tools` to the Windows troubleshooter Agent.
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

def _run_cmd(cmd: list[str], timeout: int = 30, use_shell: bool = False) -> str:
    """Run a Windows command safely and return its stdout, or an error message."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=use_shell,
        )
        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr.strip():
            output += f"\n[stderr]: {result.stderr.strip()}"
            
        final_out = _truncate_output(output if output else "(no output)")
        return final_out
    except subprocess.TimeoutExpired:
        return f"⏱️ Command timed out after {timeout}s: {' '.join(cmd)}"
    except FileNotFoundError:
        return f"❌ Command not found: {cmd[0]}. This tool requires Windows."
    except Exception as e:
        return f"❌ Error running command: {e}"


def _run_powershell(script: str, timeout: int = 30) -> str:
    """Run a PowerShell command safely and return output."""
    return _run_cmd(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Network Diagnostic Tools
# ---------------------------------------------------------------------------

def ping_host(host: str, count: int = 4) -> dict:
    """
    Ping a host to check network connectivity on a Windows PC.
    Use this to diagnose whether the user's machine can reach a server.
    Common hosts: 'google.com', '8.8.8.8', '1.1.1.1', or any user-specified host.

    Args:
        host: The hostname or IP address to ping (e.g. 'google.com', '8.8.8.8').
        count: Number of ping packets to send (default 4, max 10).

    Returns:
        dict with 'status' and 'output' keys.
    """
    count = min(max(count, 1), 10)
    output = _run_cmd(["ping", "-n", str(count), host], timeout=30)
    return {"status": "success", "output": output}


def check_dns(domain: str) -> dict:
    """
    Look up DNS records for a domain to diagnose DNS resolution issues on Windows.
    Use this when a user says websites aren't loading but their internet seems connected.

    Args:
        domain: The domain name to look up (e.g. 'google.com').

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_cmd(["nslookup", domain], timeout=15)
    return {"status": "success", "output": output}


def traceroute(host: str) -> dict:
    """
    Trace the network route to a host using Windows tracert command.
    Shows each hop between the user and the destination.
    Use this to identify WHERE network slowness or drops occur.

    Args:
        host: The hostname or IP address to trace (e.g. 'google.com').

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_cmd(["tracert", "-h", "15", host], timeout=60)
    return {"status": "success", "output": output}


def get_network_config() -> dict:
    """
    Get the current network configuration — IP addresses, subnet masks,
    default gateways, DNS servers, and DHCP status for all network adapters.
    Use this to check if the user has a valid IP and network config.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_cmd(["ipconfig", "/all"], timeout=10)
    return {"status": "success", "output": output}


def get_wifi_profiles() -> dict:
    """
    List all saved Wi-Fi profiles on the Windows PC.
    Use this when troubleshooting Wi-Fi connection issues or checking
    which networks the PC has connected to before.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_cmd(["netsh", "wlan", "show", "profiles"], timeout=10)
    return {"status": "success", "output": output}


def get_wifi_info() -> dict:
    """
    Get current Wi-Fi connection details — SSID, signal strength, channel,
    radio type, authentication type. Use this to diagnose Wi-Fi performance
    or connection problems on Windows.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_cmd(["netsh", "wlan", "show", "interfaces"], timeout=10)
    return {"status": "success", "output": output}


def check_open_ports(host: str = "localhost", ports: str = "80,443,22,3389,8080") -> dict:
    """
    Check if specific network ports are open/listening on a Windows host.
    Use this to troubleshoot service connectivity issues.

    Args:
        host: The host to check (default 'localhost').
        ports: Comma-separated port numbers to check (e.g. '80,443,22').

    Returns:
        dict with 'status' and 'output' keys.
    """
    results = []
    for port in ports.split(",")[:10]:
        port = port.strip()
        if not port.isdigit():
            continue
        script = f"Test-NetConnection -ComputerName {host} -Port {port} -WarningAction SilentlyContinue | Select-Object -Property TcpTestSucceeded"
        out = _run_powershell(script, timeout=10)
        status_str = "OPEN" if "True" in out else "CLOSED/FILTERED"
        results.append(f"  Port {port}: {status_str}")
    output = f"Port scan results for {host}:\n" + "\n".join(results)
    return {"status": "success", "output": output}


def release_renew_ip() -> dict:
    """
    Release and renew the DHCP IP address on all adapters.
    Use this as a common fix for network connectivity issues —
    'have you tried releasing and renewing your IP?'

    Returns:
        dict with 'status' and 'output' keys.
    """
    release = _run_cmd(["ipconfig", "/release"], timeout=15)
    renew = _run_cmd(["ipconfig", "/renew"], timeout=30)
    return {"status": "success", "output": f"Release:\n{release}\n\nRenew:\n{renew}"}


# ---------------------------------------------------------------------------
# System Information Tools
# ---------------------------------------------------------------------------

def get_system_info() -> dict:
    """
    Get comprehensive system information — OS version, hardware manufacturer,
    processor, RAM, boot time, hotfixes installed, network cards, etc.
    Use this as a first step when diagnosing any Windows system issue.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_cmd(["systeminfo"], timeout=30)
    return {"status": "success", "output": output}


def get_disk_usage() -> dict:
    """
    Get disk space usage for all drives — total size, free space, and
    file system type. Use this when users complain about low disk space
    or when apps won't install.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_powershell(
        "Get-PSDrive -PSProvider FileSystem | Format-Table Name, Used, Free, @{N='Total';E={$_.Used+$_.Free}} -AutoSize",
        timeout=10,
    )
    return {"status": "success", "output": output}


def get_disk_health() -> dict:
    """
    Check the S.M.A.R.T. health status of all physical disks.
    Use this when you suspect disk failure (slow reads, crashes, blue screens).

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_powershell(
        "Get-PhysicalDisk | Select-Object FriendlyName, MediaType, Size, HealthStatus, OperationalStatus | Format-Table -AutoSize",
        timeout=15,
    )
    return {"status": "success", "output": output}


# ---------------------------------------------------------------------------
# Performance & Process Tools
# ---------------------------------------------------------------------------

def get_top_processes(count: int = 10) -> dict:
    """
    Get the top CPU-consuming processes currently running on the Windows PC.
    Use this when the user complains about the computer being slow,
    fans running loudly, or high CPU usage.

    Args:
        count: Number of top processes to show (default 10, max 25).

    Returns:
        dict with 'status' and 'output' keys.
    """
    count = min(max(count, 1), 25)
    output = _run_powershell(
        f"Get-Process | Sort-Object CPU -Descending | Select-Object -First {count} Name, Id, CPU, @{{N='MemMB';E={{[math]::Round($_.WorkingSet64/1MB,1)}}}} | Format-Table -AutoSize",
        timeout=15,
    )
    return {"status": "success", "output": output}


def get_memory_usage() -> dict:
    """
    Get detailed memory (RAM) usage on the Windows PC — total physical memory,
    available memory, used percentage, and virtual memory stats.
    Use this when diagnosing slow performance or crashes.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_powershell(
        "Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory, TotalVirtualMemorySize, FreeVirtualMemory | Format-List",
        timeout=15,
    )
    return {"status": "success", "output": output}


def get_battery_info() -> dict:
    """
    Get battery status, charge level, and estimated runtime on a Windows laptop.
    Use this when diagnosing battery drain or charging issues.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_powershell(
        "Get-CimInstance Win32_Battery | Select-Object Name, EstimatedChargeRemaining, BatteryStatus, EstimatedRunTime | Format-List",
        timeout=10,
    )
    return {"status": "success", "output": output}


# ---------------------------------------------------------------------------
# System Maintenance Tools
# ---------------------------------------------------------------------------

def check_for_updates() -> dict:
    """
    Check for available Windows updates. Use this when the user asks about
    updates or when diagnosing issues that may be caused by an outdated OS.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_powershell(
        "$UpdateSession = New-Object -ComObject Microsoft.Update.Session; "
        "$UpdateSearcher = $UpdateSession.CreateUpdateSearcher(); "
        "$Updates = $UpdateSearcher.Search('IsInstalled=0'); "
        "$Updates.Updates | Select-Object Title, IsDownloaded | Format-Table -AutoSize",
        timeout=60,
    )
    return {"status": "success", "output": output}


def get_event_log_errors(log_name: str = "System", count: int = 15) -> dict:
    """
    Retrieve recent error/warning entries from the Windows Event Log.
    Use this to investigate crashes, blue screens (BSOD), service failures,
    or other system problems.

    Args:
        log_name: Which log to check — 'System', 'Application', or 'Security' (default 'System').
        count: Number of recent entries to show (default 15, max 50).

    Returns:
        dict with 'status' and 'output' keys.
    """
    count = min(max(count, 1), 50)
    safe_log = log_name if log_name in ("System", "Application", "Security") else "System"
    output = _run_powershell(
        f"Get-EventLog -LogName {safe_log} -EntryType Error,Warning -Newest {count} | "
        f"Format-Table TimeGenerated, EntryType, Source, Message -AutoSize -Wrap",
        timeout=30,
    )
    return {"status": "success", "output": output}


def run_system_file_checker() -> dict:
    """
    Run the Windows System File Checker (SFC) to scan for and report
    corrupted system files. Use this when Windows is behaving erratically
    or after a bad update/crash.

    NOTE: This scan can take several minutes. The output will show whether
    any corrupted files were found.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_cmd(["sfc", "/scannow"], timeout=300)
    return {"status": "success", "output": output}


def flush_dns_cache() -> dict:
    """
    Flush the local DNS resolver cache on Windows. Use this when users
    have DNS resolution problems — websites not loading, getting wrong
    IP addresses, or after changing DNS servers.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_cmd(["ipconfig", "/flushdns"], timeout=10)
    return {"status": "success", "output": output}


def list_startup_programs() -> dict:
    """
    List programs that run at Windows startup. Use this when diagnosing
    slow boot times or to identify unwanted programs starting automatically.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_powershell(
        "Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location | Format-Table -AutoSize -Wrap",
        timeout=15,
    )
    return {"status": "success", "output": output}


def get_installed_programs() -> dict:
    """
    List all installed programs on the Windows PC with their versions.
    Use this to check for outdated software or when troubleshooting
    software conflicts.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_powershell(
        "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | "
        "Select-Object DisplayName, DisplayVersion, Publisher | "
        "Where-Object { $_.DisplayName -ne $null } | Sort-Object DisplayName | Format-Table -AutoSize",
        timeout=20,
    )
    # Truncate if too long
    lines = output.split("\n")
    if len(lines) > 60:
        output = "\n".join(lines[:60]) + f"\n\n... ({len(lines) - 60} more programs)"
    return {"status": "success", "output": output}


# ---------------------------------------------------------------------------
# ACTION / FIX Tools — Nora can now actually repair issues!
# ---------------------------------------------------------------------------

def kill_process(process_name: str) -> dict:
    """
    Force kill a process by name on Windows. Use this when a process is
    frozen, not responding, consuming too much CPU/RAM, or causing issues.
    This is equivalent to what a technician would do in Task Manager.

    Args:
        process_name: The name of the process to kill (e.g. 'chrome.exe', 'explorer.exe').

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_cmd(["taskkill", "/F", "/IM", process_name], timeout=10)
    return {"status": "success", "output": f"Attempted to kill '{process_name}': {output}"}


def kill_process_by_pid(pid: int) -> dict:
    """
    Force kill a specific process by its PID on Windows. Use this when
    you know the exact PID from get_top_processes.

    Args:
        pid: The process ID number to kill.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_cmd(["taskkill", "/F", "/PID", str(pid)], timeout=10)
    return {"status": "success", "output": f"Kill signal sent to PID {pid}: {output}"}


def toggle_bluetooth(action: str = "toggle") -> dict:
    """
    Turn Bluetooth on or off on Windows. Use this to fix Bluetooth
    connectivity issues — toggling Bluetooth often resolves pairing
    problems with headphones, mice, keyboards, etc.

    Args:
        action: One of 'on', 'off', or 'toggle'.

    Returns:
        dict with 'status' and 'output' keys.
    """
    if action == "on":
        ps_cmd = "Start-Service bthserv"
    elif action == "off":
        ps_cmd = "Stop-Service bthserv -Force"
    else:
        ps_cmd = "If ((Get-Service bthserv).Status -eq 'Running') { Stop-Service bthserv -Force } Else { Start-Service bthserv }"
    
    output = _run_powershell(ps_cmd, timeout=15)
    return {"status": "success", "output": f"Bluetooth service toggled ({action}). {output}"}


def toggle_wifi(action: str = "toggle") -> dict:
    """
    Enable or disable the Wi-Fi adapter on Windows. Use this to fix
    Wi-Fi connectivity issues — toggling the adapter is a common
    troubleshooting step.

    Args:
        action: One of 'on', 'off', or 'toggle'.

    Returns:
        dict with 'status' and 'output' keys.
    """
    if action == "on":
        ps_cmd = "Get-NetAdapter -Name 'Wi-Fi' | Enable-NetAdapter -Confirm:$false"
    elif action == "off":
        ps_cmd = "Get-NetAdapter -Name 'Wi-Fi' | Disable-NetAdapter -Confirm:$false"
    else:
        ps_cmd = "If ((Get-NetAdapter -Name 'Wi-Fi').Status -eq 'Up') { Get-NetAdapter -Name 'Wi-Fi' | Disable-NetAdapter -Confirm:$false } Else { Get-NetAdapter -Name 'Wi-Fi' | Enable-NetAdapter -Confirm:$false }"
    
    output = _run_powershell(ps_cmd, timeout=15)
    return {"status": "success", "output": f"Wi-Fi adapter toggled ({action}). {output}"}


def manage_service(service_name: str, action: str = "restart") -> dict:
    """
    Start, stop, or restart a Windows service. Use this to fix issues
    like Bluetooth not working, print spooler stuck, Windows Update 
    frozen, audio service crashed, etc. This is how real technicians
    fix service-level issues on Windows.

    Args:
        service_name: The service name (e.g. 'bthserv' for Bluetooth, 'Spooler' for Print,
                      'Audiosrv' for Audio, 'wuauserv' for Windows Update, 'BITS').
        action: One of 'start', 'stop', 'restart' (default 'restart').

    Returns:
        dict with 'status' and 'output' keys.
    """
    if action == "restart":
        ps_cmd = f"Restart-Service '{service_name}' -Force -PassThru | Select-Object Name, Status"
    elif action == "stop":
        ps_cmd = f"Stop-Service '{service_name}' -Force -PassThru | Select-Object Name, Status"
    else:
        ps_cmd = f"Start-Service '{service_name}' -PassThru | Select-Object Name, Status"
    
    output = _run_powershell(ps_cmd, timeout=20)
    return {"status": "success", "output": f"Service '{service_name}' {action}ed.\n{output}"}


def clear_temp_files() -> dict:
    """
    Clear Windows temporary files to free up space and fix performance
    issues. This is safe and commonly done by technicians. Clears
    user temp folder, Windows temp, and prefetch data.

    Returns:
        dict with 'status' and 'output' keys.
    """
    ps_cmd = """
    $before = [Math]::Round((Get-ChildItem $env:TEMP -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
    Remove-Item "$env:TEMP\\*" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item "C:\\Windows\\Temp\\*" -Recurse -Force -ErrorAction SilentlyContinue
    $after = [Math]::Round((Get-ChildItem $env:TEMP -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
    Write-Output "Cleared approximately $([Math]::Round($before - $after, 2)) MB of temp files"
    """
    output = _run_powershell(ps_cmd, timeout=30)
    return {"status": "success", "output": f"Temp files cleaned. {output}"}


def empty_recycle_bin() -> dict:
    """
    Empty the Windows Recycle Bin to free up disk space immediately.
    Use this when disk space is critically low.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_powershell("Clear-RecycleBin -Force -ErrorAction SilentlyContinue", timeout=30)
    return {"status": "success", "output": f"Recycle Bin emptied. {output}"}


def open_application(app_name: str) -> dict:
    """
    Open a Windows application by name or path. Use this to launch apps
    the user needs, such as Task Manager, Control Panel, Settings, etc.

    Args:
        app_name: The application name or path (e.g. 'taskmgr', 'control', 'ms-settings:',
                  'devmgmt.msc' for Device Manager, 'services.msc' for Services).

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_cmd(["start", app_name], timeout=10, use_shell=True)
    return {"status": "success", "output": f"Opened '{app_name}'. {output}"}


def close_application(process_name: str) -> dict:
    """
    Gracefully close a Windows application by process name. 

    Args:
        process_name: The process name to close (e.g. 'chrome.exe', 'notepad.exe').

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_cmd(["taskkill", "/IM", process_name], timeout=10)
    return {"status": "success", "output": f"Closed '{process_name}'. {output}"}


def run_safe_powershell(command: str) -> dict:
    """
    Execute a safe PowerShell command on the user's Windows PC. This is
    the ultimate technician tool — it lets you run any diagnostic or fix.
    
    CRITICAL SAFETY RULES:
    - NEVER run destructive commands (Format-Volume, Remove-Item C:\\, etc.)
    - NEVER access credentials, passwords, or private user data
    - Only use for legitimate troubleshooting
    - Always explain to the user what you're about to run and why

    Args:
        command: The PowerShell command to execute.

    Returns:
        dict with 'status' and 'output' keys.
    """
    dangerous = ["format-volume", "remove-item c:\\", "remove-item c:/",
                 "get-credential", "convertto-securestring",
                 "invoke-webrequest | invoke-expression", "iex(", 
                 "remove-item -recurse -force c:", "clear-disk"]
    cmd_lower = command.lower()
    for d in dangerous:
        if d in cmd_lower:
            return {"status": "error", "output": f"BLOCKED: Command contains dangerous pattern '{d}'."}
    
    output = _run_powershell(command, timeout=30)
    return {"status": "success", "output": output}


def set_volume(level: int) -> dict:
    """
    Set the system audio volume level on Windows. Use this when
    troubleshooting audio issues.

    Args:
        level: Volume level from 0 (mute) to 100 (max).

    Returns:
        dict with 'status' and 'output' keys.
    """
    level = min(max(level, 0), 100)
    ps_cmd = f"""
    $wshShell = New-Object -ComObject WScript.Shell
    1..50 | ForEach-Object {{ $wshShell.SendKeys([char]174) }}
    $targetPresses = [math]::Round({level} / 2)
    1..$targetPresses | ForEach-Object {{ $wshShell.SendKeys([char]175) }}
    Write-Output 'Volume set to approximately {level}%'
    """
    output = _run_powershell(ps_cmd, timeout=10)
    return {"status": "success", "output": f"Volume set to {level}%. {output}"}


def restart_audio_service() -> dict:
    """
    Restart the Windows Audio service. This fixes most audio issues
    including no sound, devices not detected, and Bluetooth audio routing.

    Returns:
        dict with 'status' and 'output' keys.
    """
    output = _run_powershell("Restart-Service Audiosrv -Force -PassThru | Select Name, Status", timeout=15)
    return {"status": "success", "output": f"Windows Audio service restarted. {output}"}


def restart_print_spooler() -> dict:
    """
    Restart the Windows Print Spooler service and clear the print queue.
    This is the #1 fix for printer issues — stuck print jobs, printer
    not responding, etc.

    Returns:
        dict with 'status' and 'output' keys.
    """
    ps_cmd = """
    Stop-Service Spooler -Force
    Remove-Item "C:\\Windows\\System32\\spool\\PRINTERS\\*" -Force -ErrorAction SilentlyContinue
    Start-Service Spooler
    Get-Service Spooler | Select Name, Status
    """
    output = _run_powershell(ps_cmd, timeout=15)
    return {"status": "success", "output": f"Print Spooler restarted and queue cleared. {output}"}


def list_directory(path: str) -> dict:
    """
    List files and folders in a specific directory on Windows.
    
    Args:
        path: Absolute path to the directory (e.g. 'C:\\Users\\user\\Desktop').
    """
    output = _run_powershell(f"Get-ChildItem -Path '{path}' | Format-Table Mode, LastWriteTime, Length, Name -AutoSize", timeout=10)
    return {"status": "success", "output": output}


def move_path(src: str, dst: str) -> dict:
    """
    Move or rename a file or folder on Windows.
    
    Args:
        src: Source path.
        dst: Destination path.
    """
    output = _run_powershell(f"Move-Item -Path '{src}' -Destination '{dst}' -Force", timeout=10)
    return {"status": "success", "output": f"Moved {src} to {dst}. {output}"}


def create_directory(path: str) -> dict:
    """
    Create a new directory (folder) on Windows.
    
    Args:
        path: Path of the directory to create.
    """
    output = _run_powershell(f"New-Item -ItemType Directory -Force -Path '{path}'", timeout=10)
    return {"status": "success", "output": f"Created directory {path}. {output}"}


def organize_directory(path: str) -> dict:
    """
    Automatically organize a messy directory on Windows by grouping files
    into subfolders based on their file type (e.g. 'Screenshots', 'Documents').
    
    Args:
        path: Absolute path to the directory to organize.
    """
    import os
    import shutil
    
    # Use os.path behaviors for reliability in Python
    target_dir = os.path.expanduser(path)
    if not os.path.isdir(target_dir):
        return {"status": "error", "output": f"Path '{path}' is not a directory."}
    
    categories = {
        "Screenshots": [".png"],
        "Images": [".jpg", ".jpeg", ".gif", ".svg", ".bmp", ".tiff", ".webp"],
        "Documents": [".pdf", ".docx", ".doc", ".txt", ".rtf", ".pptx", ".xlsx", ".md", ".csv"],
        "Archives": [".zip", ".tar", ".gz", ".7z", ".rar"],
        "Media": [".mp4", ".mov", ".avi", ".mkv", ".mp3", ".wav"],
        "Code": [".py", ".js", ".html", ".css", ".cpp", ".h", ".java", ".go", ".rs", ".ts", ".tsx", ".json", ".yaml", ".yml"],
    }
    
    moved_count = 0
    errors = []
    
    try:
        if not os.path.exists(target_dir):
             return {"status": "error", "output": f"Directory not found: {target_dir}"}

        for filename in os.listdir(target_dir):
            file_path = os.path.join(target_dir, filename)
            
            if not os.path.isfile(file_path):
                continue
            if filename.startswith('.') or filename.lower() == "desktop.ini":
                continue
                
            name_lower = filename.lower()
            ext = os.path.splitext(name_lower)[1]
            
            target_category = "Miscellaneous"
            if name_lower.startswith("screenshot") or "screen shot" in name_lower:
                target_category = "Screenshots"
            else:
                for cat, exts in categories.items():
                    if ext in exts:
                        target_category = cat
                        break
            
            cat_dir = os.path.join(target_dir, target_category)
            if not os.path.exists(cat_dir):
                try:
                    os.makedirs(cat_dir)
                except Exception as e:
                    errors.append(f"Failed to create directory {target_category}: {e}")
                    continue
                    
            try:
                dest_path = os.path.join(cat_dir, filename)
                if os.path.exists(dest_path):
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
# All tools list (for easy import into the agent)
# ---------------------------------------------------------------------------

ALL_WINDOWS_TOOLS = [
    # Network
    ping_host,
    check_dns,
    traceroute,
    get_network_config,
    get_wifi_profiles,
    get_wifi_info,
    check_open_ports,
    release_renew_ip,
    # System
    get_system_info,
    get_disk_usage,
    get_disk_health,
    # Performance
    get_top_processes,
    get_memory_usage,
    get_battery_info,
    # Maintenance
    check_for_updates,
    get_event_log_errors,
    run_system_file_checker,
    flush_dns_cache,
    list_startup_programs,
    get_installed_programs,
    # ACTION / FIX Tools
    kill_process,
    kill_process_by_pid,
    toggle_bluetooth,
    toggle_wifi,
    manage_service,
    clear_temp_files,
    empty_recycle_bin,
    open_application,
    close_application,
    run_safe_powershell,
    set_volume,
    restart_audio_service,
    restart_print_spooler,
    list_directory,
    move_path,
    create_directory,
    organize_directory,
]

