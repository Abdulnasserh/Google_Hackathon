/**
 * useWebSocket Hook — WebSocket Connection Management
 * =====================================================
 * Manages the WebSocket connection to the FastAPI backend for
 * bidirectional streaming with the ADK agent.
 *
 * Architecture Role:
 *   React UI ←→ [useWebSocket] ←→ FastAPI WebSocket ←→ ADK ←→ Gemini
 *
 * Message Protocol:
 *   Upstream (client → server):
 *     - JSON text: { type: "text", text: "..." }
 *     - JSON image: { type: "image", data: "<base64>", mimeType: "image/jpeg" }
 *     - Binary: raw PCM audio bytes
 *   Downstream (server → client):
 *     - ADK Event JSON objects
 *
 * Interruption Handling:
 *   - User can interrupt the agent mid-speech
 *   - Audio buffer is cleared immediately for instant silence
 *   - Partial assistant messages are finalized with [interrupted] marker
 *   - Auto-reconnect with exponential backoff on unexpected disconnects
 */

import { useState, useCallback, useRef, useEffect } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    timestamp: Date;
    isPartial?: boolean;
    isTranscription?: boolean;
    imageUrl?: string;
}

export type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";

export interface AgentEvent {
    content?: {
        parts?: Array<{
            text?: string;
            inlineData?: { data: string; mimeType: string };
            functionCall?: { name: string; args: Record<string, unknown> };
        }>;
        role?: string;
    };
    partial?: boolean;
    turnComplete?: boolean;
    interrupted?: boolean;
    inputTranscription?: { text: string; finished: boolean };
    outputTranscription?: { text: string; finished: boolean };
    usageMetadata?: {
        promptTokenCount?: number;
        candidatesTokenCount?: number;
        totalTokenCount?: number;
    };
    errorCode?: string;
    errorMessage?: string;
    author?: string;
}

export interface ToolCallActivity {
    id: string;
    name: string;
    timestamp: Date;
    status: 'executing' | 'completed';
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useWebSocket() {
    const [status, setStatus] = useState<ConnectionStatus>("disconnected");
    const [messages, setMessages] = useState<Message[]>([]);
    const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
    const [currentTranscription, setCurrentTranscription] = useState("");
    const [activities, setActivities] = useState<ToolCallActivity[]>([]);

    const wsRef = useRef<WebSocket | null>(null);
    const partialTextRef = useRef("");
    const userIdRef = useRef(`user-${crypto.randomUUID().slice(0, 8)}`);
    const sessionIdRef = useRef(`session-${crypto.randomUUID().slice(0, 8)}`);

    const [isScreenSharing, setIsScreenSharing] = useState(false);
    const screenStreamRef = useRef<MediaStream | null>(null);
    const screenIntervalRef = useRef<number | null>(null);

    // Audio player refs
    const audioContextRef = useRef<AudioContext | null>(null);
    const audioWorkletNodeRef = useRef<AudioWorkletNode | null>(null);

    // Reconnection state
    const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const reconnectAttemptsRef = useRef(0);
    const maxReconnectAttempts = 5;
    const intentionalDisconnectRef = useRef(false);
    const isConnectingRef = useRef(false);

    // -----------------------------------------------------------------------
    // Audio Player Setup (24kHz output from Gemini)
    // -----------------------------------------------------------------------
    const initAudioPlayer = useCallback(async () => {
        try {
            const audioContext = new AudioContext({ sampleRate: 24000 });

            // Resume the AudioContext — browsers suspend it by default
            // due to autoplay policies. Without this, audio is silently dropped.
            if (audioContext.state === "suspended") {
                await audioContext.resume();
            }

            // Create an inline AudioWorklet for PCM playback
            const workletCode = `
        class PCMPlayerProcessor extends AudioWorkletProcessor {
          constructor() {
            super();
            this.bufferSize = 24000 * 120;
            this.buffer = new Float32Array(this.bufferSize);
            this.writeIndex = 0;
            this.readIndex = 0;
            this.port.onmessage = (event) => {
              if (event.data.command === 'endOfAudio') {
                this.readIndex = this.writeIndex;
                return;
              }
              const int16Samples = new Int16Array(event.data);
              for (let i = 0; i < int16Samples.length; i++) {
                const floatVal = int16Samples[i] / 32768;
                this.buffer[this.writeIndex] = floatVal;
                this.writeIndex = (this.writeIndex + 1) % this.bufferSize;
                if (this.writeIndex === this.readIndex) {
                  this.readIndex = (this.readIndex + 1) % this.bufferSize;
                }
              }
            };
          }
          process(inputs, outputs) {
            const output = outputs[0];
            const framesPerBlock = output[0].length;
            for (let frame = 0; frame < framesPerBlock; frame++) {
              output[0][frame] = this.buffer[this.readIndex];
              if (output.length > 1) {
                output[1][frame] = this.buffer[this.readIndex];
              }
              if (this.readIndex !== this.writeIndex) {
                this.readIndex = (this.readIndex + 1) % this.bufferSize;
              }
            }
            return true;
          }
        }
        registerProcessor('pcm-player-processor', PCMPlayerProcessor);
      `;

            const blob = new Blob([workletCode], { type: "application/javascript" });
            const url = URL.createObjectURL(blob);
            await audioContext.audioWorklet.addModule(url);
            URL.revokeObjectURL(url);

            const audioPlayerNode = new AudioWorkletNode(audioContext, "pcm-player-processor");
            audioPlayerNode.connect(audioContext.destination);

            audioContextRef.current = audioContext;
            audioWorkletNodeRef.current = audioPlayerNode;

            console.log("[AUDIO] Player initialized, context state:", audioContext.state);
        } catch (err) {
            console.error("Failed to initialize audio player:", err);
        }
    }, []);

    // -----------------------------------------------------------------------
    // Base64 → ArrayBuffer
    // -----------------------------------------------------------------------
    const base64ToArrayBuffer = useCallback((base64: string): ArrayBuffer => {
        let standardBase64 = base64.replace(/-/g, "+").replace(/_/g, "/");
        while (standardBase64.length % 4) standardBase64 += "=";
        const binaryString = atob(standardBase64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes.buffer;
    }, []);

    // -----------------------------------------------------------------------
    // Event Handler
    // -----------------------------------------------------------------------
    const handleEvent = useCallback(
        (event: AgentEvent) => {
            // --- Input Transcription (user's spoken words) ---
            if (event.inputTranscription?.text) {
                const text = event.inputTranscription.text;
                if (event.inputTranscription.finished) {
                    setCurrentTranscription("");
                    // Add as a user message
                    if (text.trim()) {
                        setMessages((prev) => [
                            ...prev,
                            {
                                id: crypto.randomUUID(),
                                role: "user",
                                content: text.trim(),
                                timestamp: new Date(),
                                isTranscription: true,
                            },
                        ]);
                    }
                } else {
                    setCurrentTranscription(text);
                }
            }

            // --- Output Transcription (agent's spoken words as text) ---
            if (event.outputTranscription?.text) {
                const text = event.outputTranscription.text;
                if (event.outputTranscription.finished) {
                    // Final transcription — add or replace partial message
                    setMessages((prev) => {
                        const lastMsg = prev[prev.length - 1];
                        if (lastMsg?.role === "assistant" && lastMsg?.isPartial) {
                            return [
                                ...prev.slice(0, -1),
                                { ...lastMsg, content: text, isPartial: false },
                            ];
                        }
                        return [
                            ...prev,
                            {
                                id: crypto.randomUUID(),
                                role: "assistant",
                                content: text,
                                timestamp: new Date(),
                                isPartial: false,
                            },
                        ];
                    });
                    partialTextRef.current = "";
                } else {
                    // Partial transcription — update or create partial message
                    partialTextRef.current = text;
                    setMessages((prev) => {
                        const lastMsg = prev[prev.length - 1];
                        if (lastMsg?.role === "assistant" && lastMsg?.isPartial) {
                            return [
                                ...prev.slice(0, -1),
                                { ...lastMsg, content: text },
                            ];
                        }
                        return [
                            ...prev,
                            {
                                id: crypto.randomUUID(),
                                role: "assistant",
                                content: text,
                                timestamp: new Date(),
                                isPartial: true,
                            },
                        ];
                    });
                }
            }

            // --- Text Content (for text-mode responses) ---
            if (event.content?.parts) {
                for (const part of event.content.parts) {
                    // Check for function calls
                    if (part.functionCall?.name) {
                        const functionName = part.functionCall.name;
                        setActivities((prev) => [...prev, {
                            id: crypto.randomUUID(),
                            name: functionName,
                            timestamp: new Date(),
                            status: 'executing'
                        }]);
                    }

                    // Audio data → play it
                    if (part.inlineData?.mimeType?.startsWith("audio/pcm")) {
                        if (audioWorkletNodeRef.current && part.inlineData.data) {
                            // Ensure AudioContext is running (may suspend if tab is backgrounded)
                            if (audioContextRef.current?.state === "suspended") {
                                audioContextRef.current.resume();
                            }
                            const audioBuffer = base64ToArrayBuffer(part.inlineData.data);
                            audioWorkletNodeRef.current.port.postMessage(audioBuffer);
                            setIsAgentSpeaking(true);
                        }
                    }

                    // Text content
                    if (part.text && event.author !== "user") {
                        continue;
                    }
                }
            }

            // --- Turn Complete ---
            if (event.turnComplete) {
                setIsAgentSpeaking(false);
                partialTextRef.current = "";
                // Mark all partial messages as complete
                setMessages((prev) =>
                    prev.map((m) => (m.isPartial ? { ...m, isPartial: false } : m))
                );
                // Mark all activities as complete
                setActivities((prev) =>
                    prev.map((a) => a.status === 'executing' ? { ...a, status: 'completed' } : a)
                );
            }

            // --- Interrupted ---
            if (event.interrupted) {
                console.log("[WS] Agent was interrupted");
                setIsAgentSpeaking(false);
                partialTextRef.current = "";

                // Clear the audio buffer immediately for instant silence
                if (audioWorkletNodeRef.current) {
                    audioWorkletNodeRef.current.port.postMessage({ command: "endOfAudio" });
                }

                // Finalize any partial assistant messages
                setMessages((prev) =>
                    prev.map((m) =>
                        m.isPartial && m.role === "assistant"
                            ? { ...m, isPartial: false }
                            : m
                    )
                );
            }

            // --- Error ---
            if (event.errorCode) {
                console.error(`Agent error: ${event.errorCode} - ${event.errorMessage}`);
                setMessages((prev) => [
                    ...prev,
                    {
                        id: crypto.randomUUID(),
                        role: "assistant",
                        content: `⚠️ Error: ${event.errorMessage || event.errorCode}`,
                        timestamp: new Date(),
                    },
                ]);
            }
        },
        [base64ToArrayBuffer]
    );

    // -----------------------------------------------------------------------
    // Clear reconnect timer
    // -----------------------------------------------------------------------
    const clearReconnectTimer = useCallback(() => {
        if (reconnectTimerRef.current) {
            clearTimeout(reconnectTimerRef.current);
            reconnectTimerRef.current = null;
        }
    }, []);

    // -----------------------------------------------------------------------
    // Connect (with auto-reconnect on unexpected disconnects)
    // -----------------------------------------------------------------------
    const connect = useCallback(async () => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;
        if (isConnectingRef.current) return;

        isConnectingRef.current = true;
        intentionalDisconnectRef.current = false;
        clearReconnectTimer();
        setStatus("connecting");

        await initAudioPlayer();

        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws/${userIdRef.current}/${sessionIdRef.current}`;

        try {
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                setStatus("connected");
                reconnectAttemptsRef.current = 0;
                isConnectingRef.current = false;
                console.log("[WS] Connected to AI PC Technician agent");

                // Play premium connection chime natively (no audio files needed)
                try {
                    const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();

                    // Base tone
                    const osc1 = audioCtx.createOscillator();
                    osc1.type = "sine";
                    osc1.frequency.setValueAtTime(523.25, audioCtx.currentTime); // C5

                    // High sparkle
                    const osc2 = audioCtx.createOscillator();
                    osc2.type = "sine";
                    osc2.frequency.setValueAtTime(1046.50, audioCtx.currentTime); // C6

                    // Envelope
                    const gainNode = audioCtx.createGain();
                    gainNode.gain.setValueAtTime(0, audioCtx.currentTime);
                    gainNode.gain.linearRampToValueAtTime(0.15, audioCtx.currentTime + 0.05); // Quick fade in
                    gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.5); // Smooth fade out

                    osc1.connect(gainNode);
                    osc2.connect(gainNode);
                    gainNode.connect(audioCtx.destination);

                    osc1.start();
                    osc2.start();
                    osc1.stop(audioCtx.currentTime + 0.5);
                    osc2.stop(audioCtx.currentTime + 0.5);
                } catch (e) {
                    console.error("[WS] Failed to play connection sound:", e);
                }
            };

            ws.onmessage = (event) => {
                try {
                    const agentEvent: AgentEvent = JSON.parse(event.data);
                    handleEvent(agentEvent);
                } catch (err) {
                    console.error("[WS] Failed to parse event:", err);
                }
            };

            ws.onerror = (err) => {
                console.error("[WS] WebSocket error:", err);
                isConnectingRef.current = false;
            };

            ws.onclose = (closeEvent) => {
                isConnectingRef.current = false;
                setIsAgentSpeaking(false);
                partialTextRef.current = "";

                // Clear audio buffer on disconnect
                if (audioWorkletNodeRef.current) {
                    audioWorkletNodeRef.current.port.postMessage({ command: "endOfAudio" });
                }

                // Finalize any partial messages
                setMessages((prev) =>
                    prev.map((m) =>
                        m.isPartial ? { ...m, isPartial: false } : m
                    )
                );

                if (intentionalDisconnectRef.current) {
                    // User intentionally disconnected — stay disconnected
                    setStatus("disconnected");
                    console.log("[WS] Intentionally disconnected");
                } else if (
                    closeEvent.code !== 1000 &&
                    closeEvent.code !== 1001 &&
                    reconnectAttemptsRef.current < maxReconnectAttempts
                ) {
                    // Abnormal close — attempt auto-reconnect with backoff
                    const attempt = reconnectAttemptsRef.current + 1;
                    const delay = Math.min(1000 * Math.pow(2, attempt - 1), 15000);
                    console.log(
                        `[WS] Unexpected disconnect (code ${closeEvent.code}). ` +
                        `Reconnecting in ${delay}ms (attempt ${attempt}/${maxReconnectAttempts})...`
                    );
                    setStatus("connecting");
                    reconnectAttemptsRef.current = attempt;
                    reconnectTimerRef.current = setTimeout(() => {
                        connect();
                    }, delay);
                } else {
                    setStatus("disconnected");
                    if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
                        console.warn("[WS] Max reconnect attempts reached. Giving up.");
                        reconnectAttemptsRef.current = 0;
                    } else {
                        console.log("[WS] Disconnected (normal close)");
                    }
                }
            };
        } catch (err) {
            console.error("[WS] Failed to create WebSocket:", err);
            isConnectingRef.current = false;
            setStatus("error");
        }
    }, [handleEvent, initAudioPlayer, clearReconnectTimer]);

    // -----------------------------------------------------------------------
    // Disconnect
    // -----------------------------------------------------------------------
    const disconnect = useCallback(() => {
        // Mark as intentional so onclose doesn't auto-reconnect
        intentionalDisconnectRef.current = true;
        clearReconnectTimer();
        reconnectAttemptsRef.current = 0;

        // Clear audio buffer before closing
        if (audioWorkletNodeRef.current) {
            audioWorkletNodeRef.current.port.postMessage({ command: "endOfAudio" });
        }

        wsRef.current?.close(1000, "User disconnected");
        wsRef.current = null;

        audioContextRef.current?.close();
        audioContextRef.current = null;
        audioWorkletNodeRef.current = null;

        setStatus("disconnected");
        setIsAgentSpeaking(false);
        partialTextRef.current = "";

        // Finalize any in-flight partial messages
        setMessages((prev) =>
            prev.map((m) => (m.isPartial ? { ...m, isPartial: false } : m))
        );

        // Clean up screen sharing
        if (screenIntervalRef.current) {
            clearInterval(screenIntervalRef.current);
            screenIntervalRef.current = null;
        }
        if (screenStreamRef.current) {
            screenStreamRef.current.getTracks().forEach((t) => t.stop());
            screenStreamRef.current = null;
        }
        setIsScreenSharing(false);
    }, [clearReconnectTimer]);

    // -----------------------------------------------------------------------
    // Send Text Message
    // -----------------------------------------------------------------------
    const sendText = useCallback((text: string) => {
        if (!text.trim() || wsRef.current?.readyState !== WebSocket.OPEN) return;

        // Add user message locally
        setMessages((prev) => [
            ...prev,
            {
                id: crypto.randomUUID(),
                role: "user",
                content: text.trim(),
                timestamp: new Date(),
            },
        ]);

        // Send to server
        wsRef.current.send(JSON.stringify({ type: "text", text: text.trim() }));
    }, []);

    // -----------------------------------------------------------------------
    // Send Audio Data (raw PCM bytes)
    // -----------------------------------------------------------------------
    const sendAudio = useCallback((pcmData: ArrayBuffer) => {
        if (wsRef.current?.readyState !== WebSocket.OPEN) return;
        try {
            wsRef.current.send(pcmData);
        } catch (err) {
            console.error("[WS] Failed to send audio:", err);
        }
    }, []);

    // -----------------------------------------------------------------------
    // Send Image (file → base64 JPEG → WebSocket)
    // -----------------------------------------------------------------------
    const sendImage = useCallback((file: File, caption?: string) => {
        if (wsRef.current?.readyState !== WebSocket.OPEN) return;

        const reader = new FileReader();
        reader.onload = () => {
            const dataUrl = reader.result as string;
            // Extract base64 data (strip "data:image/...;base64," prefix)
            const base64Data = dataUrl.split(",")[1];
            const mimeType = file.type || "image/jpeg";

            // Add local preview message
            setMessages((prev) => [
                ...prev,
                {
                    id: crypto.randomUUID(),
                    role: "user",
                    content: caption || "📷 Sent an image",
                    timestamp: new Date(),
                    imageUrl: dataUrl,
                },
            ]);

            // Send to server
            wsRef.current?.send(
                JSON.stringify({
                    type: "image",
                    data: base64Data,
                    mimeType,
                })
            );

            // If there's a caption, send it as a follow-up text
            if (caption?.trim()) {
                wsRef.current?.send(
                    JSON.stringify({ type: "text", text: caption.trim() })
                );
            }
        };
        reader.readAsDataURL(file);
    }, []);

    // -----------------------------------------------------------------------
    // Continuous Screen Sharing
    // -----------------------------------------------------------------------
    const stopScreenShare = useCallback(() => {
        if (screenIntervalRef.current) {
            clearInterval(screenIntervalRef.current);
            screenIntervalRef.current = null;
        }
        if (screenStreamRef.current) {
            screenStreamRef.current.getTracks().forEach(track => track.stop());
            screenStreamRef.current = null;
        }
        setIsScreenSharing(false);
    }, []);

    const startScreenShare = useCallback(async () => {
        if (wsRef.current?.readyState !== WebSocket.OPEN) return;

        try {
            const stream = await navigator.mediaDevices.getDisplayMedia({
                video: { displaySurface: "monitor" } as MediaTrackConstraints,
            });

            screenStreamRef.current = stream;
            setIsScreenSharing(true);

            sendText("I am sharing my screen now.");

            const video = document.createElement("video");
            video.srcObject = stream;
            await video.play();

            const canvas = document.createElement("canvas");
            const ctx = canvas.getContext("2d")!;

            // Send a frame every 2 seconds
            screenIntervalRef.current = window.setInterval(async () => {
                if (!screenStreamRef.current?.active) {
                    stopScreenShare();
                    return;
                }

                canvas.width = Math.min(video.videoWidth, 1280);
                canvas.height = Math.min(
                    video.videoHeight,
                    Math.round((1280 / video.videoWidth) * video.videoHeight)
                );
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

                const blob = await new Promise<Blob>((resolve) =>
                    canvas.toBlob((b) => resolve(b!), "image/jpeg", 0.5)
                );

                const base64Data = await new Promise<string>((resolve) => {
                    const r = new FileReader();
                    r.onload = () => resolve((r.result as string).split(",")[1]);
                    r.readAsDataURL(blob);
                });

                wsRef.current?.send(
                    JSON.stringify({
                        type: "image",
                        data: base64Data,
                        mimeType: "image/jpeg",
                    })
                );
            }, 2000);

            // Handle user stopping screen share via browser UI
            stream.getVideoTracks()[0].onended = () => {
                stopScreenShare();
            };
        } catch (err) {
            console.error("Screen share failed:", err);
            setIsScreenSharing(false);
        }
    }, [sendText, stopScreenShare]);

    const toggleScreenShare = useCallback(() => {
        if (isScreenSharing) stopScreenShare();
        else startScreenShare();
    }, [isScreenSharing, startScreenShare, stopScreenShare]);

    // -----------------------------------------------------------------------
    // Interrupt Agent — user interrupts the agent mid-speech
    // -----------------------------------------------------------------------
    const interruptAgent = useCallback(() => {
        console.log("[WS] User interrupting agent");

        // 1. Immediately clear the audio playback buffer for instant silence
        if (audioWorkletNodeRef.current) {
            audioWorkletNodeRef.current.port.postMessage({ command: "endOfAudio" });
        }

        // 2. Update state
        setIsAgentSpeaking(false);

        // 3. Finalize any partial assistant messages
        partialTextRef.current = "";
        setMessages((prev) =>
            prev.map((m) =>
                m.isPartial && m.role === "assistant"
                    ? { ...m, isPartial: false }
                    : m
            )
        );
    }, []);

    // -----------------------------------------------------------------------
    // Cleanup on unmount
    // -----------------------------------------------------------------------
    useEffect(() => {
        return () => {
            intentionalDisconnectRef.current = true;
            clearReconnectTimer();
            disconnect();
        };
    }, [disconnect, clearReconnectTimer]);

    return {
        status,
        messages,
        isAgentSpeaking,
        currentTranscription,
        activities,
        connect,
        disconnect,
        sendText,
        sendAudio,
        sendImage,
        interruptAgent,
        toggleScreenShare,
        isScreenSharing,
    };
}
