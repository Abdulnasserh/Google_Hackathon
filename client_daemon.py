import asyncio
import json
import websockets
import platform
import logging

from bidi_streaming_agent.tools import mac_tools, windows_tools

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("NoraDaemon")

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

    async for websocket in websockets.connect(ws_url):
        logger.info("Connected to Cloud Backend! Waiting for remote diagnostic commands...")
        try:
            # Send initial presence payload
            await websocket.send(json.dumps({"type": "init", "os": os_sys}))
            
            async for message in websocket:
                data = json.loads(message)
                if data.get("type") == "tool_call":
                    call_id = data.get("call_id")
                    tool_name = data.get("tool_name")
                    args = data.get("args", {})
                    
                    logger.info(f"Executing tool request: {tool_name} with args: {args}")
                    
                    if hasattr(tools_module, tool_name):
                        tool_func = getattr(tools_module, tool_name)
                        try:
                            # Tools are synchronous in our modules
                            result = tool_func(**args)
                        except Exception as e:
                            result = {"status": "error", "output": f"Exception running {tool_name}: {str(e)}"}
                    else:
                        result = {"status": "error", "output": f"Tool {tool_name} is not available on this OS ({os_sys})."}
                    
                    response = {
                        "type": "tool_result",
                        "call_id": call_id,
                        "result": json.dumps(result)
                    }
                    await websocket.send(json.dumps(response))
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection closed. Reconnecting in 3 seconds...")
            await asyncio.sleep(3)
            continue
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await asyncio.sleep(3)

def main():
    print("===========================================")
    print(" Nora AI Technician — Secure Client Daemon ")
    print("===========================================")
    print("This daemon allows the Cloud AI Agent to run")
    print("safe, read-only diagnostic tools on your PC.")
    print("===========================================\n")
    
    session_id = input("Enter the 8-character Session ID from the Web UI: ").strip()
    if not session_id:
        print("Session ID is required. Exiting.")
        return

    # For local testing, default to localhost. In prod, this would be hardcoded to the Cloud Run URL.
    default_url = "ws://localhost:8000"
    url = input(f"Enter backend URL (default {default_url}): ").strip()
    if not url:
        url = default_url

    try:
        asyncio.run(daemon_loop(url, session_id))
    except KeyboardInterrupt:
        print("\nDaemon stopped by user.")

if __name__ == "__main__":
    main()
