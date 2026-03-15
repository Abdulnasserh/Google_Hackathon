/**
 * useAudioRecorder Hook — Microphone Audio Capture
 * ==================================================
 * Captures microphone audio using Web Audio API + AudioWorklet,
 * converts to 16-bit PCM at 16kHz (required by Gemini Live API),
 * and streams chunks to the callback function.
 *
 * Architecture Role:
 *   Microphone → AudioContext(16kHz) → AudioWorklet → PCM16 → callback
 *                                                          ↓
 *                                     useWebSocket.sendAudio() → FastAPI → ADK
 */

import { useState, useCallback, useRef } from "react";

export function useAudioRecorder(onAudioData: (pcmData: ArrayBuffer) => void) {
    const [isRecording, setIsRecording] = useState(false);

    const audioContextRef = useRef<AudioContext | null>(null);
    const workletNodeRef = useRef<AudioWorkletNode | null>(null);
    const streamRef = useRef<MediaStream | null>(null);

    // -----------------------------------------------------------------------
    // Start Recording
    // -----------------------------------------------------------------------
    const startRecording = useCallback(async () => {
        try {
            // Create AudioContext at 16kHz (Gemini Live API input requirement)
            const audioContext = new AudioContext({ sampleRate: 16000 });

            // Create inline AudioWorklet for PCM capture
            const workletCode = `
        class PCMRecorderProcessor extends AudioWorkletProcessor {
          constructor() {
            super();
          }
          process(inputs, outputs, parameters) {
            if (inputs.length > 0 && inputs[0].length > 0) {
              const inputChannel = inputs[0][0];
              const inputCopy = new Float32Array(inputChannel);
              this.port.postMessage(inputCopy);
            }
            return true;
          }
        }
        registerProcessor('pcm-recorder-processor', PCMRecorderProcessor);
      `;

            const blob = new Blob([workletCode], { type: "application/javascript" });
            const url = URL.createObjectURL(blob);
            await audioContext.audioWorklet.addModule(url);
            URL.revokeObjectURL(url);

            // Request microphone access
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: { 
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                },
            });

            const source = audioContext.createMediaStreamSource(stream);
            const workletNode = new AudioWorkletNode(
                audioContext,
                "pcm-recorder-processor"
            );

            // Convert Float32 to 16-bit PCM and send to callback
            workletNode.port.onmessage = (event: MessageEvent) => {
                const float32Data: Float32Array = event.data;
                const pcm16 = new Int16Array(float32Data.length);
                for (let i = 0; i < float32Data.length; i++) {
                    pcm16[i] = float32Data[i] * 0x7fff;
                }
                onAudioData(pcm16.buffer);
            };

            source.connect(workletNode);

            // Store refs for cleanup
            audioContextRef.current = audioContext;
            workletNodeRef.current = workletNode;
            streamRef.current = stream;

            setIsRecording(true);
        } catch (err) {
            console.error("Failed to start recording:", err);
            throw err;
        }
    }, [onAudioData]);

    // -----------------------------------------------------------------------
    // Stop Recording
    // -----------------------------------------------------------------------
    const stopRecording = useCallback(() => {
        // Stop all microphone tracks
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;

        // Disconnect worklet
        workletNodeRef.current?.disconnect();
        workletNodeRef.current = null;

        // Close audio context
        audioContextRef.current?.close();
        audioContextRef.current = null;

        setIsRecording(false);
    }, []);

    return {
        isRecording,
        startRecording,
        stopRecording,
    };
}
