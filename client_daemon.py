import asyncio
import json
import websockets
import platform
import logging
import atexit

from bidi_streaming_agent.tools import mac_tools, windows_tools
from bidi_streaming_agent.tools.terminal_session import (
    terminal_manager,
    ALL_TERMINAL_TOOLS,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("NoraDaemon")


def _cleanup():
    """Kill all terminal sessions on shutdown."""
    terminal_manager.kill_all()

atexit.register(_cleanup)


async def daemon_loop(url: str, session_id: str):
    os_sys = platform.system()
    ws_url = f"{url}/ws/daemon/{session_id}"
    logger.info(f"Connecting to Nora Live Technician securely at: {ws_url}")
    logger.info(f"Detected OS: {os_sys}")
    
    if os_sys == "Darwin":
        tools_module = mac_tools
    elif os_sys == "Windows":
        tools_module = windows_tools
    else:
        logger.warning("Unsupported OS. Falling back to Mac tools as best effort.")
        tools_module = mac_tools

    # Build a map of ALL available tools (hardcoded + terminal)
    # Hardcoded tools run with exact parameters
    # Terminal tools give the AI free-form shell access
    terminal_tool_map = {t.__name__: t for t in ALL_TERMINAL_TOOLS}

    async for websocket in websockets.connect(ws_url):
        logger.info("Connected to Cloud Backend! Waiting for remote commands...")
        try:
            # Send initial presence payload
            await websocket.send(json.dumps({"type": "init", "os": os_sys}))
            
            async for message in websocket:
                data = json.loads(message)
                if data.get("type") == "tool_call":
                    call_id = data.get("call_id")
                    tool_name = data.get("tool_name")
                    args = data.get("args", {})
                    
                    logger.info(f"Executing: {tool_name}({args})")
                    
                    # Priority 1: Check terminal tools (dynamic execution)
                    if tool_name in terminal_tool_map:
                        tool_func = terminal_tool_map[tool_name]
                        try:
                            result = tool_func(**args)
                        except Exception as e:
                            result = {"status": "error", "output": f"Terminal tool error: {e}"}
                    
                    # Priority 2: Check OS-specific hardcoded tools
                    elif hasattr(tools_module, tool_name):
                        tool_func = getattr(tools_module, tool_name)
                        try:
                            result = tool_func(**args)
                        except Exception as e:
                            result = {"status": "error", "output": f"Exception running {tool_name}: {str(e)}"}
                    
                    else:
                        result = {"status": "error", "output": f"Tool '{tool_name}' is not available on this OS ({os_sys})."}
                    
                    response = {
                        "type": "tool_result",
                        "call_id": call_id,
                        "result": json.dumps(result)
                    }
                    await websocket.send(json.dumps(response))
                    
                elif data.get("type") == "terminal_stream":
                    # Future: real-time output streaming requests
                    session_id_req = data.get("session_id", "default")
                    lines = data.get("lines", 20)
                    try:
                        session = terminal_manager.get_or_create(session_id_req)
                        output = session.get_recent_output(lines=lines)
                        await websocket.send(json.dumps({
                            "type": "terminal_output",
                            "output": output,
                        }))
                    except Exception as e:
                        await websocket.send(json.dumps({
                            "type": "terminal_output",
                            "output": {"status": "error", "output": str(e)},
                        }))
                        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection closed. Reconnecting in 3 seconds...")
            await asyncio.sleep(3)
            continue
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await asyncio.sleep(3)

def main():
    print("╔══════════════════════════════════════════════╗")
    print("║   Nora AI Technician — Secure Client Daemon  ║")
    print("║   Full Computer Control · Diagnose & Fix      ║")
    print("╠══════════════════════════════════════════════╣")
    print("║  This daemon gives Nora autonomous control    ║")
    print("║  over your machine to diagnose AND fix issues. ║")
    print("║                                                ║")
    print("║  Capabilities:                                 ║")
    print("║   • Run diagnostic scans                       ║")
    print("║   • Execute terminal commands                  ║")
    print("║   • Restart services                           ║")
    print("║   • Kill frozen processes                      ║")
    print("║   • Toggle hardware (Wi-Fi, Bluetooth)         ║")
    print("║   • And much more...                           ║")
    print("╚══════════════════════════════════════════════╝\n")
    
    session_id = input("Enter the 8-character Session ID from the Web UI: ").strip()
    if not session_id:
        print("Session ID is required. Exiting.")
        return

    default_url = "ws://localhost:8000"
    url = input(f"Enter backend URL (default {default_url}): ").strip()
    if not url:
        url = default_url
    
    # Auto-sanitize URL for common user mistakes (e.g. pasting http instead of ws)
    if url.startswith("https://"):
        url = url.replace("https://", "wss://", 1)
    elif url.startswith("http://"):
        url = url.replace("http://", "ws://", 1)
    
    # Remove trailing slash which breaks concatenation
    url = url.rstrip("/")

    try:
        asyncio.run(daemon_loop(url, session_id))
    except KeyboardInterrupt:
        print("\nDaemon stopped by user.")
    finally:
        terminal_manager.kill_all()

if __name__ == "__main__":
    main()
