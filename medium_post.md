# Beyond Chatbots: How I Built Nora, an Autonomous AI Companion with Google Gemini and ADK

*This article was created for the purposes of entering the Google Live Agent Hackathon. #GeminiLiveAgentChallenge*

---

For years, we’ve interacted with AI through a "text box paradigm." You type something, the AI thinks, and it types back. It’s effective, but it’s limited. It’s a brain without hands, a ghost in a digital cage. 

When the **Google Live Agent Hackathon** was announced, I saw an opportunity to break that cage. I wanted to build something that didn't just advise, but **acted**. 

Introducing **Nora**: an autonomous AI companion that sees, hears, speaks, and directly controls your computer to turn conversation into real-world action.

## The Inspiration: Why "Live" Agents Matter
Automation used to be the domain of rigid, predefined scripts. If a task wasn't explicitly programmed, the computer couldn't do it. But Large Language Models (LLMs) have changed the math. They can reason. 

My goal with Nora was to leverage this reasoning power to automate the "boring stuff"—organizing a messy desktop, writing and testing code, or fixing system issues—all through a natural, human-like interface. I wanted to move away from the keyboard and move toward **Voice, Vision, and Agency.**

## The Architecture: A Hybrid Cloud-Local Topology
Building a truly "live" agent requires more than just a fast model; it requires a specialized architecture. Nora’s design is a **bidirectional-streaming, hybrid system** that bridges Google’s cloud-scale intelligence with the user’s local hardware.

### 1. The Brain: Google Gemini 2.0 Flash & ADK
Nora’s reasoning is powered by **Gemini 2.0 Flash** via the **Google Agentic Development Kit (ADK)**. We used the ADK’s built-in **Bidi-streaming** capabilities to handle real-time audio and vision. 

Unlike traditional request/response APIs, Bidi-streaming allows for:
- **Sub-second Latency:** Audio and vision data flow continuously, making conversation feel fluid.
- **Graceful Interruption:** One of the hardest parts of voice AI is knowing when to stop talking. Using the ADK event chain, Nora can detect when a user starts speaking and instantly clear her audio buffers to listen.

### 2. The Nervous System: FastAPI & WebSockets
The backend acts as a high-speed orchestrator. It receives raw 16kHz PCM audio from the frontend, manages session persistence (so Nora remembers who you are even if you refresh), and routes tool-call requests to the local machine.

### 3. The Hands: The Nora Daemon
To give Nora "hands," I built a custom **Python Daemon**. This is a lightweight client that runs on the user's macOS or Windows machine. When Nora decides to take an action—like `create_project` or `organize_desktop`—the server sends a WebSocket request to this daemon, which executes whitelisted terminal commands in a **persistent, stateful shell**.

![Nora Architecture](https://raw.githubusercontent.com/Abdulnasserh/Google_Hackathon/main/README_assets/architecture_diagram.png)

## What Nora Can Do
- **Autonomous Technical Support:** Ask Nora why your sound isn't working or why your computer is slow. She will run diagnostic commands, interpret the real-time logs, and apply fixes autonomously.
- **Multimodal Coding:** You can share your screen and literally point to a bug. Nora "sees" the error through Gemini’s vision capabilities and "fixes" it by writing directly to your local file system.
- **System Organization:** Tell Nora "my desktop is a mess," and she will categorize your files into logical folders (images, documents, screenshots) using her filesystem tools.

## Challenges & Breakthroughs
The biggest hurdle was the **"Linking Problem."** Managing a live WebSocket connection between a cloud-hosted agent (running on Google Cloud) and a local device behind a firewalled network is complex. 

By implementing a robust **Session ID persistence system** and optimizing the **Google Cloud Run** instance settings to handle stateful WebSocket traffic, I was able to achieve a stable connection that stays "paired" regardless of browser state.

## What I Learned
Building Nora taught me that the future of AI isn't in better chatbots—it's in **Agency**. By combining the multimodal power of **Gemini 2.0** with the structured execution of the **Google ADK**, we can finally build software that understands our intent and has the power to carry it out.

Nora is just the beginning. The goal is to move toward a world where your voice is the only interface you need to master your digital world.

---

### **Tech Stack Summary**
- **AI Framework:** Google ADK (Agent Development Kit)
- **Model:** Gemini 2.0 Flash (Bidi-streaming API)
- **Cloud Infrastructure:** Google Cloud Run, Vertex AI
- **Backend:** Python, FastAPI, WebSockets
- **Frontend:** React 19, Vite, TypeScript

#GeminiLiveAgentChallenge
