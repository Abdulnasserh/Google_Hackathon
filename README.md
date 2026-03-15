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
| 🛠️ **Act (Live Command Engine)** | Nora uses a **persistent, stateful command shell** living on the user's host machine. Instead of relying purely on hardcoded scripts, she synthesizes and streams raw bash/PowerShell commands in real-time, allowing her to solve *any* problem interactively. |
| 🛑 **Graceful Interruption** | A core hackathon requirement: users can interrupt the agent mid-sentence simply by speaking over it or clicking the mic. The system instantly clears audio buffers and coordinates backend cancellation events to handle the interruption smoothly. |

---

---

## 🏗️ Architecture & System Design

Nora leverages a **hybrid cloud-local architecture**. The intelligence resides in **Google Cloud (Vertex AI)**, while the execution happens locally through a secure **Client Daemon**.

![Nora Architecture Diagram](README_assets/architecture_diagram.png)

### 1. Persistent Autonomous Execution (The "Live Command Engine")
The crown jewel of Nora is her **Agentic execution architecture**. We moved beyond simple hardcoded diagnostic scripts. The AI is essentially a "ghost in the machine":
- **Stateful Terminals:** The client daemon spawns a real, persistent `powershell.exe` or `/bin/bash` session. Directory changes (`cd`) and variables carry over between commands.
- **Interactive Prompts:** If a process asks *"Are you sure? [y/N]"*, the backend does not hang. Nora reads the standard output stream, generates the answer `"y"`, and pushes it to standard input dynamically.
- **Unrestricted Problem Solving:** Because she can synthesize raw shell commands, she can fix issues the developers never explicitly anticipated.
- **Desktop Organization:** Nora can now "See" a messy desktop and autonomously arrange it into categorized folders (Screenshots, Images, Documents) using her newly added filesystem tools.
- **Safety First:** The daemon implements a rigorous blocklist preventing destructive patterns (`rm -rf /`, `format`, password scraping).

### 2. Cinematic UX & Real-Time Feedback
We've broken the "textbox paradigm". When the user asks Nora to fix their Bluetooth:
- They don't just get a text reply saying "I fixed it."
- A **Live Activity** dashboard slides in, showing a cinematic stream of the exact CLI commands Nora is executing on their machine (`> launchctl kickstart -k system/com.apple.bluetoothd`).
- **OS-Aware Onboarding:** The frontend detects the user's OS and provides tailored, one-click download links for the **Nora Daemon (.zip)** directly from the cloud backend.

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
