"""
Nora Personal Assistant — FastAPI WebSocket Server
=================================================
This module implements the backend server for Nora, an autonomous AI Personal Assistant.
It uses FastAPI with WebSocket support for real-time bidirectional communication.

Architecture Overview:
    ┌─────────────┐     WebSocket      ┌──────────────────┐     Live API     ┌─────────────┐
    │   React UI  │ ◄──────────────► │  FastAPI Server  │ ◄──────────────► │ Gemini Model │
    │  (Frontend) │   text + audio    │  (This Module)   │   ADK Pipeline   │  (Google AI) │
    └─────────────┘                    └──────────────────┘                   └─────────────┘

Lifecycle Phases (per ADK Bidi-streaming):
    Phase 1: Application Initialization (once at startup)
        - Create Agent, SessionService, Runner
    Phase 2: Session Initialization (per user connection)
        - Get/Create Session, RunConfig, LiveRequestQueue
    Phase 3: Bidi-streaming (active communication)
        - Upstream: User → LiveRequestQueue → Agent → Gemini
        - Downstream: Gemini → Agent → Events → WebSocket → User
    Phase 4: Termination (on disconnect)
        - Close LiveRequestQueue, cleanup resources
"""

import asyncio
import base64
import json
import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables BEFORE importing the agent module
# (Agent reads env vars at import time for model selection)
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import our PC Technician agent base config
from bidi_streaming_agent.agent import root_agent
import inspect
from bidi_streaming_agent.tools.mac_tools import ALL_MAC_TOOLS
from bidi_streaming_agent.tools.windows_tools import ALL_WINDOWS_TOOLS
from bidi_streaming_agent.tools.terminal_session import ALL_TERMINAL_TOOLS

connected_daemons: dict[str, WebSocket] = {}
daemon_responses: dict[str, asyncio.Future] = {}
daemon_listeners: dict[str, list[WebSocket]] = {}

async def notify_daemon_status(session_id: str, status: str):
    """Notifies all browser listeners for a session that the daemon status has changed."""
    if session_id in daemon_listeners:
        msg = json.dumps({"type": "daemon_status", "status": status})
        disconnected = []
        for ws in daemon_listeners[session_id]:
            try:
                await ws.send_text(msg)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            daemon_listeners[session_id].remove(ws)

def build_remote_tools_for_session(session_id: str):
    unique_tool_names = set()
    all_tools = []
    # Collect all unique tools across Mac, Windows, and Terminal Session
    for t in ALL_MAC_TOOLS + ALL_WINDOWS_TOOLS + ALL_TERMINAL_TOOLS:
        if t.__name__ not in unique_tool_names:
            unique_tool_names.add(t.__name__)
            all_tools.append(t)
            
    remote_tools = []
    for tool in all_tools:
        sig = inspect.signature(tool)
        name = tool.__name__
        doc = tool.__doc__
        
        async def remote_wrapper(_name=name, **kwargs):
            if session_id not in connected_daemons:
                return (
                    f"Error: Your Nora Daemon is not connected for session {session_id}. "
                    "You MUST tell the user to download the Nora Daemon executable from the links "
                    f"on the Welcome Screen. Tell them to run it, and when asked, paste their Daemon ID: {session_id}. "
                    "You cannot control their PC until they do this."
                )
            
            call_id = str(uuid.uuid4())
            future = asyncio.get_running_loop().create_future()
            daemon_responses[call_id] = future
            
            ws = connected_daemons[session_id]
            req = {"type": "tool_call", "call_id": call_id, "tool_name": _name, "args": kwargs}
            try:
                await ws.send_text(json.dumps(req))
                result = await asyncio.wait_for(future, timeout=60.0)
                return result
            except asyncio.TimeoutError:
                return "Error: Tool execution timed out on the client daemon."
            except Exception as e:
                return f"Error communicating with local daemon: {e}"
            finally:
                daemon_responses.pop(call_id, None)

        remote_wrapper.__name__ = name
        remote_wrapper.__doc__ = doc
        remote_wrapper.__signature__ = sig
        remote_tools.append(remote_wrapper)
        
    from google.adk.tools import google_search
    return [google_search] + remote_tools

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================================================================
# Phase 1: Application Initialization (once at startup)
# =========================================================================

APP_NAME = "nora-personal-assistant"

app = FastAPI(
    title="Nora Personal Assistant",
    description="Real-time autonomous AI Personal Assistant that can See, Hear, Speak, and Act",
    version="1.0.0",
)

# CORS — allow the Vite dev server to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session service — stores conversation history (in-memory for dev)
session_service = InMemorySessionService()

# Runner — orchestrates agent execution
runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service,
)


# =========================================================================
# Health Check Endpoint
# =========================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "agent": root_agent.name,
        "model": root_agent.model,
    }

# =========================================================================
# Daemon WebSocket Endpoint (For Client CLI Tools)
# =========================================================================

@app.websocket("/ws/daemon/{session_id}")
async def daemon_websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info(f"[DAEMON] Connected for session: {session_id}")
    connected_daemons[session_id] = websocket
    
    # Notify any browser listeners that a daemon just connected
    await notify_daemon_status(session_id, "connected")
    
    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "init":
                os_sys = data.get("os", "Unknown")
                logger.info(f"[DAEMON] Session {session_id} initialized. OS: {os_sys}")
            elif msg_type == "tool_result":
                call_id = data.get("call_id")
                result_str = data.get("result", "No output")
                future = daemon_responses.get(call_id)
                if future and not future.done():
                    future.set_result(result_str)
                    
    except WebSocketDisconnect:
        logger.info(f"[DAEMON] Disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"[DAEMON] Error: {e}")
    finally:
        connected_daemons.pop(session_id, None)
        # Notify any browser listeners that the daemon disconnected
        await notify_daemon_status(session_id, "disconnected")

@app.websocket("/ws/status/{session_id}")
async def status_websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    if session_id not in daemon_listeners:
        daemon_listeners[session_id] = []
    daemon_listeners[session_id].append(websocket)
    
    # Send initial status
    initial_status = "connected" if session_id in connected_daemons else "disconnected"
    await websocket.send_text(json.dumps({"type": "daemon_status", "status": initial_status}))
    
    try:
        while True:
            await websocket.receive_text() # Keep alive
    except WebSocketDisconnect:
        pass
    finally:
        if session_id in daemon_listeners:
            daemon_listeners[session_id].remove(websocket)


# =========================================================================
# WebSocket Endpoint — Bidi-streaming
# =========================================================================

@app.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    session_id: str,
) -> None:
    """
    WebSocket endpoint for bidirectional streaming with the AI agent.

    Message Protocol (Client → Server):
        Text messages (JSON):
            {"type": "text", "text": "My computer is slow"}
            {"type": "image", "data": "<base64>", "mimeType": "image/jpeg"}
        Binary messages:
            Raw PCM audio bytes (16-bit, 16kHz, mono)

    Events (Server → Client):
        ADK Event objects serialized as JSON, containing:
            - content.parts[].text           → Text responses
            - content.parts[].inline_data    → Audio response chunks
            - input_transcription            → User's speech-to-text
            - output_transcription           → Agent's speech-to-text
            - turn_complete                  → Agent finished responding
            - interrupted                    → User interrupted agent
    """
    await websocket.accept()
    logger.info(f"[WS] Client connected: user={user_id}, session={session_id}")

    # =====================================================================
    # Phase 2: Session Initialization
    # =====================================================================

    # Configure streaming behavior
    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        session_resumption=types.SessionResumptionConfig(),
    )

    # Get or create ADK session (handles both new and returning users)
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    if not session:
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        logger.info(f"[SESSION] Created new session: {session_id}")
    else:
        logger.info(f"[SESSION] Resuming existing session: {session_id}")

    # Create a fresh LiveRequestQueue for this session
    live_request_queue = LiveRequestQueue()

    # Shared cancellation event — when either side fails, the other stops
    cancel_event = asyncio.Event()

    # =====================================================================
    # Phase 3: Bidi-streaming (concurrent upstream + downstream)
    # =====================================================================

    async def upstream_task() -> None:
        """
        Receives messages from the WebSocket client and forwards them
        to the ADK LiveRequestQueue for processing by the agent.

        Handles three message types:
            1. Text messages → send_content()
            2. Audio binary frames → send_realtime()
            3. Image messages → send_realtime()
        """
        try:
            while not cancel_event.is_set():
                try:
                    message = await websocket.receive()
                except WebSocketDisconnect:
                    logger.info("[WS] Client disconnected (upstream)")
                    break

                if message.get("type") == "websocket.disconnect":
                    logger.info("[WS] Client sent disconnect frame")
                    break

                if message.get("type") == "websocket.receive":
                    # --- Binary data: raw audio PCM ---
                    if "bytes" in message and message["bytes"]:
                        audio_data = message["bytes"]
                        audio_blob = types.Blob(
                            mime_type="audio/pcm;rate=16000",
                            data=audio_data,
                        )
                        live_request_queue.send_realtime(audio_blob)

                    # --- Text data: JSON messages ---
                    elif "text" in message and message["text"]:
                        try:
                            json_message = json.loads(message["text"])
                            msg_type = json_message.get("type", "text")

                            if msg_type == "text":
                                # User typed a text message
                                text = json_message.get("text", "")
                                if text.strip():
                                    content = types.Content(
                                        parts=[types.Part(text=text)]
                                    )
                                    live_request_queue.send_content(content)
                                    logger.info(
                                        f"[UPSTREAM] Text: {text[:80]}..."
                                    )

                            elif msg_type == "image":
                                # User sent an image (base64 JPEG)
                                image_data = base64.b64decode(
                                    json_message["data"]
                                )
                                mime_type = json_message.get(
                                    "mimeType", "image/jpeg"
                                )
                                image_blob = types.Blob(
                                    mime_type=mime_type,
                                    data=image_data,
                                )
                                live_request_queue.send_realtime(image_blob)
                                logger.info("[UPSTREAM] Image received")

                            elif msg_type == "interrupt":
                                # User explicitly clicked the UI to mute the agent mid-sentence.
                                # Send a turn_complete signal to explicitly tell Gemini to stop generating
                                try:
                                    logger.info("[UPSTREAM] UI Interrupt Signal Received")
                                    # Create client content mapping matching the underlying ADK requirements
                                    live_request_queue.send(
                                        {"client_content": {"turn_complete": True}}
                                    )
                                except Exception as ei:
                                    logger.warning(f"Could not forward interrupt: {ei}")

                        except json.JSONDecodeError:
                            # Treat as plain text if not valid JSON
                            content = types.Content(
                                parts=[types.Part(text=message["text"])]
                            )
                            live_request_queue.send_content(content)

        except Exception as e:
            logger.error(f"[UPSTREAM] Error: {e}")
        finally:
            # Signal the downstream task to stop
            cancel_event.set()
            logger.info("[UPSTREAM] Task ended")

    async def downstream_task() -> None:
        """
        Receives Event objects from the ADK runner's run_live() async
        generator and forwards them to the WebSocket client as JSON.

        Event types handled:
            - Text content events
            - Audio inline_data events
            - Transcription events (input/output)
            - Tool call events
            - Turn complete / interrupted signals
            - Error events
        """
        try:
            # Create session agent and runner
            session_agent = Agent(
                model=root_agent.model,
                name=root_agent.name,
                instruction=root_agent.instruction,
                tools=build_remote_tools_for_session(session_id),
            )
            session_runner = Runner(
                app_name=APP_NAME,
                agent=session_agent,
                session_service=session_service,
            )

            async for event in session_runner.run_live(
                user_id=user_id,
                session_id=session_id,
                live_request_queue=live_request_queue,
                run_config=run_config,
            ):
                if cancel_event.is_set():
                    logger.info("[DOWNSTREAM] Cancel event received, stopping")
                    break

                try:
                    # Serialize event to JSON and send to client
                    event_json = event.model_dump_json(
                        exclude_none=True, by_alias=True
                    )
                    await websocket.send_text(event_json)
                except (WebSocketDisconnect, RuntimeError) as send_err:
                    # Client already disconnected — can't send, so stop
                    logger.info(
                        f"[DOWNSTREAM] Client gone during send: {send_err}"
                    )
                    break

                # Log key events for debugging
                if event.turn_complete:
                    logger.info("[DOWNSTREAM] Turn complete")
                if event.interrupted:
                    logger.info("[DOWNSTREAM] Interrupted by user")
                if event.error_code:
                    logger.error(
                        f"[DOWNSTREAM] Error: {event.error_code} - "
                        f"{event.error_message}"
                    )

        except WebSocketDisconnect:
            logger.info("[WS] Client disconnected (downstream)")
        except Exception as e:
            logger.error(f"[DOWNSTREAM] Error: {e}")
        finally:
            # Signal the upstream task to stop
            cancel_event.set()
            logger.info("[DOWNSTREAM] Task ended")

    # Run upstream and downstream concurrently
    try:
        await asyncio.gather(
            upstream_task(),
            downstream_task(),
            return_exceptions=True,
        )
    finally:
        # =================================================================
        # Phase 4: Termination — clean up resources
        # =================================================================
        cancel_event.set()  # Ensure both tasks know to stop
        live_request_queue.close()
        logger.info(f"[WS] Session closed: user={user_id}, session={session_id}")


# =========================================================================
# Static Frontend Serving
# =========================================================================

# Path to the built frontend (dist/)
frontend_path = Path(__file__).parent.parent / "dist"

# If the dist folder exists, mount it to serve static files
if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=frontend_path / "assets"), name="assets")

# Serve Daemon binaries
daemons_path = Path(__file__).parent.parent / "daemons"
if daemons_path.exists():
    app.mount("/daemons", StaticFiles(directory=daemons_path), name="daemons")

if frontend_path.exists():
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Prevent intercepting the WebSocket or Health check paths
        if full_path.startswith("ws/") or full_path == "health" or full_path.startswith("daemons/"):
            return None # FastAPI will continue to search routing table
        
        # Check if the requested file exists (e.g. logo.png, robots.txt)
        file_path = frontend_path / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        
        # Otherwise, serve index.html (SPA Fallback)
        return FileResponse(frontend_path / "index.html")
else:
    logger.warning("Frontend 'dist' directory not found. Static files will not be served.")


# =========================================================================
# Entry Point
# =========================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
