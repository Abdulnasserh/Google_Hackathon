import { useRef, useEffect, useCallback } from "react";
import {
    Mic,
    ArrowLeft,
    X,
    Activity,
    MonitorUp,
    ImagePlus,
    Download,
    Shield,
    Cpu,
    Terminal
} from "lucide-react";
import { toast } from "sonner";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useAudioRecorder } from "@/hooks/useAudioRecorder";
import { Orb } from "@/components/ui/orb";
import { ParticleField } from "@/components/ParticleField";
import { DaemonStatusOverlay } from "@/components/DaemonStatusOverlay";

export function ChatInterface() {

    const messagesEndRef = useRef<HTMLDivElement>(null);

    const {
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
        daemonConnected,
        sessionId,
    } = useWebSocket();

    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleImageSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            sendImage(file, "I am sharing an image. Please look at it.");
            toast.success("Image uploaded to AI Assistant");
        }
        e.target.value = "";
    }, [sendImage]);

    // Wrap sendAudio to auto-interrupt agent when user speaks
    const sendAudioWithInterrupt = useCallback((pcmData: ArrayBuffer) => {
        if (isAgentSpeaking) {
            const pcm16 = new Int16Array(pcmData);
            let sum = 0;
            for (let i = 0; i < pcm16.length; i++) {
                sum += Math.abs(pcm16[i]);
            }
            const avg = sum / pcm16.length;
            // threshold for voice activity ~ 500 (much more sensitive for interruptions)
            if (avg > 500) {
                interruptAgent();
            }
        }
        sendAudio(pcmData);
    }, [sendAudio, isAgentSpeaking, interruptAgent]);

    const { isRecording, startRecording, stopRecording } = useAudioRecorder(sendAudioWithInterrupt);

    // REAL CONNECTION STATUS: We consider it 'connected' if the voice/text bridge is up 
    // AND the local daemon is paired.
    const isVoiceConnected = status === "connected" || status === "connecting";
    const isConnected = isVoiceConnected && daemonConnected;
    const isListening = isRecording || isVoiceConnected;

    // Real date for the UI
    const now = new Date();
    const dateParts = now.toDateString().split(" ");
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }).toLowerCase().replace('am', '').replace('pm', '').trim();

    const computeAgentState = (): "thinking" | "listening" | "talking" | null => {
        if (!isConnected) return null;
        if (isAgentSpeaking) return "talking";
        if (status === "connecting" || (isListening && (!isRecording && currentTranscription))) return "thinking";
        if (isConnected || isRecording) return "listening";
        return null;
    };
    const agentState = computeAgentState();

    const handleMicTap = useCallback(async () => {
        if (isRecording || isConnected) {
            // If agent is speaking, interrupt it first for a clean stop
            if (isAgentSpeaking) {
                interruptAgent();
            }
            stopRecording();
            disconnect();
        } else {
            await connect();
            try {
                await startRecording();
            } catch {
                toast.error("Microphone access denied");
            }
        }
    }, [isRecording, isConnected, isAgentSpeaking, connect, disconnect, startRecording, stopRecording, interruptAgent]);



    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, currentTranscription]);

    const handleBackTap = useCallback(() => {
        if (isAgentSpeaking) interruptAgent();
        if (isRecording || isConnected) {
            stopRecording();
            disconnect();
        }
    }, [isAgentSpeaking, interruptAgent, isRecording, isConnected, stopRecording, disconnect]);

    // View: HOME DASHBOARD (Idle)
    if (!isListening) {
        return (
            <div className="flex flex-col h-screen text-white bg-gradient-to-b from-[#0a0a0f] via-[#060610] to-[#040406] font-sans selection:bg-sky-500/30 overflow-hidden relative">
                {/* Ambient Nora Branding Watermark */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none select-none overflow-hidden z-0">
                    <span className="text-[25vw] font-black text-white/[0.03] tracking-[0.2em]">NORA</span>
                </div>

                {/* Cinematic particle background */}
                <ParticleField particleCount={50} />
                {/* Daemon connection ceremony overlay */}
                <DaemonStatusOverlay daemonConnected={daemonConnected} sessionId={sessionId} />
                {/* Top App Bar */}
                <div className="flex justify-between items-center px-8 pt-10 pb-4 max-w-5xl mx-auto w-full relative z-20">
                    <div className="flex items-center gap-6">
                        <div className="flex flex-col leading-tight border-r border-white/10 pr-6">
                            <span className="text-3xl font-light tracking-widest text-sky-50">{timeStr}</span>
                            <span className="text-xs text-sky-100/50 tracking-widest font-semibold uppercase">{dateParts[1]} {dateParts[2]}</span>
                        </div>
                        <div className="flex flex-col">
                            <span className="text-2xl font-bold tracking-[0.3em] text-white/90 drop-shadow-sm">NORA</span>
                            <span className="text-[10px] text-sky-400 font-bold uppercase tracking-[0.2em] -mt-1 opacity-80">Autonomous</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="text-right flex flex-col items-end">
                            <span className="text-sm font-medium text-white/90">Personal Assistant</span>
                            {isConnected ? (
                                <span className="text-[10px] text-emerald-400 font-medium tracking-wider uppercase flex items-center gap-1.5 mt-0.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> Systems Online
                                </span>
                            ) : isVoiceConnected ? (
                                <span className="text-[10px] text-amber-400 font-medium tracking-wider uppercase flex items-center gap-1.5 mt-0.5" title="Connected to AI, but daemon is offline">
                                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span> Voice Only (No Target)
                                </span>
                            ) : daemonConnected ? (
                                <span className="text-[10px] text-sky-400/90 font-medium tracking-wider uppercase flex items-center gap-1.5 mt-0.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-sky-500"></span> Daemon Ready
                                </span>
                            ) : (
                                <span className="text-[10px] text-white/50 font-medium tracking-wider uppercase flex items-center gap-1.5 mt-0.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-white/30"></span> Offline / Idle
                                </span>
                            )}
                            <div className="mt-1 flex items-center gap-2">
                                <span className="text-[9px] text-zinc-500 font-mono">Daemon ID: {sessionId}</span>
                                <div className="flex gap-1.5 border-l border-white/10 pl-2">
                                    <a href="https://github.com/Abdulnasserh/Google_Hackathon/releases/tag/NORA-DAEMONS" target="_blank" rel="noopener noreferrer" className="text-[9px] flex items-center gap-0.5 text-sky-400 hover:text-sky-300 bg-sky-500/10 hover:bg-sky-500/20 px-1.5 py-0.5 rounded transition-colors" title="Download Windows Daemon from GitHub">
                                        <Download className="w-2.5 h-2.5" /> Win
                                    </a>
                                    <a href="https://github.com/Abdulnasserh/Google_Hackathon/releases/tag/NORA-DAEMONS" target="_blank" rel="noopener noreferrer" className="text-[9px] flex items-center gap-0.5 text-sky-400 hover:text-sky-300 bg-sky-500/10 hover:bg-sky-500/20 px-1.5 py-0.5 rounded transition-colors" title="Download macOS Intel Daemon from GitHub">
                                        <Download className="w-2.5 h-2.5" /> Mac (Intel)
                                    </a>
                                    <a href="https://github.com/Abdulnasserh/Google_Hackathon/releases/tag/NORA-DAEMONS" target="_blank" rel="noopener noreferrer" className="text-[9px] flex items-center gap-0.5 text-sky-400 hover:text-sky-300 bg-sky-500/10 hover:bg-sky-500/20 px-1.5 py-0.5 rounded transition-colors" title="Download macOS Apple Silicon Daemon from GitHub">
                                        <Download className="w-2.5 h-2.5" /> Mac (Silicon)
                                    </a>
                                </div>
                            </div>
                        </div>
                        <div className="h-10 w-10 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-500 p-[2px] shadow-[0_0_15px_rgba(56,189,248,0.3)]">
                            <div className="h-full w-full rounded-full bg-[#0a0a0f] overflow-hidden flex items-center justify-center">
                                <Activity className="w-5 h-5 text-sky-400" />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Center Orb */}
                <div className="flex-1 flex flex-col items-center justify-center relative -mt-4 w-full h-[300px] max-w-5xl mx-auto">
                    <Orb agentState={agentState} colors={["#38bdf8", "#818cf8"]} />
                    <div
                        className="absolute inset-0 flex flex-col items-center justify-center cursor-pointer group z-10"
                        onClick={handleMicTap}
                    >
                        <span className="text-sky-100/30 text-[10px] mb-2 tracking-[0.5em] uppercase font-bold">NORA SYSTEM</span>
                        <span className="text-2xl font-light group-hover:text-sky-300 transition-all duration-500 gradient-text-premium scale-110 group-hover:scale-125">Tap to Connect</span>
                        <div className="flex items-center gap-3 mt-4">
                            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.06]">
                                <Shield className="w-3 h-3 text-emerald-400" />
                                <span className="text-[10px] text-white/40">Write</span>
                            </div>
                            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.06]">
                                <Terminal className="w-3 h-3 text-sky-400" />
                                <span className="text-[10px] text-white/40">Code</span>
                            </div>
                            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.06]">
                                <Cpu className="w-3 h-3 text-violet-400" />
                                <span className="text-[10px] text-white/40">System</span>
                            </div>
                        </div>
                        <div className="mt-6 text-white/30 group-hover:text-white/80 transition-all group-hover:scale-110">
                            <Mic className="w-6 h-6" />
                        </div>
                    </div>
                </div>

                {/* Hidden File Input */}
                <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleImageSelect}
                    className="hidden"
                />

                {/* Bottom Section Container */}
                <div className="w-full max-w-4xl mx-auto flex flex-col gap-8 pb-28 px-6">
                    {/* Suggested Queries */}
                    <div className="w-full overflow-x-auto hide-scrollbar">
                        <div className="flex gap-3 snap-x pb-2 px-1">
                            {[
                                { icon: "📝", text: "Write a letter to my friend" },
                                { icon: "💻", text: "Create a new Python project" },
                                { icon: "🧹", text: "Clean up system temp files" },
                                { icon: "🎵", text: "Open YouTube in Chrome" },
                            ].map((q, i) => (
                                <div key={i} className="whitespace-nowrap snap-center glass-card-premium px-5 py-3 text-sm font-light text-white/70 hover:bg-white/10 hover:text-white cursor-pointer transition-all shadow-lg flex items-center gap-2.5 shrink-0" onClick={async () => { await connect(); try { await startRecording(); } catch {} sendText(q.text); }}>
                                    <span>{q.icon}</span>
                                    <span>{q.text}</span>
                                </div>
                            ))}
                        </div>
                    </div>


                </div>

                {/* Bottom Nav */}
                <div className="absolute bottom-0 w-full bg-[#0a0a0f]/90 backdrop-blur-xl border-t border-white/5 py-3 z-50">
                    <div className="max-w-xs mx-auto px-6 flex justify-between items-center text-white/40">
                        <button
                            onClick={toggleScreenShare}
                            className={`p-3 rounded-xl transition-all ${isScreenSharing ? 'bg-indigo-500/20 text-indigo-400 shadow-[0_0_15px_rgba(99,102,241,0.3)]' : 'hover:text-white hover:bg-white/10'}`}
                            title={isScreenSharing ? "Stop sharing screen" : "Share screen"}
                        >
                            <MonitorUp className={`w-6 h-6 ${isScreenSharing ? 'animate-pulse' : ''}`} />
                        </button>

                        <button
                            onClick={handleMicTap}
                            className="relative -top-6 bg-gradient-to-tr from-sky-500 to-indigo-500 p-4 rounded-full text-white shadow-[0_8px_25px_rgba(56,189,248,0.3)] hover:scale-105 transition-transform"
                        >
                            <Mic className="w-6 h-6" />
                        </button>

                        <button
                            onClick={() => fileInputRef.current?.click()}
                            className="p-3 rounded-xl hover:text-white hover:bg-white/10 transition-all"
                            title="Upload Image"
                        >
                            <ImagePlus className="w-6 h-6" />
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // View: LISTENING / TEXT CHAT / ACTIVE
    return (
        <div className="flex flex-col h-screen text-white bg-gradient-to-b from-[#0a0a0f] via-[#060610] to-[#040406] font-sans overflow-hidden selection:bg-sky-500/30 relative">
            {/* Cinematic particle background */}
            <ParticleField particleCount={30} />
            
            {/* Ambient Nora Branding Watermark */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none select-none overflow-hidden z-0">
                <span className="text-[20vw] font-black text-white/[0.02] tracking-[0.2em] transform -rotate-12 translate-y-12">NORA</span>
            </div>

            {/* Daemon connection ceremony overlay */}
            <DaemonStatusOverlay daemonConnected={daemonConnected} sessionId={sessionId} />
            {/* Top App Bar */}
            <div className="flex justify-between items-center px-6 pt-10 pb-4 z-20 max-w-5xl mx-auto w-full">
                <button
                    onClick={handleBackTap}
                    className="w-10 h-10 rounded-full border border-white/10 flex items-center justify-center bg-white/5 hover:bg-white/10 transition-colors"
                >
                    <ArrowLeft className="w-5 h-5 text-white/70" />
                </button>
                <div className="flex flex-col items-center">
                    <div className="flex items-center gap-2">
                        <span className="text-[10px] text-sky-400 font-bold uppercase tracking-[0.3em]">NORA</span>
                        <div className="w-1 h-3 border-l border-white/20"></div>
                        <div className="text-sm font-medium tracking-wide text-white/90">
                            {status === "connecting" ? "Linking Interface..." : "Active Session"}
                        </div>
                    </div>
                    {isAgentSpeaking && (
                        <div className="text-[9px] text-sky-400/70 font-bold uppercase tracking-[0.4em] mt-1 animate-pulse">
                            Processing Data
                        </div>
                    )}
                </div>
                <div className="w-10 h-10 flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-sky-500 shadow-[0_0_8px_rgba(56,189,248,0.8)] animate-pulse"></div>
                </div> {/* Spacer for alignment */}
            </div>

            {/* Main Area: Mixed Text and Voice mode */}
            <div className="flex-1 flex flex-col min-h-0 z-10 w-full">
                {/* Full screen Orb View with Activity Log */}
                    <div className="flex-1 flex flex-col md:flex-row items-center justify-center relative w-full h-full min-h-[400px] max-w-6xl mx-auto px-6 gap-8">

                        {/* Empty spacer for centering on desktop if needed, or left-aligning */}
                        <div className="hidden md:block w-[300px]"></div>

                        {/* Center Orb */}
                        <div className="flex-1 flex items-center justify-center w-full">
                            <Orb agentState={agentState} colors={["#38bdf8", "#818cf8"]} />
                        </div>

                        {/* Right Activity Log Panel */}
                        <div className="w-full md:w-[300px] h-[320px] bg-[#12121a]/80 backdrop-blur-2xl border border-white/10 rounded-2xl flex flex-col shadow-2xl overflow-hidden self-center">
                            {/* Panel Header */}
                            <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between bg-white/[0.02]">
                                <div className="flex items-center gap-2">
                                    <div className="relative flex items-center justify-center w-4 h-4">
                                        <div className="absolute inset-0 bg-sky-500/20 rounded-full animate-ping"></div>
                                        <Activity className="w-3.5 h-3.5 text-sky-400 relative z-10" />
                                    </div>
                                    <span className="text-[11px] font-semibold text-sky-100/70 tracking-widest uppercase">Live Activity</span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <div className={`w-1 h-1 rounded-full ${daemonConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></div>
                                    <span className={`text-[10px] font-mono ${daemonConnected ? 'text-emerald-400/80' : 'text-red-400/80'}`}>
                                        {daemonConnected ? 'DAEMON_LINKED' : 'DAEMON_OFFLINE'}
                                    </span>
                                </div>
                            </div>

                            {/* Log Items */}
                            <div className="flex-1 overflow-y-auto p-4 space-y-4 hide-scrollbar flex flex-col justify-end bg-gradient-to-b from-transparent to-black/20">

                                <div className="flex flex-col gap-1.5 opacity-40">
                                    <div className="flex items-center justify-between">
                                        <span className="text-[10px] text-white/40 font-mono uppercase">System</span>
                                        <span className="text-[9px] text-white/30 font-mono">{timeStr}</span>
                                    </div>
                                    <div className="text-[12px] text-white/60 font-mono">
                                        Connection to Gateway established
                                    </div>
                                </div>

                                {activities.map((activity) => (
                                    <div key={activity.id} className={`flex flex-col gap-1.5 ${activity.status === 'executing' ? 'animate-fade-in-up' : 'opacity-60'}`}>
                                        <div className="flex items-center justify-between">
                                            <span className={`text-[10px] font-mono uppercase ${activity.status === 'executing' ? 'text-sky-400' : activity.status === 'failed' ? 'text-red-400' : 'text-emerald-400'}`}>
                                                {activity.status === 'executing' ? 'Tool Executing' : activity.status === 'failed' ? 'Execution Failed' : 'Tool Completed'}
                                            </span>
                                            <span className={`text-[9px] font-mono ${activity.status === 'executing' ? 'text-sky-400/50 animate-pulse' : activity.status === 'failed' ? 'text-red-400/50' : 'text-white/30'}`}>
                                                {activity.status === 'executing' ? 'Now' : activity.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }).toLowerCase().replace('am', '').replace('pm', '').trim()}
                                            </span>
                                        </div>
                                        <div className={`text-[13px] font-mono flex items-center gap-2 px-2.5 py-1.5 rounded-lg relative overflow-hidden ${activity.status === 'executing' ? 'text-sky-400 bg-sky-400/10 border border-sky-400/30 shadow-[0_0_10px_rgba(56,189,248,0.1)]' : activity.status === 'failed' ? 'text-red-400 bg-red-400/10 border border-red-400/20' : 'text-emerald-400 bg-emerald-400/10 border border-emerald-400/20'}`}>
                                            {activity.status === 'executing' && (
                                                <>
                                                    <div className="absolute bottom-0 left-0 h-[1px] bg-sky-400 w-full animate-[progress_2s_ease-in-out_infinite]"></div>
                                                    <span className="w-1.5 h-1.5 bg-sky-400 rounded-full animate-pulse shadow-[0_0_5px_rgba(56,189,248,0.8)]"></span>
                                                </>
                                            )}
                                            {activity.status === 'failed' && (
                                                <span className="w-1.5 h-1.5 bg-red-400 rounded-full"></span>
                                            )}
                                            NoraMCP({activity.name})
                                        </div>
                                        {activity.args && Object.keys(activity.args).length > 0 && (
                                            <div className="text-[10px] font-mono text-white/50 bg-black/40 p-2 rounded ml-2 border-l border-white/10 break-all whitespace-pre-wrap">
                                                {activity.name === 'execute_command' || activity.name === 'run_safe_shell_command' || activity.name === 'run_safe_powershell'
                                                    ? `> ${activity.args.command || activity.args.cmd || '...'}`
                                                    : JSON.stringify(activity.args)
                                                }
                                            </div>
                                        )}
                                        {activity.status === 'failed' && (
                                            <div className="text-[9px] font-mono text-red-400/80 ml-2">
                                                ❌ Daemon offline. Command not sent.
                                            </div>
                                        )}
                                    </div>
                                ))}

                            </div>
                        </div>
                    </div>
            </div>

            {/* Transcript Text over Voice Orb (Only visible in pure voice mode) */}
            {isListening && (messages.length > 0 || currentTranscription) && (
                <div className="px-8 pb-10 text-center z-20 w-full max-w-3xl mx-auto">
                    <p className="text-2xl font-light text-white leading-relaxed">
                        {currentTranscription ? (
                            <span className="text-sky-300 animate-pulse">{currentTranscription}</span>
                        ) : messages.length > 0 ? (
                            <span dangerouslySetInnerHTML={{
                                __html: messages[messages.length - 1].content.replace(
                                    /network|system|diagnostic/i,
                                    '<span class="text-sky-400/80 font-normal">$&</span>'
                                )
                            }} />
                        ) : null}
                    </p>
                </div>
            )}

            {/* Hidden File Input (for active view) */}
            <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleImageSelect}
                className="hidden"
            />

            {/* Screensharing indicator */}
            {isScreenSharing && (
                <div className="absolute top-24 right-6 z-50 bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 text-xs px-3 py-1.5 rounded-full flex items-center gap-2 animate-fade-in-up backdrop-blur-md">
                    <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                    Screen Sharing Active
                </div>
            )}

            {/* Bottom Controls */}
            <div className="px-8 pb-10 pt-4 w-full flex justify-between items-center max-w-lg mx-auto z-20 relative">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-[1px] bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-y-4"></div>
                    {/* Voice Controls */}
                    <>
                        <div className="flex gap-2">
                            <button
                                onClick={() => fileInputRef.current?.click()}
                                className="w-12 h-12 rounded-full bg-[#12121a]/80 backdrop-blur-xl border border-white/10 flex items-center justify-center hover:bg-white/10 transition-colors shadow-lg"
                                title="Upload Image"
                            >
                                <ImagePlus className="w-5 h-5 text-white/50" />
                            </button>
                        </div>

                        <button
                            onClick={handleMicTap}
                            className="relative flex items-center justify-center w-24 h-24 group mx-4"
                        >
                            <div className="absolute inset-0 bg-sky-500/20 rounded-full animate-[ping_2s_cubic-bezier(0,0,0.2,1)_infinite]"></div>
                            <div className="absolute inset-2 bg-sky-500/30 rounded-full blur-xl"></div>
                            <div className="relative w-20 h-20 bg-gradient-to-br from-sky-400 to-indigo-600 rounded-full flex items-center justify-center shadow-[0_0_40px_rgba(56,189,248,0.5)] group-hover:scale-105 transition-transform border border-sky-300/30">
                                <Mic className="w-8 h-8 text-white" />
                            </div>
                        </button>

                        <div className="flex gap-2">
                            <button
                                onClick={toggleScreenShare}
                                className={`w-12 h-12 rounded-full backdrop-blur-xl border flex items-center justify-center transition-colors shadow-lg ${isScreenSharing ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-400' : 'bg-[#12121a]/80 border-white/10 text-white/50 hover:bg-white/10 hover:text-white'}`}
                                title={isScreenSharing ? "Stop sharing screen" : "Share screen"}
                            >
                                <MonitorUp className={`w-5 h-5 ${isScreenSharing ? 'animate-pulse' : ''}`} />
                            </button>
                            {isAgentSpeaking ? (
                                <button
                                    onClick={interruptAgent}
                                    className="w-12 h-12 rounded-full border border-rose-500/30 bg-rose-500/10 backdrop-blur-xl flex items-center justify-center hover:bg-rose-500 hover:border-rose-500 text-rose-400 hover:text-white transition-colors group shadow-lg"
                                    title="Stop Agent Speaking"
                                >
                                    <div className="w-4 h-4 bg-current rounded-sm" />
                                </button>
                            ) : (
                                <button
                                    onClick={handleMicTap}
                                    className="w-12 h-12 rounded-full border border-white/10 bg-[#12121a]/80 backdrop-blur-xl flex items-center justify-center hover:bg-white/10 hover:border-white/20 hover:text-rose-400 transition-colors group shadow-lg"
                                    title="Stop Agent"
                                >
                                    <X className="w-5 h-5 text-white/50 group-hover:text-rose-400" />
                                </button>
                            )}
                        </div>
                    </>
            </div>
        </div>
    );
}
