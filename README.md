# Nora — AI Live Technician

> 🏆 **Google Live Agent Hackathon Submission**
> **Category:** Live Agents 🗣️
> An advanced multimodal AI technician that can **See, Hear, Speak, and Act** to help users troubleshoot PC issues in real-time with graceful interruption capabilities.

## 🚀 Overview

Nora is not just a chatbot; it's a Live Technician. Built using the **Google ADK (Agent Development Kit)** and the **Gemini Live API**, Nora allows users to:
- Talk naturally about their computer problems via real-time bidirectional audio.
- Share their screen or upload error screenshots.
- Grant the AI access to run safe, whitelisted **CLI diagnostic commands** directly on their machine.

The agent automatically detects whether the user is running **macOS** or **Windows** and seamlessly loads a tailored suite of troubleshooting tools (ping, DNS checks, system info, disk health, etc.) to diagnose issues without asking manual questions.

---

## ✨ Key Features

| Capability | How It Works |
|:---:|---|
| 👂 **Hear** | Real-time voice streaming at 16kHz PCM. The user can speak naturally, and the agent listens continuously. |
| 🗣️ **Speak** | The agent responds with natural, sub-second latency voice (24kHz PCM) powered by Gemini 2.5 Flash Native Audio. |
| 👁️ **See** | Users can share their screen, drag-and-drop images, or upload screenshots. The agent reads error codes, BSOD screens, and UI elements to provide visual context. |
| 🛠️ **Act (CLI Tools)** | The backend auto-detects the host OS and equips the agent with up to 20 OS-specific CLI tools (e.g., `ipconfig`, `system_profiler`, `sfc /scannow`). The agent runs these proactively to gather system data. |
| 🛑 **Graceful Interruption** | A core hackathon requirement: users can interrupt the agent mid-sentence simply by speaking over it or clicking the mic. The system instantly clears audio buffers and coordinates backend cancellation events to handle the interruption smoothly. |

---

## 🏗️ Architecture & System Design

The application consists of a **React frontend**, a **FastAPI WebSocket backend**, and the **Google ADK** routing to the Gemini model.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND                                        │
│                   React + Vite + Shadcn/UI                               │
│                                                                          │
│  ┌──────────────┐  ┌────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ ChatInterface│  │VoiceButton │  │Activity Log  │  │Image Upload  │  │
│  │ Messages,    │  │ Mic toggle │  │ Live MCP     │  │ File picker, │  │
│  │ text input   │  │ with pulse │  │ tracking UI  │  │ screen cap   │  │
│  └──────┬───────┘  └─────┬──────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                │                 │                  │          │
│         └────────────────┼─────────────────┼──────────────────┘          │
│                          │                 │                             │
│                ┌─────────▼─────────────────▼──┐                          │
│                │     useWebSocket Hook         │                         │
│                │  • Connects to WS server      │                         │
│                │  • Sends text/audio/images    │                         │
│                │  • Parses ADK response events │                         │
│                │  • Plays audio                │                         │
│                └─────────────┬─────────────────┘                         │
└──────────────────────────────┼───────────────────────────────────────────┘
                               │
                        WebSocket Connection
                        ws://localhost:8000/ws/{session}
                        ├─ Upstream: JSON/PCM text/audio/images
                        └─ Downstream: ADK Event objects (JSON)
                               │
┌──────────────────────────────┼───────────────────────────────────────────┐
│                          BACKEND                                         │
│                   FastAPI + Google ADK                                   │
│                                                                          │
│  ┌───────────────────────────▼────────────┐                              │
│  │              WebSocket Server             │                           │
│  │              (app/main.py)                │                           │
│  └─────────────────────┬───────────────────┘                             │
│                        │                                                 │
│  ┌─────────────────────┴───────────────────┐                             │
│  │            ADK Runner.run_live()           │                          │
│  │         • Routes multimodal input          │                          │
│  │         • Yields response events           │                          │
│  └─────────────────────┬───────────────────┘                             │
│                        │                                                 │
│  ┌─────────────────────▼─────────────────────────────────────────────┐   │
│  │                      Root Agent (Nora)                             │   │
│  │           Acts as universal MCP Tool Client                        │   │
│  └─────────────────────┬─────────────────┬───────────┬───────────────┘   │
│                        │                 │           │                   │
│               MCP      │        MCP      │     MCP   │                   │
│               Protocol │        Protocol │     Proto │                   │
│  ┌─────────────────────▼──┐ ┌────────────▼───┐ ┌─────▼──────────────┐    │
│  │    MacTechnicianMCP    │ │WindowsTechMCP  │ │  Android Node      │    │
│  │    (FastMCP Server)    │ │(FastMCP Server)│ │  (Soon)            │    │
│  │    - ping, dns         │ │- sfc, ipconfig │ │  - battery, sms    │    │
│  │    - flush_dns         │ │- event_logs    │ │  - camera.snap     │    │
│  └────────────────────────┘ └────────────────┘ └────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1. Modular MCP Architecture
To support real-time bidi streaming while granting secure, modular system access, the agent's architecture uses the **Model Context Protocol (MCP)**:

1. **OS Detection:** The FastAPI server uses `platform.system()` to detect the host environment.
2. **MCP Server Spawning:** The agent dynamically identifies the correct OS-specific FastMCP server (e.g., `mac_mcp_server.py`).
3. **Dynamic Bridge:** Using the `MCP Client Bridge`, Nora spawns the server as a background subprocess and dynamically fetches tools over the **stdio** protocol. This makes the agent completely modular — adding support for a new platform like Linux or Android is as simple as creating a new MCP server without touching the core agent logic.
4. **Prompt Adjustments:** The detected OS and tool capabilities are injected directly into the Gemini instruction prompt.

### 2. WebSocket & Interruption Flow
Graceful interruptions require precise coordination across the full stack:
- **Frontend (`useWebSocket.ts`):** Wraps Web Audio API playback. When the user speaks, it triggers `interruptAgent()`, which instantly clears the audio buffer, drops partial messages, and sends an interruption signal.
- **Backend (`main.py`):** Uses an `asyncio.Event` (`cancel_event`) shared between the upstream (receive) and downstream (send) tasks. If the client disconnects or interrupts, tasks are cleanly cancelled without hanging the server or queue.
- **Auto-Reconnect:** Features exponential backoff for unexpected network drops, ensuring a resilient live session.

---

## 📂 Project Structure

```
Google_Hackathon/
├── .env                        # API key + model config
├── requirements.txt            # Python dependencies
│
├── bidi_streaming_agent/       # Google ADK Agent Code
│   ├── agent.py                # Root agent: Persona, MCP Client loading
│   ├── mcp_client_bridge.py    # Bridge: Spawns MCP server & dynamically wraps tools
│   ├── mcp_servers/            # Standalone FastMCP servers
│   │   ├── mac_mcp_server.py   # macOS FastMCP entry point
│   │   └── windows_mcp_server.py # Windows FastMCP entry point
│   └── tools/                  # Underlying CLI implementation logic
│       ├── mac_tools.py        # 17 safe CLI tools for macOS (with output truncation)
│       └── windows_tools.py    # 20 safe CLI tools for Windows (with output truncation)
│
├── app/
│   └── main.py                 # FastAPI WebSocket server (session & interrupt mgmt)
│
└── frontend/                   # React app (Vite + TypeScript)
    └── src/
        ├── hooks/
        │   ├── useWebSocket.ts      # WS lifecycle, streaming, interruption handling
        │   └── useAudioRecorder.ts  # Mic capture via AudioWorklet (16kHz PCM)
        └── components/
            ├── ChatInterface.tsx    # Main UI (Messages, Mic toggle, Screen Share)
            └── ui/                  # Shadcn UI primitives
```

---

## 🛠️ Spin-Up Instructions (For Judges)

The project requires a local environment to allow the agent access to CLI diagnostic tools.

### Prerequisites
- Python 3.10+
- Node.js & `pnpm`
- A Gemini API Key

### 1. Backend Setup
1. Clone the repository and navigate to the root directory.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your `.env` file in the root directory:
   ```env
   GEMINI_API_KEY="your_api_key_here"
   DEMO_AGENT_MODEL="gemini-2.5-flash-native-audio-preview-12-2025"
   ```
5. Start the FastAPI server:
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### 2. Frontend Setup
1. Open a second terminal and navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   pnpm install
   ```
3. Start the Vite development server:
   ```bash
   pnpm run dev
   ```
4. Open your browser to `http://localhost:5173`. Click the microphone icon to connect to the Live API and start talking!

---

## ☁️ Google Cloud Deployment Notes

While this specific application is designed to run locally to allow the AI access to the user's *local* CLI tools for PC troubleshooting, the backend infrastructure itself leverages Google Cloud.

**How it uses Google Cloud:**
- **Google ADK & Vertex AI/Gemini API:** The core intelligence and multimodal live streaming are powered completely by Google's cloud infrastructure via the Gemini Live API endpoint.
- **Production Deployment Strategy:** In a production scenario, the FastAPI backend acts as a signaling server and can be deployed via **Google Cloud Run** using a Dockerfile. The local CLI tools would be packaged into a lightweight, downloadable client daemon (e.g., using PyInstaller) that connects via WebSocket to the Cloud Run backend, maintaining strict security and isolation.

---

## ⚙️ Tech Stack

- **Agent Framework:** Google ADK (Agent Development Kit)
- **AI Model:** Gemini 2.5 Flash Native Audio (bidi streaming API)
- **Backend:** Python, FastAPI, Uvicorn, WebSockets, `asyncio`
- **Frontend:** React 19, Vite, TypeScript, Tailwind CSS v4, Shadcn/UI
- **Browser APIs:** Web Audio API, AudioWorklet (raw PCM conversion), Screen Capture API
