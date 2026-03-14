"""
Terminal Session Manager — Persistent Interactive Shell
========================================================
Provides a stateful, interactive terminal session on the user's machine.
The AI agent can:
  1. Execute any command and get real-time streaming output
  2. Send input to interactive prompts (y/n, passwords, etc.)
  3. Maintain directory state across commands (cd persists)
  4. Run long background tasks without blocking

Architecture:
    ┌──────────────────┐         ┌──────────────────────────┐
    │  Cloud Backend   │  WS ──► │  Client Daemon           │
    │  (tool calls)    │ ◄── WS  │  TerminalSessionManager  │
    │                  │         │    └── PTY subprocess     │
    └──────────────────┘         └──────────────────────────┘

This runs ON THE DAEMON (user's machine), not on Cloud Run.

Security:
    - Blocklist of dangerous command patterns
    - Maximum output buffer size to prevent memory bombs
    - Configurable timeout per command
    - Sessions auto-cleanup on daemon shutdown
"""

import subprocess
import threading
import time
import queue
import os
import platform
import shlex
from typing import Optional


# ---------------------------------------------------------------------------
# Safety: Command blocklist (shared across Mac + Windows)
# ---------------------------------------------------------------------------
DANGEROUS_PATTERNS = [
    # Filesystem destruction
    "rm -rf /", "rm -rf ~", "rm -rf /*", "rm -rf .",
    "del /s /q c:\\", "format c:", "format d:",
    "diskutil eraseDisk", "diskutil erase",
    "mkfs", "dd if=",
    # Data exfiltration / credential theft
    "security find-generic-password", "security find-internet-password",
    "security dump-keychain",
    "Get-Credential", "ConvertTo-SecureString",
    "cmdkey /list",
    "passwd", "dscl . -passwd",
    # Remote code execution
    "curl | bash", "curl | sh", "wget | bash", "wget | sh",
    "Invoke-WebRequest | Invoke-Expression", "iex(",
    "powershell -enc", "powershell -encodedcommand",
    # Boot / firmware
    "> /dev/sda", "> /dev/disk",
    "bcdedit", "bcdboot",
    # Ransomware-like
    "cipher /w:", "sdelete",
]

# Commands we allow even though they look risky (because we use them ourselves)
ALLOW_PATTERNS = [
    "launchctl", "systemctl", "sc ", "net start", "net stop",
]


def is_command_safe(command: str) -> tuple[bool, str]:
    """Check if a command is safe to execute. Returns (is_safe, reason)."""
    cmd_lower = command.lower().strip()
    
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in cmd_lower:
            # Check if it's in our allow list
            allowed = any(a.lower() in cmd_lower for a in ALLOW_PATTERNS)
            if not allowed:
                return False, f"BLOCKED: Contains dangerous pattern '{pattern}'"
    
    return True, "OK"


# ---------------------------------------------------------------------------
# Terminal Session — A single persistent shell instance
# ---------------------------------------------------------------------------
class TerminalSession:
    """
    A persistent, interactive terminal session using subprocess.
    
    Unlike subprocess.run() which is fire-and-forget, this keeps a shell
    process alive so:
      - Directory changes persist (cd /tmp → next command runs in /tmp)
      - Environment variables persist
      - You can send input to interactive prompts
      - Output is streamed in real-time via a thread-safe queue
    """
    
    def __init__(self, session_id: str, shell: Optional[str] = None):
        self.session_id = session_id
        self.created_at = time.time()
        self.last_activity = time.time()
        self._output_buffer: list[str] = []
        self._output_queue: queue.Queue = queue.Queue()
        self._max_buffer_lines = 500
        self._is_alive = False
        self._process: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        
        # Determine the shell to use
        system = platform.system()
        if shell:
            self.shell = shell
        elif system == "Windows":
            self.shell = "powershell.exe"
        else:
            self.shell = "/bin/bash"
    
    def start(self) -> dict:
        """Start the persistent shell process."""
        try:
            # Build shell command
            if "powershell" in self.shell.lower():
                cmd = [self.shell, "-NoProfile", "-NoLogo", "-NonInteractive"]
            else:
                cmd = [self.shell, "--norc", "--noprofile"]
            
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1,  # Line-buffered
                env={**os.environ},
                cwd=os.path.expanduser("~"),
            )
            self._is_alive = True
            
            # Start background reader thread
            self._reader_thread = threading.Thread(
                target=self._read_output_loop,
                daemon=True,
                name=f"terminal-reader-{self.session_id}",
            )
            self._reader_thread.start()
            
            return {
                "status": "success",
                "session_id": self.session_id,
                "shell": self.shell,
                "pid": self._process.pid,
                "output": f"Terminal session started ({self.shell}, PID {self._process.pid})",
            }
        except Exception as e:
            self._is_alive = False
            return {"status": "error", "output": f"Failed to start terminal: {e}"}
    
    def _read_output_loop(self):
        """Background thread: continuously reads stdout and buffers it."""
        try:
            while self._is_alive and self._process and self._process.stdout:
                line = self._process.stdout.readline()
                if not line:
                    break
                self._output_queue.put(line)
                self._output_buffer.append(line)
                # Trim buffer if too large
                if len(self._output_buffer) > self._max_buffer_lines:
                    self._output_buffer = self._output_buffer[-self._max_buffer_lines:]
                self.last_activity = time.time()
        except Exception:
            pass
        finally:
            self._is_alive = False
    
    def execute(self, command: str, timeout: float = 30.0) -> dict:
        """
        Execute a command in the persistent shell and return the output.
        
        The command is written to stdin of the running shell process.
        A unique delimiter marker is appended so we know when the output
        for THIS specific command ends.
        """
        if not self._is_alive or not self._process or not self._process.stdin:
            return {"status": "error", "output": "Terminal session is not running. Call start_terminal first."}
        
        # Safety check
        is_safe, reason = is_command_safe(command)
        if not is_safe:
            return {"status": "error", "output": reason}
        
        self.last_activity = time.time()
        
        # Drain any pending output from previous commands
        while not self._output_queue.empty():
            try:
                self._output_queue.get_nowait()
            except queue.Empty:
                break
        
        # Use a unique end‐marker so we know when the command's output is done
        marker = f"__NORA_CMD_DONE_{int(time.time() * 1000)}__"
        
        try:
            system = platform.system()
            if system == "Windows":
                # PowerShell: execute and print marker
                full_cmd = f"{command}\nWrite-Output '{marker}'\n"
            else:
                # Bash: execute and echo marker
                full_cmd = f"{command}\necho '{marker}'\n"
            
            self._process.stdin.write(full_cmd)
            self._process.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            self._is_alive = False
            return {"status": "error", "output": f"Terminal session died: {e}"}
        
        # Collect output until we see the marker or timeout
        output_lines = []
        deadline = time.time() + timeout
        
        while time.time() < deadline:
            try:
                line = self._output_queue.get(timeout=0.1)
                # Check if this line contains our end marker
                if marker in line:
                    break
                output_lines.append(line.rstrip("\n").rstrip("\r"))
            except queue.Empty:
                continue
        
        output_text = "\n".join(output_lines)
        
        # Smart truncation for very long outputs
        if len(output_text) > 4000:
            half = 2000
            output_text = (
                output_text[:half]
                + f"\n\n...[TRUNCATED {len(output_text) - 4000} chars]...\n\n"
                + output_text[-half:]
            )
        
        return {
            "status": "success",
            "output": output_text if output_text else "(command completed with no output)",
        }
    
    def send_input(self, text: str) -> dict:
        """Send raw input to the terminal (for responding to interactive prompts)."""
        if not self._is_alive or not self._process or not self._process.stdin:
            return {"status": "error", "output": "Terminal session is not running."}
        
        try:
            self._process.stdin.write(text + "\n")
            self._process.stdin.flush()
            self.last_activity = time.time()
            
            # Wait briefly and collect any response
            time.sleep(0.5)
            response_lines = []
            while not self._output_queue.empty():
                try:
                    response_lines.append(self._output_queue.get_nowait().rstrip("\n"))
                except queue.Empty:
                    break
            
            return {
                "status": "success",
                "output": "\n".join(response_lines) if response_lines else "(input sent, waiting for response...)",
            }
        except Exception as e:
            return {"status": "error", "output": f"Failed to send input: {e}"}
    
    def get_recent_output(self, lines: int = 50) -> dict:
        """Get the most recent N lines of output from the terminal buffer."""
        # Also drain queue into buffer
        while not self._output_queue.empty():
            try:
                line = self._output_queue.get_nowait()
                self._output_buffer.append(line)
            except queue.Empty:
                break
        
        recent = self._output_buffer[-lines:]
        return {
            "status": "success",
            "alive": self._is_alive,
            "total_lines": len(self._output_buffer),
            "output": "".join(recent) if recent else "(no output yet)",
        }
    
    def kill(self) -> dict:
        """Terminate the terminal session."""
        self._is_alive = False
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
        return {"status": "success", "output": f"Terminal session {self.session_id} terminated."}


# ---------------------------------------------------------------------------
# Session Manager — manages multiple terminal sessions
# ---------------------------------------------------------------------------
class TerminalSessionManager:
    """Manages multiple terminal sessions (one per daemon connection)."""
    
    def __init__(self):
        self._sessions: dict[str, TerminalSession] = {}
    
    def get_or_create(self, session_id: str = "default") -> TerminalSession:
        """Get existing session or create a new one."""
        if session_id not in self._sessions or not self._sessions[session_id]._is_alive:
            session = TerminalSession(session_id)
            result = session.start()
            if result["status"] == "success":
                self._sessions[session_id] = session
            else:
                raise RuntimeError(result["output"])
        return self._sessions[session_id]
    
    def kill_session(self, session_id: str = "default") -> dict:
        """Kill a specific session."""
        if session_id in self._sessions:
            result = self._sessions[session_id].kill()
            del self._sessions[session_id]
            return result
        return {"status": "error", "output": f"No session '{session_id}' found."}
    
    def kill_all(self):
        """Kill all sessions (called on daemon shutdown)."""
        for sid in list(self._sessions.keys()):
            self._sessions[sid].kill()
        self._sessions.clear()
    
    def list_sessions(self) -> dict:
        """List all active sessions."""
        sessions = []
        for sid, s in self._sessions.items():
            sessions.append({
                "session_id": sid,
                "shell": s.shell,
                "alive": s._is_alive,
                "age_seconds": round(time.time() - s.created_at),
                "idle_seconds": round(time.time() - s.last_activity),
            })
        return {"status": "success", "sessions": sessions}


# ---------------------------------------------------------------------------
# Global singleton — used by the daemon
# ---------------------------------------------------------------------------
terminal_manager = TerminalSessionManager()


# ---------------------------------------------------------------------------
# Tool functions — These are the tools exposed to the AI agent
# ---------------------------------------------------------------------------

def execute_command(command: str, timeout: int = 30) -> dict:
    """
    Execute ANY command in a persistent interactive terminal on the user's machine.
    This is your most powerful tool — it gives you full control of the user's computer,
    just like a real technician sitting at their desk.
    
    The terminal session is PERSISTENT — directory changes, environment variables,
    and state carry over between calls. For example:
      1. execute_command("cd /tmp")
      2. execute_command("ls")  ← this lists /tmp contents
    
    You can run ANY bash (macOS/Linux) or PowerShell (Windows) command:
    - System diagnostics: "systemctl status bluetooth", "Get-Service Spooler"
    - Fix services: "launchctl kickstart -k system/com.apple.bluetoothd"
    - Process control: "kill -9 1234", "taskkill /F /PID 1234"
    - Network fixes: "networksetup -setairportpower en0 off && sleep 2 && networksetup -setairportpower en0 on"
    - File operations: "ls -la ~/Desktop", "dir C:\\Users"
    - Package management: "brew install htop", "winget install --id Microsoft.PowerToys"
    - Multi-step scripts: chain commands with && or ;
    
    The AI determines WHAT commands to run based on its extensive knowledge of
    operating systems. You are NOT limited to predefined tools.
    
    SAFETY: Dangerous commands (rm -rf /, format C:, etc.) are automatically blocked.
    
    Args:
        command: The bash or PowerShell command to execute.
        timeout: Maximum seconds to wait for output (default 30).
    
    Returns:
        dict with 'status' and 'output' keys.
    """
    try:
        session = terminal_manager.get_or_create("default")
        return session.execute(command, timeout=float(timeout))
    except Exception as e:
        return {"status": "error", "output": f"Terminal error: {e}"}


def send_terminal_input(text: str) -> dict:
    """
    Send input to an interactive prompt in the terminal. Use this when a
    previously executed command is waiting for user input (e.g., "Are you
    sure? [y/N]", "Enter password:", "Press Enter to continue").
    
    This is what makes you different from a simple script — you can
    interact with complex CLI tools that require back-and-forth dialog.
    
    Args:
        text: The text to send as input (e.g., "y", "yes", "1", etc.)
    
    Returns:
        dict with 'status' and 'output' keys.
    """
    try:
        session = terminal_manager.get_or_create("default")
        return session.send_input(text)
    except Exception as e:
        return {"status": "error", "output": f"Terminal error: {e}"}


def get_terminal_output(lines: int = 50) -> dict:
    """
    Get the most recent output from the terminal session. Use this to
    check on the progress of a long-running command, or to see what
    happened after sending input to an interactive prompt.
    
    Args:
        lines: Number of recent lines to retrieve (default 50).
    
    Returns:
        dict with 'status', 'output', 'alive', and 'total_lines' keys.
    """
    try:
        session = terminal_manager.get_or_create("default")
        return session.get_recent_output(lines=lines)
    except Exception as e:
        return {"status": "error", "output": f"Terminal error: {e}"}


# ---------------------------------------------------------------------------
# All terminal tools list
# ---------------------------------------------------------------------------
ALL_TERMINAL_TOOLS = [
    execute_command,
    send_terminal_input,
    get_terminal_output,
]
