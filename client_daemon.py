import asyncio
import json
import websockets
import platform
import atexit
import sys

from bidi_streaming_agent.tools import mac_tools, windows_tools
from bidi_streaming_agent.tools.terminal_session import (
    terminal_manager,
    ALL_TERMINAL_TOOLS,
)

# Custom hacker-style ANSI UI
class UI:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    @staticmethod
    def info(msg):
        print(f"{UI.CYAN}●{UI.RESET} {UI.DIM}{msg}{UI.RESET}")

    @staticmethod
    def success(msg):
        print(f"{UI.GREEN}✓{UI.RESET} {msg}")
        
    @staticmethod
    def warning(msg):
        print(f"{UI.YELLOW}⚠{UI.RESET} {msg}")

    @staticmethod
    def error(msg):
        print(f"{UI.RED}✖{UI.RESET} {UI.BOLD}{msg}{UI.RESET}")

    @staticmethod
    def executing(tool, args):
        print()
        print(f"{UI.MAGENTA}⚡ NORA EXECUTING AUTONOMOUS COMMAND{UI.RESET}")
        print(f"  {UI.DIM}Task Agent:{UI.RESET} {tool}")
        if 'command' in args or 'cmd' in args:
            cmd = args.get('command') or args.get('cmd')
            print(f"  {UI.DIM}Cmd:{UI.RESET}  {UI.BOLD}{UI.GREEN}>{UI.RESET} {cmd}")
        elif args:
            print(f"  {UI.DIM}Args:{UI.RESET} {json.dumps(args)}")
        print()
        
    @staticmethod
    def result_status(status, output):
        if status == "success":
            print(f"  {UI.GREEN}↳ Process Completed{UI.RESET}")
            if output:
                # Truncate output for visuals if needed, but here just show raw
                out_str = str(output).strip()
                if len(out_str) > 200:
                    out_str = out_str[:197] + "..."
                if out_str and out_str != "None":
                    print(f"  {UI.DIM}Output: {out_str}{UI.RESET}")
        else:
            print(f"  {UI.RED}↳ Task Failed{UI.RESET} {UI.DIM}({output}){UI.RESET}")


def _cleanup():
    """Kill all terminal sessions on shutdown."""
    UI.info("Shutting down terminal sessions...")
    terminal_manager.kill_all()

atexit.register(_cleanup)


async def daemon_loop(url: str, session_id: str):
    os_sys = platform.system()
    ws_url = f"{url}/ws/daemon/{session_id}"
    
    UI.info(f"Target Gateway: {UI.BOLD}{ws_url}{UI.RESET}")
    UI.info(f"Host OS Detected: {UI.BOLD}{os_sys}{UI.RESET}")
    
    if os_sys == "Darwin":
        tools_module = mac_tools
    elif os_sys == "Windows":
        tools_module = windows_tools
    else:
        UI.warning("Unsupported OS. Falling back to Mac tools as best effort.")
        tools_module = mac_tools

    terminal_tool_map = {t.__name__: t for t in ALL_TERMINAL_TOOLS}

    while True:
        try:
            UI.info(f"Attempting secure connection to Nora...")
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as websocket:
                UI.success(f"Uplink Established! {UI.BOLD}Nora is now your Active Assistant.{UI.RESET}")
                
                # Send initial presence payload
                await websocket.send(json.dumps({"type": "init", "os": os_sys}))
                
                async for message in websocket:
                    data = json.loads(message)
                    if data.get("type") == "tool_call":
                        call_id = data.get("call_id")
                        tool_name = data.get("tool_name")
                        args = data.get("args", {})
                        
                        UI.executing(tool_name, args)
                        
                        status = "success"
                        
                        if tool_name in terminal_tool_map:
                            tool_func = terminal_tool_map[tool_name]
                            try:
                                res = tool_func(**args)
                                status = res.get("status", "success") if isinstance(res, dict) else "success"
                            except Exception as e:
                                res = {"status": "error", "output": f"Terminal tool error: {e}"}
                                status = "error"
                        
                        elif hasattr(tools_module, tool_name):
                            tool_func = getattr(tools_module, tool_name)
                            try:
                                res = tool_func(**args)
                                status = res.get("status", "success") if isinstance(res, dict) else "success"
                            except Exception as e:
                                res = {"status": "error", "output": f"Exception running {tool_name}: {str(e)}"}
                                status = "error"
                        
                        else:
                            res = {"status": "error", "output": f"Tool '{tool_name}' is not available on this OS ({os_sys})."}
                            status = "error"
                        
                        UI.result_status(status, res)
                            
                        response = {
                            "type": "tool_result",
                            "call_id": call_id,
                            "result": json.dumps(res)
                        }
                        await websocket.send(json.dumps(response))
                        
                    elif data.get("type") == "terminal_stream":
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
                                
        except websockets.exceptions.InvalidURI:
            UI.error(f"Invalid Connection URI: {ws_url}")
            break
        except websockets.exceptions.ConnectionClosed:
            UI.warning("Connection severed by gateway. Attempting reconnect...")
        except Exception as e:
            err_msg = str(e)
            UI.warning(f"Connection failed: {err_msg}")
            if "SSL" in err_msg or "certificate verify failed" in err_msg:
                UI.error("Mac SSL Certificate Error detected!")
                UI.info("Run: /Applications/Python\\ 3.x/Install\\ Certificates.command")
            UI.info("Retrying in 5 seconds...")
            await asyncio.sleep(5)


def main():
    print(f"\n{UI.CYAN}{UI.BOLD}")
    print("      ███▄    █  ▒█████   ██▀███   ▄▄▄      ")
    print("      ██ ▀█   █ ▒██▒  ██▒▓██ ▒ ██▒▒████▄    ")
    print("     ▓██  ▀█ ██▒▒██░  ██▒▓██ ░▄█ ▒▒██  ▀█▄  ")
    print("     ▓██▒  ▐▌██▒▒██   ██░▒██▀▀█▄  ░██▄▄▄▄██ ")
    print("     ▒██░   ▓██░░ ████▓▒░░██▓ ▒██▒ ▓█   ▓██▒")
    print("     ░ ▒░   ▒ ▒ ░ ▒░▒░▒░ ░ ▒▓ ░▒▓░ ▒▒   ▓▒█░")
    print("     ░ ░░   ░ ▒░  ░ ▒ ▒░   ░▒ ░ ▒░  ▒   ▒▒ ░")
    print(f"        ░   ░ ░ ░ ░ ░ ▒    ░░   ░   ░   ▒   ")
    print(f"              ░     ░ ░     ░           ░  {UI.RESET}")
    print(f"\n     {UI.BOLD}NORA PERSONAL ASSISTANT — HOST DAEMON{UI.RESET}")
    print(f"     {UI.DIM}Bridging Nora's Intelligence to your Local System{UI.RESET}\n")
    print("  [✓] Autonomous Engine: Loaded")
    print("  [✓] Resource Control: Granted")
    print("  [✓] System Permissions: Active\n")
    
    session_id = input(f" {UI.YELLOW}►{UI.RESET} {UI.BOLD}Enter Session ID:{UI.RESET} ").strip()
    if not session_id:
        UI.error("Session ID required for secure pairing. Exiting.")
        return

    default_url = "ws://localhost:8000"
    url = input(f" {UI.YELLOW}►{UI.RESET} {UI.BOLD}Enter Backend URL{UI.RESET} {UI.DIM}(default {default_url}):{UI.RESET} ").strip()
    if not url:
        url = default_url
    
    if url.startswith("https://"):
        url = url.replace("https://", "wss://", 1)
    elif url.startswith("http://"):
        url = url.replace("http://", "ws://", 1)
    url = url.rstrip("/")

    try:
        asyncio.run(daemon_loop(url, session_id))
    except KeyboardInterrupt:
        print()
        UI.warning("Daemon terminated by user.")
    finally:
        sys.exit(0)

if __name__ == "__main__":
    # Fix for Windows ANSI colors
    if platform.system() == "Windows":
        import os
        os.system("color") 
    main()

